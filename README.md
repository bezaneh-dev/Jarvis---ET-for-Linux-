# Jarvis Lite Linux (MVP)

A local-first PC assistant backend for Linux with:
- system metrics and websocket alerts
- tool-based command execution with allowlist
- process listing and kill (confirmation required)
- system actions (shutdown/restart/sleep/lock) with mandatory confirmation
- hybrid AI routing (Ollama first, cloud fallback)
- web research helper with source links
- optional voice record/transcribe and text-to-speech endpoints
- first-interaction greeting behavior

## Quick start

1. Run one command.

```bash
cd '/home/kali/Projects/Robot '
./jarvis
```

What this does automatically:
- creates `.venv` if missing
- installs dependencies
- asks for credentials/settings on first run (free-first defaults)
- starts voice-first Jarvis chat mode

If `.env` exists but creds are incomplete, launcher asks if you want to run setup wizard.

## Free credentials (recommended)

Use this stack to keep the project free:
- LLM: Ollama local (no key) https://ollama.com/
- STT: faster-whisper local (no key)
- TTS: Piper local voice model (no key) https://huggingface.co/rhasspy/piper-voices

Optional free cloud fallback (rate-limited):
- Groq API key page: https://console.groq.com/keys
- Groq quickstart: https://console.groq.com/docs/quickstart

Free note:
- Local components above are free to run.
- Cloud free tiers can change over time, so verify current limits in provider docs.

Manual setup wizard:

```bash
source .venv/bin/activate
python3 -m app.setup_wizard
```

## Make voice sound more human

Best quality currently comes from Piper TTS.

1. Install audio tools:

```bash
sudo apt update
sudo apt install -y alsa-utils pulseaudio-utils speech-dispatcher espeak-ng
```

2. Install Piper (example if available in your distro), then download a voice model.
3. Set these in `.env`:

```bash
TTS_MODE=local
PIPER_BIN=piper
PIPER_MODEL_PATH=/absolute/path/to/voice-model.onnx
PIPER_SPEAKER_ID=0
```

If Piper is not configured, the system falls back to `spd-say`/`espeak-ng`.

## Improve understanding (speech-to-text)

For better recognition, use faster-whisper locally or cloud STT fallback.

1. Optional local STT install:

```bash
source .venv/bin/activate
pip install faster-whisper
```

2. Set `.env`:

```bash
STT_MODE=hybrid
FASTER_WHISPER_MODEL=small
STT_LANGUAGE=en
OPENAI_API_KEY=your_key_if_you_want_cloud_fallback
OPENAI_STT_MODEL=whisper-1
```

`small` gives good quality; use `medium` for better quality if your machine can handle it.

Run CLI mode:

```bash
source .venv/bin/activate
python3 -m app.cli
```

## Test endpoints

Replace TOKEN with your `.env` token.

```bash
curl "http://127.0.0.1:8010/health"
curl "http://127.0.0.1:8010/metrics?x_token=TOKEN"

curl -X POST "http://127.0.0.1:8010/assistant/message?x_token=TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message":"show cpu and memory"}'

curl -X POST "http://127.0.0.1:8010/assistant/message?x_token=TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message":"shutdown"}'

curl "http://127.0.0.1:8010/web/research?x_token=TOKEN&query=linux+cpu+optimization"

curl -X POST "http://127.0.0.1:8010/voice/record-transcribe?x_token=TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"seconds":4}'

curl -X POST "http://127.0.0.1:8010/voice/chat?x_token=TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"seconds":5,"speak_reply":true}'

curl -X POST "http://127.0.0.1:8010/voice/speak?x_token=TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello from Jarvis Lite"}'
```

If an action requires confirmation, you will receive `pending_action_id`.

```bash
curl -X POST "http://127.0.0.1:8010/assistant/confirm?x_token=TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"action_id":"YOUR_ID","approve":true}'
```

## Notes

- Keep this backend on trusted networks only.
- High-risk actions are blocked until explicit confirmation.
- Shell command execution is restricted by `ALLOWED_COMMANDS`.
- Voice recording uses `arecord` (install with `alsa-utils`).
- Voice speak uses Piper when configured, else `spd-say`, `espeak-ng`, or `espeak`.
- Assistant greets on first interaction when `GREETING_ENABLED=true`.

## How to use now

1. Start Jarvis with one command:

```bash
cd '/home/kali/Projects/Robot '
./jarvis
```

If you want zero cloud credentials, choose `none` provider in setup wizard.

2. Jarvis greets you automatically on first interaction.

3. Interaction flow:
- press Enter: records microphone and responds with voice
- type text: sends text command
- type `exit`: quits

4. Optional API mode (if you still want HTTP endpoints):

```bash
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8010
```
