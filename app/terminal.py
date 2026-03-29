from __future__ import annotations

from pathlib import Path

from app.assistant_core import AssistantCore
from app.capabilities import detect_capabilities, format_capability_report
from app.config import settings
from app.voice import VoiceService


def main() -> None:
    core = AssistantCore()
    voice = VoiceService()
    capabilities = detect_capabilities()

    print(f"\n{settings.assistant_name} Terminal")
    print(format_capability_report(capabilities))
    print("Commands: Enter=/voice | plain text=message | /speak <text>=read aloud | help=examples | exit=quit\n")

    while True:
        user_in = input("you> ").strip()
        if user_in.lower() in {"exit", "quit"}:
            print("bye")
            break

        if user_in in {"", "/voice"}:
            message = _capture_voice_input(voice)
            if message is None:
                continue
        elif user_in.startswith("/speak "):
            text = user_in[len("/speak "):].strip()
            ok, summary = voice.speak_text(text)
            print(f"{settings.assistant_name}> {summary}")
            if not ok:
                print(f"{settings.assistant_name}> Falling back to text-only mode for now.")
            continue
        else:
            message = user_in

        resp = core.handle_message(message)
        print(f"{settings.assistant_name}> {resp.reply}")

        if resp.action_required and resp.pending_action_id:
            expires = f" ({resp.pending_action_expires_in}s left)" if resp.pending_action_expires_in is not None else ""
            confirm = input(f"confirm action{expires}? (yes/no)> ").strip().lower()
            approved = confirm in {"y", "yes"}
            result = core.confirm_action(resp.pending_action_id, approved)
            print(f"{settings.assistant_name}> {result.summary}")


def _capture_voice_input(voice: VoiceService) -> str | None:
    ok, summary, wav_path = voice.record_wav(seconds=5)
    if not ok or wav_path is None:
        print(f"{settings.assistant_name}> {summary}")
        return None

    try:
        t_ok, text, err = voice.transcribe_file(wav_path)
    finally:
        Path(wav_path).unlink(missing_ok=True)

    if not t_ok:
        print(f"{settings.assistant_name}> {err}")
        return None

    print(f"heard> {text}")
    return text
