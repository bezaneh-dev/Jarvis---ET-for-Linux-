# Jarvis Lite Linux

> A free-first Linux assistant built for weak PCs.
> No paid API required. No local LLM required. Still useful.

## Why This Project Exists

Jarvis Lite is for people who want a personal Linux assistant without:

- paying for APIs
- running a heavy local LLM
- needing a powerful machine

It is designed to be **tool-first**, **safe by default**, and **actually usable offline** for common desktop tasks.

## What It Can Do

- Show CPU, memory, disk, and system health
- List running processes
- Kill a process with confirmation
- Run safe allowlisted shell commands
- Open desktop apps
- Do web research with source links
- Handle optional voice input and text-to-speech
- Expose an HTTP API for integrations

## Free-First Design

Jarvis Lite works well with this setup:

- `AI_ROUTE_MODE=off`
- no cloud key
- no Ollama
- optional `faster-whisper` for speech-to-text
- optional Piper or `espeak-ng` for voice output

That means the assistant still works for:

- local system tasks
- command execution through the allowlist
- process management
- web search with sources
- text-based interaction

## Quick Start

Run:

```bash
cd '/home/kali/Projects/Robot '
./jarvis
```

What happens automatically:

- a `.venv` is created if missing
- dependencies are installed
- the setup wizard runs on first launch
- Jarvis starts in the unified terminal mode

## Terminal Experience

The terminal mode is the main UI.

You can:

- press `Enter` or type `/voice` to record from the microphone
- type a normal message for text commands
- type `/speak hello` to test text-to-speech
- type `help` to see built-in examples
- type `exit` to quit

Example commands:

```text
show cpu and memory
list top processes
run df -h
run uptime
open firefox
search web linux swap tuning
shutdown
```

## Setup Notes

The setup wizard writes `.env` for you:

```bash
source .venv/bin/activate
python3 -m app.setup_wizard
```

Recommended weak-PC defaults:

```env
AI_ROUTE_MODE=off
STT_MODE=local
FASTER_WHISPER_MODEL=tiny
TTS_MODE=hybrid
```

If you choose provider `none`, Jarvis stays fully free-first.

Detailed `.env` setup help lives in:

- `ENV_SETUP.md`

## Optional Voice Stack

Install basic voice packages:

```bash
sudo apt update
sudo apt install -y alsa-utils pulseaudio-utils speech-dispatcher espeak-ng
```

Optional upgrades:

- `faster-whisper` for offline speech-to-text
- Piper for better voice output
- `xdotool` or `wmctrl` for desktop control like minimize, close, and typing into the active window

Piper setup example:

```env
TTS_MODE=local
PIPER_BIN=piper
PIPER_MODEL_PATH=/absolute/path/to/voice-model.onnx
PIPER_SPEAKER_ID=0
```

Helpful links:

- Ollama: https://ollama.com/
- Piper voices: https://huggingface.co/rhasspy/piper-voices
- Groq keys: https://console.groq.com/keys

Where to change things in this repo:

- Voice recording / STT / TTS: `app/voice.py`
- Command obedience and routing: `app/assistant_core.py`
- Safe shell and app launching: `app/tools.py`
- AI provider settings: `app/config.py` and `.env`
- First-run setup helper: `app/setup_wizard.py`

Free model/API options that work with this project:

- Fully offline and free: `AI_ROUTE_MODE=off` plus `faster-whisper` and local TTS
- Free local AI: install Ollama and keep `AI_ROUTE_MODE=local` or `hybrid`
- Free cloud tier: set `CLOUD_PROVIDER=groq`, get a key from `https://console.groq.com/keys`, and use the OpenAI-compatible base URL already supported by the app

Suggested free cloud setup for weak machines:

```env
CLOUD_PROVIDER=groq
OPENAI_API_KEY=your_groq_key
OPENAI_BASE_URL=https://api.groq.com/openai/v1
OPENAI_MODEL=llama-3.3-70b-versatile
OPENAI_STT_MODEL=whisper-large-v3-turbo
OPENAI_TTS_MODEL=playai-tts
OPENAI_TTS_VOICE=Fritz-PlayAI
AI_ROUTE_MODE=cloud
STT_MODE=cloud
TTS_MODE=cloud
```

For desktop actions on Linux:

```bash
sudo apt install -y xdotool wmctrl
```

Example commands after that:

- `minimize current window`
- `maximize current window`
- `close current window`
- `type hello world`

## API Mode

Start the API:

```bash
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8010
```

Set `ASSISTANT_TOKEN` in `.env`, then call endpoints with `?x_token=TOKEN`.

Useful endpoints:

- `GET /health`
- `GET /capabilities`
- `GET /metrics`
- `POST /assistant/message`
- `POST /assistant/confirm`
- `GET /web/research`
- `POST /voice/record-transcribe`
- `POST /voice/chat`
- `POST /voice/speak`

Example:

```bash
curl "http://127.0.0.1:8010/capabilities?x_token=TOKEN"

curl -X POST "http://127.0.0.1:8010/assistant/message?x_token=TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message":"show cpu and memory"}'
```

## Security

Important before you use or share this:

- Do not expose this service to the public internet.
- Keep it on trusted local networks only.
- High-risk actions require confirmation, but this is still a machine-control tool.
- Shell execution is limited by `ALLOWED_COMMANDS`, so review that list before adding new commands.
- `.env` contains local secrets and should never be committed.

## Push-Safe Repo Notes

Current repo hygiene is set up for GitHub:

- `.env` is ignored
- `.venv/` is ignored
- `__pycache__/` and build/cache files are ignored
- generated audio/model files are ignored
- the tracked repo contains placeholders, not real API keys

Before pushing, keep using:

```bash
git status
```

and make sure `.env` does not appear in the staged files.

## Troubleshooting

- No microphone recording: install `alsa-utils` for `arecord`
- No spoken output: install `speech-dispatcher` and `espeak-ng`, or configure Piper
- Weak PC: keep `AI_ROUTE_MODE=off`
- No LLM installed: that is okay, Jarvis will fall back to local guidance

## Development

Run tests:

```bash
source .venv/bin/activate
pytest -q
```

Current test status in this repo: `10 passed`
