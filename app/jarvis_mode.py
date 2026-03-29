from __future__ import annotations

from pathlib import Path

from app.assistant_core import AssistantCore
from app.config import settings
from app.voice import VoiceService


def _ask_confirm() -> bool:
    ans = input("confirm action? (yes/no)> ").strip().lower()
    return ans in {"y", "yes"}


def _print_reply(reply: str) -> None:
    print(f"{settings.assistant_name}> {reply}")


def main() -> None:
    core = AssistantCore()
    voice = VoiceService()

    print("\nJarvis voice mode")
    print("Press Enter to talk with microphone.")
    print("Type text to send text command.")
    print("Type 'exit' to quit.\n")

    while True:
        user_in = input("you> ").strip()
        if user_in.lower() in {"exit", "quit"}:
            print("bye")
            break

        if not user_in:
            ok, summary, wav_path = voice.record_wav(seconds=5)
            if not ok or wav_path is None:
                print(f"{settings.assistant_name}> {summary}")
                continue
            try:
                t_ok, text, err = voice.transcribe_file(wav_path)
            finally:
                Path(wav_path).unlink(missing_ok=True)

            if not t_ok:
                print(f"{settings.assistant_name}> {err}")
                continue

            print(f"heard> {text}")
            message = text
        else:
            message = user_in

        resp = core.handle_message(message)
        _print_reply(resp.reply)

        if resp.action_required and resp.pending_action_id:
            approved = _ask_confirm()
            result = core.confirm_action(resp.pending_action_id, approved)
            _print_reply(result.summary)

        ok, summary = voice.speak_text(resp.reply)
        if not ok:
            print(f"{settings.assistant_name}> {summary}")


if __name__ == "__main__":
    main()
