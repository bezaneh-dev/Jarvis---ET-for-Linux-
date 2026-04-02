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

        fd, out_path = tempfile.mkstemp(prefix="jarvis_", suffix=".wav")
        os.close(fd)

        try:
            for cmd in self._recording_commands(seconds, out_path):
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=seconds + 5)
                if proc.returncode == 0:
                    return True, "Audio recorded.", out_path
            Path(out_path).unlink(missing_ok=True)
            return False, "Audio recording failed. Check your microphone input source.", None
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
            err = self._merge_stt_errors(err, err2)

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

        cloud_failure_summary: str | None = None

        if settings.tts_mode in {"local", "hybrid"}:
            ok, summary = self._speak_with_piper(text)
            if ok:
                return ok, summary
            if settings.tts_mode == "local":
                return False, summary

        if settings.tts_mode in {"cloud", "hybrid"} and settings.openai_api_key:
            ok, summary = self._speak_openai(text)
            if ok:
                return ok, summary
            cloud_failure_summary = summary

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
                if cloud_failure_summary:
                    return True, f"{cloud_failure_summary} Fell back to {cmd}."
                return True, f"Speaking with {cmd}."
            except Exception:
                continue

        if cloud_failure_summary:
            return False, cloud_failure_summary
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
            segments, _ = model.transcribe(
                wav_path,
                language=settings.stt_language,
                task="transcribe",
                beam_size=5,
                best_of=5,
                temperature=0.0,
                vad_filter=False,
                condition_on_previous_text=False,
                initial_prompt=(
                    "Short Linux desktop commands such as open chrome, open firefox, "
                    "open terminal, show cpu and memory, list processes, shutdown, restart, "
                    "sleep, lock, exit, quit."
                ),
            )
            text = " ".join(segment.text.strip() for segment in segments if segment.text).strip()
            if not text:
                return False, "", "I did not hear clear speech. Please try again."
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
        replacements = {
            "jarvis ": "",
            "jarvs ": "",
            "open fire fox": "open firefox",
            "launch fire fox": "launch firefox",
            "open chrome browser": "open chrome",
            "show c p u": "show cpu",
            "c p u": "cpu",
        }
        lowered = f"{text.lower()} "
        for src, dst in replacements.items():
            lowered = lowered.replace(src, f"{dst} ")
        text = lowered.strip()
        text = text.replace(" i ", " I ")
        if text and text[0].islower():
            text = text[0].upper() + text[1:]
        return text

    @staticmethod
    def _recording_commands(seconds: int, out_path: str) -> list[list[str]]:
        commands: list[list[str]] = []
        ffmpeg_path = shutil.which("ffmpeg")
        if ffmpeg_path is not None:
            commands.append(
                [
                    ffmpeg_path,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-f",
                    "pulse",
                    "-i",
                    "default",
                    "-t",
                    str(seconds),
                    "-ac",
                    "1",
                    "-ar",
                    "16000",
                    "-y",
                    out_path,
                ]
            )

        arecord_path = shutil.which("arecord")
        if arecord_path is not None:
            commands.append(
                [
                    arecord_path,
                    "-q",
                    "-f",
                    "S16_LE",
                    "-c",
                    "1",
                    "-r",
                    "16000",
                    "-t",
                    "wav",
                    "-d",
                    str(seconds),
                    out_path,
                ]
            )
        return commands

    @staticmethod
    def _merge_stt_errors(primary: str, fallback: str) -> str:
        primary = primary.strip()
        fallback = fallback.strip()
        if primary and fallback and primary != fallback:
            if "not installed" in fallback.lower() and "not installed" not in primary.lower():
                return primary
            return f"{primary} Fallback STT also failed: {fallback}"
        return primary or fallback

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

    def _speak_openai(self, text: str) -> tuple[bool, str]:
        headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
        url = f"{settings.openai_base_url}/audio/speech"
        fd, audio_path = tempfile.mkstemp(prefix="jarvis_cloud_tts_", suffix=".wav")
        os.close(fd)

        payload = {
            "model": settings.openai_tts_model,
            "voice": settings.openai_tts_voice,
            "input": text,
            "response_format": "wav",
        }

        try:
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(url, headers=headers, json=payload)
                if resp.is_error:
                    return False, self._format_cloud_tts_error(resp)
                Path(audio_path).write_bytes(resp.content)

            ok, summary = self._play_audio_file(audio_path)
            if ok:
                return True, "Speaking with cloud TTS."
            return False, summary
        except Exception as exc:
            return False, f"Cloud TTS failed: {exc}"
        finally:
            Path(audio_path).unlink(missing_ok=True)

    @staticmethod
    def _format_cloud_tts_error(resp: httpx.Response) -> str:
        try:
            payload = resp.json()
        except Exception:
            payload = {}

        message = ""
        if isinstance(payload, dict):
            err = payload.get("error")
            if isinstance(err, dict):
                message = str(err.get("message", "")).strip()

        if "model_terms_required" in str(payload) or "requires terms acceptance" in message.lower():
            return (
                "Cloud TTS needs one-time Groq model approval. "
                "Open https://console.groq.com/playground?model=canopylabs%2Forpheus-v1-english and accept the terms."
            )

        if "decommissioned" in message.lower():
            return f"Cloud TTS failed: {message}"

        if message:
            return f"Cloud TTS failed: {message}"
        return f"Cloud TTS failed with status {resp.status_code}."

    @staticmethod
    def _play_audio_file(audio_path: str) -> tuple[bool, str]:
        player = shutil.which("aplay") or shutil.which("paplay") or shutil.which("ffplay")
        if player is None:
            return False, "Audio player not found. Install alsa-utils or pulseaudio-utils."

        if Path(player).name == "ffplay":
            play_cmd = [player, "-nodisp", "-autoexit", "-loglevel", "quiet", audio_path]
        else:
            play_cmd = [player, audio_path]

        try:
            subprocess.run(play_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30, check=False)
            return True, "Audio playback complete."
        except Exception as exc:
            return False, f"Audio playback failed: {exc}"
