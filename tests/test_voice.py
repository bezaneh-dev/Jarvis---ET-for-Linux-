from app.voice import VoiceService


def test_missing_tts_is_nonfatal(monkeypatch) -> None:
    monkeypatch.setattr("app.voice.shutil.which", lambda _name: None)

    ok, summary = VoiceService().speak_text("hello")

    assert ok is False
    assert "Text reply is still available" in summary


def test_faster_whisper_model_is_cached(monkeypatch, tmp_path) -> None:
    audio = tmp_path / "sample.wav"
    audio.write_bytes(b"fake")

    created = {"count": 0}

    class FakeSegment:
        text = "hello"

    class FakeModel:
        def __init__(self, *args, **kwargs) -> None:
            created["count"] += 1

        def transcribe(self, *args, **kwargs):
            return [FakeSegment()], None

    monkeypatch.setattr("app.voice.VoiceService._faster_whisper_model", None, raising=False)
    monkeypatch.setattr("app.voice.VoiceService._faster_whisper_model_name", None, raising=False)
    monkeypatch.setitem(__import__("sys").modules, "faster_whisper", type("M", (), {"WhisperModel": FakeModel})())

    voice = VoiceService()
    first = voice.transcribe_file(str(audio))
    second = voice.transcribe_file(str(audio))

    assert first[0] is True
    assert second[0] is True
    assert created["count"] == 1


def test_transcribe_prefers_primary_error_over_missing_cli(monkeypatch, tmp_path) -> None:
    audio = tmp_path / "sample.wav"
    audio.write_bytes(b"fake")

    voice = VoiceService()
    monkeypatch.setattr(voice, "_transcribe_faster_whisper", lambda _path: (False, "", "I did not hear clear speech. Please try again."))
    monkeypatch.setattr(voice, "_transcribe_whisper_cli", lambda _path: (False, "", "whisper CLI is not installed."))

    ok, text, err = voice.transcribe_file(str(audio))

    assert ok is False
    assert text == ""
    assert err == "I did not hear clear speech. Please try again."


def test_transcript_normalization_fixes_common_spoken_commands() -> None:
    voice = VoiceService()

    text = voice._normalize_transcript("jarvis open fire fox")

    assert text == "Open firefox"
