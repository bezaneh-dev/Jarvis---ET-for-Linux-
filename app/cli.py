from __future__ import annotations

from app.config import settings
from app.assistant_core import AssistantCore
from app.voice import VoiceService


def main() -> None:
    core = AssistantCore()
    voice = VoiceService()

    print("Jarvis Lite CLI")
    if settings.greeting_enabled:
        print(f"{settings.assistant_name}> Hello {settings.user_name}. I am online and ready.")
    print("Type 'exit' to quit.")
    print("Prefix with '/speak ' to read output aloud.")

    while True:
        user = input("you> ").strip()
        if not user:
            continue
        if user.lower() in {"exit", "quit"}:
            print("bye")
            break

        speak_output = False
        if user.startswith("/speak "):
            speak_output = True
            user = user[len("/speak "):].strip()

        resp = core.handle_message(user)
        print(f"jarvis> {resp.reply}")

        if resp.action_required and resp.pending_action_id:
            ans = input("confirm action? (yes/no)> ").strip().lower()
            approved = ans in {"y", "yes"}
            result = core.confirm_action(resp.pending_action_id, approved)
            print(f"jarvis> {result.summary}")

        if speak_output:
            ok, summary = voice.speak_text(resp.reply)
            if not ok:
                print(f"jarvis> {summary}")


if __name__ == "__main__":
    main()
