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
