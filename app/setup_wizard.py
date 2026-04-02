from __future__ import annotations

import secrets
from pathlib import Path

from app.capabilities import detect_capabilities, format_capability_report

ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT_DIR / ".env"


def _parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _prompt(field: str, default: str, secret: bool = False) -> str:
    shown = "(hidden)" if secret and default else default
    entered = input(f"{field} [{shown}]: ").strip()
    if not entered:
        return default
    return entered


def _choose_provider(default: str) -> str:
    print("\nCloud fallback provider (optional):")
    print("  1) none (100% local, 100% free)")
    print("  2) groq (free tier with limits)")
    print("  3) openai")
    print("  4) custom openai-compatible")
    selected = input(f"Choose provider [default: {default}]: ").strip().lower()
    if not selected:
        return default
    aliases = {
        "1": "none",
        "2": "groq",
        "3": "openai",
        "4": "custom",
        "none": "none",
        "groq": "groq",
        "openai": "openai",
        "custom": "custom",
    }
    return aliases.get(selected, default)


def run_setup() -> None:
    values = _parse_env(ENV_FILE)
    capabilities = detect_capabilities()

    print("\nJarvis first-run setup")
    print("Press Enter to keep defaults.")
    print("Free-first mode: Jarvis works without paid APIs and does not need a local LLM.\n")
    print(format_capability_report(capabilities))
    print("\nRecommended for weak PCs: AI off, faster-whisper tiny, basic text-first flow.\n")

    token_default = values.get("ASSISTANT_TOKEN", "")
    if not token_default or token_default == "change-me":
        token_default = secrets.token_hex(16)

    provider_default = values.get("CLOUD_PROVIDER", "none")
    provider = _choose_provider(provider_default)

    api_key_default = values.get("OPENAI_API_KEY", "")
    base_default = values.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model_default = values.get("OPENAI_MODEL", "gpt-4o-mini")
    stt_model_default = values.get("OPENAI_STT_MODEL", "whisper-1")
    tts_model_default = values.get("OPENAI_TTS_MODEL", "canopylabs/orpheus-v1-english")
    tts_voice_default = values.get("OPENAI_TTS_VOICE", "austin")

    if provider == "none":
        api_key_default = ""
        model_default = values.get("OPENAI_MODEL", "")
    elif provider == "groq":
        base_default = "https://api.groq.com/openai/v1"
        model_default = values.get("OPENAI_MODEL", "llama-3.3-70b-versatile")
        stt_model_default = values.get("OPENAI_STT_MODEL", "whisper-large-v3-turbo")
        tts_model_default = values.get("OPENAI_TTS_MODEL", "canopylabs/orpheus-v1-english")
        tts_voice_default = values.get("OPENAI_TTS_VOICE", "austin")

    print("\nCredential links:")
    print("- Ollama local (no key): https://ollama.com/")
    print("- Groq API keys (free tier): https://console.groq.com/keys")
    print("- Piper voices (free): https://huggingface.co/rhasspy/piper-voices")

    out = {
        "ASSISTANT_TOKEN": _prompt("Assistant token", token_default, secret=True),
        "ASSISTANT_NAME": _prompt("Assistant name", values.get("ASSISTANT_NAME", "Jarvis")),
        "USER_NAME": _prompt("Your name", values.get("USER_NAME", "Boss")),
        "CLOUD_PROVIDER": provider,
        "OPENAI_API_KEY": _prompt("Cloud API key (optional)", api_key_default, secret=True),
        "OPENAI_BASE_URL": _prompt("Cloud base URL", base_default),
        "OPENAI_MODEL": _prompt("Cloud model", model_default),
        "OLLAMA_BASE_URL": values.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
        "OLLAMA_MODEL": values.get("OLLAMA_MODEL", "llama3.1:8b"),
        "AI_ROUTE_MODE": values.get("AI_ROUTE_MODE", "off" if provider == "none" else "hybrid"),
        "GREETING_ENABLED": values.get("GREETING_ENABLED", "true"),
        "STT_MODE": values.get("STT_MODE", "cloud" if provider != "none" else "local"),
        "STT_LANGUAGE": values.get("STT_LANGUAGE", "en"),
        "FASTER_WHISPER_MODEL": values.get("FASTER_WHISPER_MODEL", "tiny"),
        "OPENAI_STT_MODEL": stt_model_default,
        "TTS_MODE": values.get("TTS_MODE", "cloud" if provider != "none" else "hybrid"),
        "OPENAI_TTS_MODEL": tts_model_default,
        "OPENAI_TTS_VOICE": tts_voice_default,
        "PIPER_BIN": values.get("PIPER_BIN", "piper"),
        "PIPER_MODEL_PATH": _prompt("Piper model path (optional)", values.get("PIPER_MODEL_PATH", "")),
        "PIPER_SPEAKER_ID": values.get("PIPER_SPEAKER_ID", "0"),
        "REFRESH_INTERVAL": values.get("REFRESH_INTERVAL", "1.0"),
        "CPU_THRESHOLD": values.get("CPU_THRESHOLD", "90"),
        "MEMORY_THRESHOLD": values.get("MEMORY_THRESHOLD", "90"),
        "TOOL_TIMEOUT_SECONDS": values.get("TOOL_TIMEOUT_SECONDS", "8"),
        "ALLOWED_COMMANDS": values.get("ALLOWED_COMMANDS", "ls,pwd,whoami,date,uptime,free,df,ps"),
    }

    content = "\n".join(f"{k}={v}" for k, v in out.items()) + "\n"
    ENV_FILE.write_text(content, encoding="utf-8")

    print("\nSaved .env successfully.")
    print("If cloud key is empty, Jarvis stays in free local-first mode and still works for tools, web search, and text replies.")


if __name__ == "__main__":
    run_setup()
