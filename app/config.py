from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    assistant_token: str = os.getenv("ASSISTANT_TOKEN", "change-me")
    refresh_interval: float = float(os.getenv("REFRESH_INTERVAL", "1.0"))
    cpu_threshold: float = float(os.getenv("CPU_THRESHOLD", "90"))
    memory_threshold: float = float(os.getenv("MEMORY_THRESHOLD", "90"))
    tool_timeout_seconds: int = int(os.getenv("TOOL_TIMEOUT_SECONDS", "8"))

    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_base_url: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    ai_route_mode: str = os.getenv("AI_ROUTE_MODE", "off").lower()
    greeting_enabled: bool = os.getenv("GREETING_ENABLED", "true").lower() == "true"
    assistant_name: str = os.getenv("ASSISTANT_NAME", "Jarvis")
    user_name: str = os.getenv("USER_NAME", "Boss")

    stt_mode: str = os.getenv("STT_MODE", "hybrid").lower()
    stt_language: str = os.getenv("STT_LANGUAGE", "en")
    faster_whisper_model: str = os.getenv("FASTER_WHISPER_MODEL", "tiny")
    openai_stt_model: str = os.getenv("OPENAI_STT_MODEL", "whisper-1")

    tts_mode: str = os.getenv("TTS_MODE", "hybrid").lower()
    piper_bin: str = os.getenv("PIPER_BIN", "piper")
    piper_model_path: str = os.getenv("PIPER_MODEL_PATH", "")
    piper_speaker_id: int = int(os.getenv("PIPER_SPEAKER_ID", "0"))
    allowed_commands: tuple[str, ...] = tuple(
        cmd.strip()
        for cmd in os.getenv("ALLOWED_COMMANDS", "ls,pwd,whoami,date,uptime,free,df,ps").split(",")
        if cmd.strip()
    )


settings = Settings()
