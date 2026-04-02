from __future__ import annotations

import importlib.util
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path

import httpx

from app.config import settings
from app.web_helper import DDGS


@dataclass(frozen=True)
class CapabilityStatus:
    available: bool
    detail: str


@dataclass(frozen=True)
class CapabilitySnapshot:
    microphone: CapabilityStatus
    offline_stt: CapabilityStatus
    tts: CapabilityStatus
    llm: CapabilityStatus
    web_search: CapabilityStatus

    def as_dict(self) -> dict[str, dict[str, str | bool]]:
        return {
            "microphone": asdict(self.microphone),
            "offline_stt": asdict(self.offline_stt),
            "tts": asdict(self.tts),
            "llm": asdict(self.llm),
            "web_search": asdict(self.web_search),
        }


def detect_capabilities() -> CapabilitySnapshot:
    return CapabilitySnapshot(
        microphone=_detect_microphone(),
        offline_stt=_detect_offline_stt(),
        tts=_detect_tts(),
        llm=_detect_llm(),
        web_search=_detect_web_search(),
    )


def format_capability_report(capabilities: CapabilitySnapshot) -> str:
    lines = ["System ready:"]
    labels = {
        "microphone": "Microphone",
        "offline_stt": "Offline STT",
        "tts": "TTS",
        "llm": "Optional LLM",
        "web_search": "Web search",
    }
    for key, label in labels.items():
        status = getattr(capabilities, key)
        prefix = "ready" if status.available else "optional"
        lines.append(f"- {label}: {prefix} - {status.detail}")
    return "\n".join(lines)


def _detect_microphone() -> CapabilityStatus:
    if shutil.which("arecord"):
        return CapabilityStatus(True, "Microphone recording works via arecord.")
    if shutil.which("ffmpeg"):
        return CapabilityStatus(True, "Microphone recording works via ffmpeg and PulseAudio.")
    return CapabilityStatus(False, "Install alsa-utils for microphone recording.")


def _detect_offline_stt() -> CapabilityStatus:
    if shutil.which("whisper"):
        return CapabilityStatus(True, "Offline transcription works via whisper CLI.")
    if importlib.util.find_spec("faster_whisper") is not None:
        return CapabilityStatus(True, f"Offline transcription ready with faster-whisper ({settings.faster_whisper_model}).")
    return CapabilityStatus(False, "Install faster-whisper or whisper CLI for offline voice input.")


def _detect_tts() -> CapabilityStatus:
    if shutil.which(settings.piper_bin) and settings.piper_model_path.strip() and Path(settings.piper_model_path).exists():
        return CapabilityStatus(True, "Natural TTS is configured with Piper.")

    for cmd in ("spd-say", "espeak-ng", "espeak"):
        if shutil.which(cmd):
            return CapabilityStatus(True, f"Basic TTS is available through {cmd}.")
    return CapabilityStatus(False, "Install Piper or espeak-ng for spoken replies.")


def _detect_llm() -> CapabilityStatus:
    mode = settings.ai_route_mode
    if mode == "off":
        return CapabilityStatus(False, "AI mode is off; Jarvis stays fully local and tool-first.")

    if mode in {"local", "hybrid"} and _ollama_reachable():
        return CapabilityStatus(True, f"Ollama is reachable with model {settings.ollama_model}.")

    if mode in {"cloud", "hybrid"} and settings.openai_api_key:
        provider = settings.cloud_provider or "cloud"
        return CapabilityStatus(True, f"{provider.title()} is configured with model {settings.openai_model}.")

    return CapabilityStatus(False, "No LLM configured; Jarvis will use built-in local guidance.")


def _detect_web_search() -> CapabilityStatus:
    if DDGS is None:
        return CapabilityStatus(False, "Install the optional 'ddgs' package to enable web search.")
    return CapabilityStatus(True, "DuckDuckGo text search is available without API keys.")


def _ollama_reachable() -> bool:
    try:
        with httpx.Client(timeout=1.5) as client:
            resp = client.get(f"{settings.ollama_base_url}/api/tags")
            resp.raise_for_status()
        return True
    except Exception:
        return False
