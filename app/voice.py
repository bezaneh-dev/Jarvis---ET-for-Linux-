from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
import re

import httpx

from app.config import settings


class VoiceService:
    _faster_whisper_model = None
    _faster_whisper_model_name: str | None = None

    def record_wav(self, seconds: int = 4) -> tuple[bool, str, str | None]:
        if seconds < 1 or seconds > 20:
            return False, "Recording seconds must be between 1 and 20.", None

        arecord_path = shutil.which("arecord")
        if arecord_path is None:
            return False, "arecord is not installed. Install alsa-utils.", None

        fd, out_path = tempfile.mkstemp(prefix="jarvis_", suffix=".wav")
        os.close(fd)

        cmd = [
            arecord_path,
            "-f",
            "cd",
            "-t",
            "wav",
            "-d",
            str(seconds),
            out_path,
        ]

        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=seconds + 3)
            if proc.returncode != 0:
                Path(out_path).unlink(missing_ok=True)
                return False, proc.stderr.strip() or "Audio recording failed.", None
            return True, "Audio recorded.", out_path
        except Exception as exc:
            Path(out_path).unlink(missing_ok=True)
            return False, f"Recording failed: {exc}", None

    def transcribe_file(self, wav_path: str) -> tuple[bool, str, str]:
        if not Path(wav_path).exists():
            return False, "", "Audio file not found."

        if settings.stt_mode in {"local", "hybrid"}:
            ok, text, err = self._transcribe_faster_whisper(wav_path)
            if ok:
                return True, self._normalize_transcript(text), ""

            ok, text, err2 = self._transcribe_whisper_cli(wav_path)
            if ok:
                return True, self._normalize_transcript(text), ""
            err = err2 or err

            if settings.stt_mode == "local":
                return False, "", err or "Local STT failed."

        if settings.openai_api_key:
            ok, text, err = self._transcribe_openai(wav_path)
            if ok:
                return True, self._normalize_transcript(text), ""
            return False, "", err

        return False, "", "No STT backend available. Install faster-whisper or whisper CLI for fully free voice input."

    def speak_text(self, text: str) -> tuple[bool, str]:
        text = text.strip()
        if not text:
            return False, "Text is empty."

        if settings.tts_mode in {"local", "hybrid"}:
            ok, summary = self._speak_with_piper(text)
            if ok:
                return ok, summary
            if settings.tts_mode == "local":
                return False, summary

        for cmd in ["spd-say", "espeak-ng", "espeak"]:
            binary = shutil.which(cmd)
            if binary is None:
                continue
            try:
                subprocess.run(
                    [binary, text],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=15,
                    check=False,
                )
                return True, f"Speaking with {cmd}."
            except Exception:
                continue

        return False, "No TTS engine found. Text reply is still available."

    def _transcribe_faster_whisper(self, wav_path: str) -> tuple[bool, str, str]:
        try:
            from faster_whisper import WhisperModel
        except Exception:
            return False, "", "faster-whisper is not installed."

        try:
            if (
                self.__class__._faster_whisper_model is None
                or self.__class__._faster_whisper_model_name != settings.faster_whisper_model
            ):
                self.__class__._faster_whisper_model = WhisperModel(
                    settings.faster_whisper_model,
                    device="auto",
                    compute_type="int8",
                )
                self.__class__._faster_whisper_model_name = settings.faster_whisper_model
            model = self.__class__._faster_whisper_model
            segments, _ = model.transcribe(wav_path, language=settings.stt_language, vad_filter=True)
            text = " ".join(segment.text.strip() for segment in segments if segment.text).strip()
            if not text:
                return False, "", "faster-whisper produced empty text."
            return True, text, ""
        except Exception as exc:
            return False, "", f"faster-whisper failed: {exc}"

    def _transcribe_whisper_cli(self, wav_path: str) -> tuple[bool, str, str]:
        whisper_cli = shutil.which("whisper")
        if whisper_cli is None:
            return False, "", "whisper CLI is not installed."

        cmd = [
            whisper_cli,
            wav_path,
            "--language",
            settings.stt_language,
            "--task",
            "transcribe",
            "--fp16",
            "False",
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if proc.returncode == 0 and proc.stdout.strip():
                return True, proc.stdout.strip(), ""
            return False, "", proc.stderr.strip() or "whisper CLI failed."
        except Exception as exc:
            return False, "", f"whisper CLI failed: {exc}"

    def _normalize_transcript(self, text: str) -> str:
        text = re.sub(r"\s+", " ", text).strip()
        text = text.replace(" i ", " I ")
        if text and text[0].islower():
            text = text[0].upper() + text[1:]
        return text

    def _speak_with_piper(self, text: str) -> tuple[bool, str]:
        piper_bin = shutil.which(settings.piper_bin)
        model_path = settings.piper_model_path.strip()
        if piper_bin is None:
            return False, "Piper binary not found."
        if not model_path:
            return False, "PIPER_MODEL_PATH is not configured."
        if not Path(model_path).exists():
            return False, "Piper model file not found."

        fd, wav_path = tempfile.mkstemp(prefix="jarvis_tts_", suffix=".wav")
        os.close(fd)

        try:
            cmd = [
                piper_bin,
                "--model",
                model_path,
                "--speaker",
                str(settings.piper_speaker_id),
                "--output_file",
                wav_path,
            ]
            proc = subprocess.run(cmd, input=text, capture_output=True, text=True, timeout=30)
            if proc.returncode != 0:
                return False, proc.stderr.strip() or "Piper synthesis failed."

            player = shutil.which("aplay") or shutil.which("paplay") or shutil.which("ffplay")
            if player is None:
                return False, "Audio player not found. Install alsa-utils or pulseaudio-utils."

            if Path(player).name == "ffplay":
                play_cmd = [player, "-nodisp", "-autoexit", "-loglevel", "quiet", wav_path]
            else:
                play_cmd = [player, wav_path]

            subprocess.run(play_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30, check=False)
            return True, "Speaking with piper."
        except Exception as exc:
            return False, f"Piper TTS failed: {exc}"
        finally:
            Path(wav_path).unlink(missing_ok=True)

    def _transcribe_openai(self, wav_path: str) -> tuple[bool, str, str]:
        headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
        url = f"{settings.openai_base_url}/audio/transcriptions"
        try:
            with open(wav_path, "rb") as f:
                files = {"file": (Path(wav_path).name, f, "audio/wav")}
                data = {"model": settings.openai_stt_model}
                with httpx.Client(timeout=60.0) as client:
                    resp = client.post(url, headers=headers, files=files, data=data)
                    resp.raise_for_status()
                    payload = resp.json()
            text = str(payload.get("text", "")).strip()
            if not text:
                return False, "", "Transcription returned empty text."
            return True, text, ""
        except Exception as exc:
            return False, "", f"Cloud transcription failed: {exc}"
