from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from app.config import settings
from app.llm import LLMRouter
from app.models import AssistantMessageResponse, RiskLevel, ToolResult
from app.safety import ConfirmationManager, needs_confirmation
from app.tools import (
    tool_kill_process,
    tool_list_processes,
    tool_metrics,
    tool_open_app,
    tool_shell,
    tool_system_control,
    tool_type_text,
    tool_window_control,
)
from app.web_helper import WebHelper


@dataclass
class ToolDecision:
    risk: RiskLevel
    summary: str
    executor: Callable[[], ToolResult]


class AssistantCore:
    def __init__(self) -> None:
        self.confirmations = ConfirmationManager(ttl_seconds=120)
        self.llm = LLMRouter()
        self.web = WebHelper(self.llm)
        self._has_greeted = False
        self._last_user_message: str | None = None

    def handle_message(self, user_text: str) -> AssistantMessageResponse:
        text = user_text.strip()
        lower = text.lower()
        recall_request = self._is_recall_request(lower)

        greeting_prefix = ""
        if settings.greeting_enabled and not self._has_greeted:
            greeting_prefix = (
                f"Hello {settings.user_name}. I am {settings.assistant_name}. "
                "I am ready when you are.\n"
            )
            self._has_greeted = True

        if recall_request:
            return AssistantMessageResponse(reply=greeting_prefix + self._last_heard_text())

        self._last_user_message = text

        decision = self._route_tool(lower, text)
        if decision is not None:
            if needs_confirmation(decision.risk):
                action_id = self.confirmations.create(decision.summary, decision.executor)
                return AssistantMessageResponse(
                    reply=greeting_prefix + f"Confirmation required: {decision.summary}",
                    action_required=True,
                    pending_action_id=action_id,
                    pending_action_expires_in=self.confirmations.expires_in(action_id),
                )

            result = decision.executor()
            return AssistantMessageResponse(reply=greeting_prefix + self._format_tool_result(result), action_required=False)

        if lower in {"help", "commands", "/help"}:
            return AssistantMessageResponse(reply=greeting_prefix + self._help_text())

        social_reply = self._social_reply(lower)
        if social_reply is not None:
            return AssistantMessageResponse(reply=greeting_prefix + social_reply)

        web_result = self.web.research(text, max_results=3)
        if web_result.ok:
            return AssistantMessageResponse(reply=greeting_prefix + self._format_tool_result(web_result), action_required=False)

        if not self.llm.is_enabled():
            return AssistantMessageResponse(reply=greeting_prefix + self._local_fallback(text))

        prompt = (
            "You are Jarvis-lite for Linux. Keep answers short, practical, and command-focused. "
            f"User request: {text}"
        )
        llm_text, model = self.llm.ask(prompt)
        return AssistantMessageResponse(reply=greeting_prefix + llm_text, model_used=model)

    def confirm_action(self, action_id: str, approve: bool) -> ToolResult:
        return self.confirmations.confirm(action_id=action_id, approve=approve)

    def _route_tool(self, lower: str, original: str) -> ToolDecision | None:
        normalized = self._normalize_for_routing(lower)

        if any(phrase in normalized for phrase in ["voice setup", "fix voice", "voice api", "voice help", "speech setup", "microphone setup"]):
            return ToolDecision(
                risk=RiskLevel.low,
                summary="Show voice setup help",
                executor=lambda: ToolResult(ok=True, summary=self._voice_setup_text()),
            )

        research_prefixes = ["research ", "search web ", "web search ", "find on web "]
        for prefix in research_prefixes:
            if lower.startswith(prefix):
                query = original[len(prefix):].strip()
                return ToolDecision(
                    risk=RiskLevel.low,
                    summary=f"Research query: {query}",
                    executor=lambda q=query: self.web.research(q),
                )

        if lower.startswith("search ") and "process" not in lower:
            query = original[7:].strip()
            return ToolDecision(
                risk=RiskLevel.low,
                summary=f"Research query: {query}",
                executor=lambda q=query: self.web.research(q),
            )

        if lower.startswith(("show ", "check ", "status ")) and any(kw in normalized for kw in ["cpu", "memory", "disk", "metrics", "health", "ram", "storage"]):
            risk, executor = tool_metrics()
            return ToolDecision(risk=risk, summary="Read system metrics", executor=executor)

        if any(kw in normalized for kw in ["metrics", "cpu", "memory", "disk usage", "health", "ram usage", "storage usage"]):
            risk, executor = tool_metrics()
            return ToolDecision(risk=risk, summary="Read system metrics", executor=executor)

        if any(phrase in normalized for phrase in ["list process", "top process", "running process", "show process", "what process", "which process"]):
            risk, executor = tool_list_processes()
            return ToolDecision(risk=risk, summary="List active processes", executor=executor)

        if any(phrase in normalized for phrase in ["minimize current tab", "minimize current window", "minimize the current window", "minimize this window", "hide this window"]):
            risk, executor = tool_window_control("minimize")
            return ToolDecision(risk=risk, summary="Minimize the active window", executor=executor)

        if any(phrase in normalized for phrase in ["maximize current tab", "maximize current window", "maximize the current window", "maximize this window"]):
            risk, executor = tool_window_control("maximize")
            return ToolDecision(risk=risk, summary="Maximize the active window", executor=executor)

        if any(phrase in normalized for phrase in ["close current tab", "close current window", "close the current window", "close this window"]):
            risk, executor = tool_window_control("close")
            return ToolDecision(risk=risk, summary="Close the active window", executor=executor)

        kill_match = re.search(r"(?:kill|terminate|stop|close)\s+(?:process\s*)?(?:pid\s*)?(\d+)", normalized)
        if kill_match:
            pid = int(kill_match.group(1))
            risk, executor = tool_kill_process(pid)
            return ToolDecision(risk=risk, summary=f"Kill process {pid}", executor=executor)

        system_aliases = {
            "shutdown": ("shutdown", "power off", "turn off the computer"),
            "restart": ("restart", "reboot"),
            "sleep": ("sleep", "suspend"),
            "lock": ("lock", "lock screen"),
        }
        for action, aliases in system_aliases.items():
            if any(alias in normalized for alias in aliases):
                risk, executor = tool_system_control(action)
                return ToolDecision(risk=risk, summary=f"System action: {action}", executor=executor)

        app_request = self._extract_open_target(original)
        if app_request is not None:
            app_name = app_request
            risk, executor = tool_open_app(app_name)
            return ToolDecision(risk=risk, summary=f"Open app: {app_name}", executor=executor)

        shell_request = self._extract_shell_command(original)
        if shell_request is not None:
            cmd = shell_request
            risk, executor = tool_shell(cmd)
            return ToolDecision(risk=risk, summary=f"Run shell command: {cmd}", executor=executor)

        typing_request = self._extract_typed_text(original)
        if typing_request is not None:
            risk, executor = tool_type_text(typing_request)
            return ToolDecision(risk=risk, summary=f"Type text into the active window: {typing_request}", executor=executor)

        return None

    @staticmethod
    def _format_tool_result(result: ToolResult) -> str:
        base = result.summary
        if not result.data:
            return base
        preview = []
        if "stdout" in result.data and result.data["stdout"]:
            preview.append(f"Output:\n{result.data['stdout'][:400]}")
        if "stderr" in result.data and result.data["stderr"]:
            preview.append(f"Warnings:\n{result.data['stderr'][:240]}")
        if "cpu_percent" in result.data:
            preview.append(
                "System metrics:\nCPU {cpu:.1f}% | Memory {mem:.1f}% | Disk {disk:.1f}%".format(
                    cpu=result.data.get("cpu_percent", 0.0),
                    mem=result.data.get("memory_percent", 0.0),
                    disk=result.data.get("disk_percent", 0.0),
                )
            )
        if "processes" in result.data:
            top = result.data["processes"][:5]
            lines = []
            for proc in top:
                lines.append(
                    "{name} pid={pid} cpu={cpu:.1f}% mem={mem:.1f}%".format(
                        name=proc.get("name", "unknown"),
                        pid=proc.get("pid", "?"),
                        cpu=float(proc.get("cpu_percent", 0.0) or 0.0),
                        mem=float(proc.get("memory_percent", 0.0) or 0.0),
                    )
                )
            preview.append("Top processes:\n" + "\n".join(lines))
        if "summary" in result.data and isinstance(result.data["summary"], str):
            preview.append(f"Research summary:\n{result.data['summary'][:800]}")
        if "sources" in result.data and isinstance(result.data["sources"], list):
            refs = []
            for src in result.data["sources"][:3]:
                if isinstance(src, dict) and src.get("url"):
                    refs.append(str(src["url"]))
            if refs:
                preview.append("Sources:\n" + "\n".join(refs))
        return base + ("\n" + "\n".join(preview) if preview else "")

    @staticmethod
    def _help_text() -> str:
        return (
            "Local commands I handle well:\n"
            "- show cpu and memory\n"
            "- what is using my memory\n"
            "- list top processes\n"
            "- run df -h\n"
            "- execute uptime\n"
            "- open firefox\n"
            "- launch terminal\n"
            "- minimize current window\n"
            "- type hello world\n"
            "- search web linux swap tuning\n"
            "- fix voice\n"
            "- shutdown / restart / sleep / lock (confirmation required)"
        )

    @staticmethod
    def _social_reply(lower: str) -> str | None:
        normalized = re.sub(r"[^a-z0-9\s]", "", lower).strip()
        if normalized in {"hi", "hey", "hello", "yo", "sup", "whats up", "good morning", "good afternoon", "good evening"}:
            return (
                f"Hello {settings.user_name}. "
                "How can I help you right now?"
            )
        if normalized in {"thanks", "thank you", "thx"}:
            return "You are welcome."
        return None

    def _local_fallback(self, text: str) -> str:
        if not text:
            return self._help_text()
        return (
            "I am running in free local mode without an LLM, so I focus on reliable Linux tasks.\n"
            f"You said: {text}\n"
            "Try one of these next:\n"
            "- show cpu and memory\n"
            "- list top processes\n"
            "- run uptime\n"
            "- search web linux performance tuning\n"
            "- type help to see more commands"
        )

    def _last_heard_text(self) -> str:
        if not self._last_user_message:
            return "I do not have a previous message yet."
        return f"I heard: {self._last_user_message}"

    @staticmethod
    def _is_recall_request(lower: str) -> bool:
        normalized = " ".join(re.sub(r"[^a-z0-9\s]", " ", lower).split())
        return normalized in {
            "what did i say",
            "what did you hear",
            "repeat what i said",
            "repeat what you heard",
            "show me what i said",
            "show what i said",
        }

    @staticmethod
    def _normalize_for_routing(text: str) -> str:
        normalized = " ".join(text.lower().split())
        normalized = re.sub(r"\bjarvis\b", "", normalized)
        normalized = re.sub(r"\bjarvs\b", "", normalized)
        normalized = re.sub(r"\bplease\b", "", normalized)
        normalized = re.sub(r"\bcould you\b", "", normalized)
        normalized = re.sub(r"\bcan you\b", "", normalized)
        normalized = re.sub(r"\bwould you\b", "", normalized)
        normalized = re.sub(r"\bfor me\b", "", normalized)
        normalized = re.sub(r"\bram\b", "memory", normalized)
        return " ".join(normalized.split())

    @classmethod
    def _extract_open_target(cls, original: str) -> str | None:
        text = cls._normalize_for_routing(original)
        patterns = [
            r"^(?:open|launch|start)\s+(.+)$",
            r"^(?:open|launch|start)\s+the\s+(.+)$",
            r"^(?:please\s+)?(?:open|launch|start)\s+(.+)$",
        ]
        for pattern in patterns:
            match = re.match(pattern, text)
            if match:
                return match.group(1).strip()
        return None

    @classmethod
    def _extract_shell_command(cls, original: str) -> str | None:
        text = cls._normalize_for_routing(original)
        patterns = [
            r"^(?:run|execute)\s+(.+)$",
            r"^(?:run|execute)\s+command\s+(.+)$",
        ]
        for pattern in patterns:
            match = re.match(pattern, text)
            if match:
                return match.group(1).strip()
        return None

    @classmethod
    def _extract_typed_text(cls, original: str) -> str | None:
        text = cls._normalize_for_routing(original)
        patterns = [
            r"^type\s+(.+)$",
            r"^write\s+this\s+(.+)$",
        ]
        for pattern in patterns:
            match = re.match(pattern, text)
            if match:
                candidate = match.group(1).strip().strip("'\"")
                if candidate:
                    return candidate
        return None

    @staticmethod
    def _voice_setup_text() -> str:
        return (
            "Voice setup help:\n"
            "- Microphone recording uses arecord or ffmpeg in app/voice.py\n"
            "- Offline speech-to-text uses faster-whisper or whisper CLI\n"
            "- Spoken replies use Piper first, then spd-say / espeak-ng / espeak\n"
            "- Desktop control for minimize/type needs xdotool or wmctrl on Linux\n"
            "- Free voice model files: https://huggingface.co/rhasspy/piper-voices\n"
            "- Free cloud key option for AI replies: https://console.groq.com/keys\n"
            "- Setup wizard: python3 -m app.setup_wizard\n"
            "- Main voice code: app/voice.py\n"
            "- Main assistant routing: app/assistant_core.py"
        )
