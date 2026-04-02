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
    welcome = _startup_greeting()

    print(f"\n{settings.assistant_name} Terminal")
    print(f"{settings.assistant_name}> {welcome}")
    print(format_capability_report(capabilities))
    if settings.voice_only_mode:
        print("Voice mode: speak naturally. Say 'exit' or 'quit' to stop.\n")
    else:
        print("Commands: Enter=/voice | plain text=message | /speak <text>=read aloud | help=examples | exit=quit\n")
    _speak_startup_greeting(voice, welcome)

    if settings.voice_only_mode:
        try:
            _run_voice_loop(core, voice)
        except KeyboardInterrupt:
            print(f"\n{settings.assistant_name}> Goodbye.")
        return

    try:
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
                _speak_reply(voice, result.summary)
    except KeyboardInterrupt:
        print(f"\n{settings.assistant_name}> Goodbye.")


def _run_voice_loop(core: AssistantCore, voice: VoiceService) -> None:
    while True:
        message = _capture_voice_input(voice)
        if message is None:
            continue

        if _is_exit_command(message):
            goodbye = "Goodbye."
            print(f"{settings.assistant_name}> {goodbye}")
            _speak_reply(voice, goodbye)
            break

        resp = core.handle_message(message)
        print(f"{settings.assistant_name}> {resp.reply}")
        _speak_reply(voice, resp.reply)

        if resp.action_required and resp.pending_action_id:
            approved = _capture_voice_confirmation(voice, resp.pending_action_id)
            result = core.confirm_action(resp.pending_action_id, approved)
            print(f"{settings.assistant_name}> {result.summary}")
            _speak_reply(voice, result.summary)


def _capture_voice_input(voice: VoiceService) -> str | None:
    print(f"{settings.assistant_name}> Listening...")
    ok, summary, wav_path = voice.record_wav(seconds=settings.voice_input_seconds)
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


def _capture_voice_confirmation(voice: VoiceService, action_id: str) -> bool:
    prompt = "Confirmation required. Please say yes or no."
    print(f"{settings.assistant_name}> {prompt}")
    _speak_reply(voice, prompt)

    for _ in range(2):
        message = _capture_voice_input(voice)
        if message is None:
            continue
        if _is_positive_reply(message):
            return True
        if _is_negative_reply(message):
            return False
        retry = "I did not catch that. Please say yes or no."
        print(f"{settings.assistant_name}> {retry}")
        _speak_reply(voice, retry)

    return False


def _startup_greeting() -> str:
    return (
        f"Welcome {settings.user_name}. I am {settings.assistant_name}. "
        "I am ready when you are."
    )


def _speak_startup_greeting(voice: VoiceService, message: str) -> None:
    if not settings.greeting_enabled or not settings.startup_voice_greeting:
        return

    ok, summary = voice.speak_text(message)
    if not ok:
        print(f"{settings.assistant_name}> {summary}")


def _speak_reply(voice: VoiceService, message: str) -> None:
    ok, summary = voice.speak_text(message)
    if not ok:
        print(f"{settings.assistant_name}> {summary}")


def _is_exit_command(message: str) -> bool:
    normalized = " ".join(message.lower().split())
    return normalized in {"exit", "quit", "goodbye", "stop listening", "stop"}


def _is_positive_reply(message: str) -> bool:
    normalized = " ".join(message.lower().split())
    return normalized in {"yes", "yeah", "yep", "confirm", "approve", "do it"}


def _is_negative_reply(message: str) -> bool:
    normalized = " ".join(message.lower().split())
    return normalized in {"no", "nope", "cancel", "deny", "stop"}
