from app.terminal import (
    _capture_voice_input,
    _is_exit_command,
    _is_negative_reply,
    _is_positive_reply,
    _looks_like_bad_repeat,
    _startup_greeting,
    _speak_startup_greeting,
    main,
)


def test_startup_greeting_mentions_welcome() -> None:
    greeting = _startup_greeting()

    assert "Welcome" in greeting
    assert "ready when you are" in greeting


def test_startup_voice_greeting_ignores_missing_tts(monkeypatch, capsys) -> None:
    class FakeVoice:
        def speak_text(self, _message: str) -> tuple[bool, str]:
            return False, "No TTS engine found."

    class FakeSettings:
        greeting_enabled = True
        startup_voice_greeting = True
        assistant_name = "Jarvis"

    monkeypatch.setattr("app.terminal.settings", FakeSettings())

    _speak_startup_greeting(FakeVoice(), "Welcome")

    output = capsys.readouterr().out
    assert "No TTS engine found." in output


def test_exit_command_detection() -> None:
    assert _is_exit_command("exit") is True
    assert _is_exit_command("stop listening") is True
    assert _is_exit_command("open chrome") is False


def test_voice_confirmation_keywords() -> None:
    assert _is_positive_reply("yes") is True
    assert _is_positive_reply("do it") is True
    assert _is_negative_reply("no") is True
    assert _is_negative_reply("cancel") is True


def test_main_handles_keyboard_interrupt_in_voice_mode(monkeypatch, capsys) -> None:
    monkeypatch.setattr("app.terminal.detect_capabilities", lambda: object())
    monkeypatch.setattr("app.terminal.format_capability_report", lambda _caps: "System ready:")

    class FakeCore:
        pass

    class FakeVoice:
        def speak_text(self, _message: str) -> tuple[bool, str]:
            return True, "ok"

    class FakeSettings:
        assistant_name = "Jarvis"
        user_name = "Beza"
        voice_only_mode = True
        greeting_enabled = True
        startup_voice_greeting = False

    monkeypatch.setattr("app.terminal.AssistantCore", FakeCore)
    monkeypatch.setattr("app.terminal.VoiceService", FakeVoice)
    monkeypatch.setattr("app.terminal.settings", FakeSettings())
    monkeypatch.setattr("app.terminal._run_voice_loop", lambda *_args: (_ for _ in ()).throw(KeyboardInterrupt()))

    main()

    output = capsys.readouterr().out
    assert "Goodbye." in output


def test_capture_voice_input_prints_heard_text(monkeypatch, capsys, tmp_path) -> None:
    audio = tmp_path / "sample.wav"
    audio.write_bytes(b"fake")

    class FakeVoice:
        def record_wav(self, seconds: int = 0):
            return True, "ok", str(audio)

        def transcribe_file(self, _wav_path: str):
            return True, "open firefox", ""

    class FakeSettings:
        assistant_name = "Jarvis"
        voice_input_seconds = 4
        voice_echo_input = True
        voice_confirm_transcript = False

    monkeypatch.setattr("app.terminal.settings", FakeSettings())

    text = _capture_voice_input(FakeVoice())

    output = capsys.readouterr().out
    assert text == "open firefox"
    assert "I heard: open firefox" in output


def test_bad_repeat_detection_flags_short_repeats() -> None:
    assert _looks_like_bad_repeat("thank you", 3) is True
    assert _looks_like_bad_repeat("open firefox", 3) is False
