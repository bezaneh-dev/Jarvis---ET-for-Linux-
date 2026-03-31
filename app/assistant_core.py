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

    def handle_message(self, user_text: str) -> AssistantMessageResponse:
        text = user_text.strip()
        lower = text.lower()

        greeting_prefix = ""
        if settings.greeting_enabled and not self._has_greeted:
            greeting_prefix = (
                f"Hello {settings.user_name}. I am {settings.assistant_name}. "
                "I am ready when you are.\n"
            )
            self._has_greeted = True

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

        if lower.startswith(("show ", "check ", "status ")) and any(kw in lower for kw in ["cpu", "memory", "disk", "metrics", "health"]):
            risk, executor = tool_metrics()
            return ToolDecision(risk=risk, summary="Read system metrics", executor=executor)

        if any(kw in lower for kw in ["metrics", "cpu", "memory", "disk usage", "health"]):
            risk, executor = tool_metrics()
            return ToolDecision(risk=risk, summary="Read system metrics", executor=executor)

        if "list process" in lower or "top process" in lower or "running process" in lower:
            risk, executor = tool_list_processes()
            return ToolDecision(risk=risk, summary="List active processes", executor=executor)

        kill_match = re.search(r"kill\s+(?:pid\s*)?(\d+)", lower)
        if kill_match:
            pid = int(kill_match.group(1))
            risk, executor = tool_kill_process(pid)
            return ToolDecision(risk=risk, summary=f"Kill process {pid}", executor=executor)

        for action in ["shutdown", "restart", "sleep", "lock"]:
            if action in lower:
                risk, executor = tool_system_control(action)
                return ToolDecision(risk=risk, summary=f"System action: {action}", executor=executor)

        if lower.startswith("open "):
            app_name = original[5:]
            risk, executor = tool_open_app(app_name)
            return ToolDecision(risk=risk, summary=f"Open app: {app_name}", executor=executor)

        if lower.startswith("run "):
            cmd = original[4:]
            risk, executor = tool_shell(cmd)
            return ToolDecision(risk=risk, summary=f"Run shell command: {cmd}", executor=executor)

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
            "- list top processes\n"
            "- run df -h\n"
            "- open firefox\n"
            "- search web linux swap tuning\n"
            "- shutdown / restart / sleep / lock (confirmation required)"
        )

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
