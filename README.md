# Jarvis Lite Linux (MVP)

A local-first PC assistant backend for Linux with:
- system metrics and websocket alerts
- tool-based command execution with allowlist
- process listing and kill (confirmation required)
- system actions (shutdown/restart/sleep/lock) with mandatory confirmation
- no-LLM-required terminal mode with optional AI providers
- web research helper with source links and offline-friendly summarizing
- optional voice record/transcribe and text-to-speech endpoints
- startup capability report for weak PCs and free-first setups

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
- starts the unified terminal mode

If `.env` exists but creds are incomplete, launcher asks if you want to run setup wizard.

## Free credentials (recommended)

Use this stack to keep the project free:
- LLM: optional only; Jarvis works without one
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

# Jarvis Lite (Linux)

Jarvis Lite is a **local-first** Jarvis-style assistant for Linux. It focuses on **reliable PC actions** (metrics, safe commands, app launch, process control) and optionally adds **voice input/output**, **web research**, and an **LLM brain** (local Ollama first, optional cloud fallback).

This repo includes:
- Voice-first terminal mode (recommended)
- HTTP API (FastAPI) with token guard
- Safety confirmation gate for high-risk actions

## Quick start (one command)

```bash
./jarvis
```

What it does:
- Creates `.venv` if missing
- Installs dependencies
- Runs first-time setup wizard (writes `.env`)
- Starts voice-first Jarvis mode

If you want **100% free/local**, choose provider `none` in the wizard.

## Features

- System metrics: CPU/RAM/Disk + `/ws/metrics` alerts
- Process tools: list processes; kill by PID (**confirmation required**)
- System actions: shutdown/restart/sleep/lock (**confirmation required**)
- Safe shell runner: `run <command>` restricted by `ALLOWED_COMMANDS`
- Web research: DuckDuckGo search + short summary + sources (no API key required)
- Voice:
  - Record from mic via `arecord` (optional)
  - STT: local-first (faster-whisper / whisper CLI) with optional cloud fallback
  - TTS: Piper (best quality) or fallback to `speech-dispatcher` / `espeak-ng`
- Greeting on first interaction (`GREETING_ENABLED=true`)

## Requirements

- Linux
- Python 3.10+ recommended
- `python3-venv` available

Optional (voice):

```bash
sudo apt update
sudo apt install -y alsa-utils speech-dispatcher espeak-ng
```

## Setup wizard

The wizard runs automatically on first launch, and writes `.env`. You can re-run it anytime:

```bash
source .venv/bin/activate
python3 -m app.setup_wizard
```

Useful links:
- Groq API keys (optional free tier): https://console.groq.com/keys
- Piper voices (free): https://huggingface.co/rhasspy/piper-voices
- Ollama (optional local LLM): https://ollama.com/

## Usage

### 1) Voice-first mode (recommended)

Start:

```bash
./jarvis
```

Controls:
- Press **Enter**: records voice and replies (if mic is available)
- Type text: sends as a message
- Type `exit`: quit

Example commands:
- `show cpu and memory`
- `list top processes`
- `run df -h`
- `open firefox`
- `search web linux swap tuning`
- `shutdown` (will ask for confirmation)

### 2) API mode (FastAPI)

Run server:

```bash
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8010
```

Token: set `ASSISTANT_TOKEN` in `.env`, then call endpoints with `?x_token=TOKEN`.

Examples:

```bash
curl "http://127.0.0.1:8010/health"

curl "http://127.0.0.1:8010/capabilities?x_token=TOKEN"
curl "http://127.0.0.1:8010/metrics?x_token=TOKEN"

curl -X POST "http://127.0.0.1:8010/assistant/message?x_token=TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message":"show cpu and memory"}'

curl "http://127.0.0.1:8010/web/research?x_token=TOKEN&query=linux+cpu+optimization"

curl -X POST "http://127.0.0.1:8010/voice/chat?x_token=TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"seconds":5,"speak_reply":true}'
```

If a request requires confirmation you’ll get `pending_action_id`, then confirm it:

```bash
curl -X POST "http://127.0.0.1:8010/assistant/confirm?x_token=TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"action_id":"YOUR_ID","approve":true}'
```

## Security model (important)

- Do not expose this service to the public internet.
- Dangerous actions (shutdown/restart/sleep/lock, kill PID) require explicit confirmation.
- Shell execution is restricted to an allowlist (`ALLOWED_COMMANDS`).

## Making the voice more human (Piper)

1) Install Piper (method varies by distro) and download a `.onnx` voice model from:
https://huggingface.co/rhasspy/piper-voices

2) Set in `.env`:

```bash
TTS_MODE=local
PIPER_BIN=piper
PIPER_MODEL_PATH=/absolute/path/to/voice-model.onnx
PIPER_SPEAKER_ID=0
```

If Piper is not configured, Jarvis falls back to `speech-dispatcher` / `espeak-ng`.

## Troubleshooting

- Mic recording fails: install `alsa-utils` (needs `arecord`).
- No spoken output: install `speech-dispatcher` and `espeak-ng`, or configure Piper.
- Weak PC: keep `AI_ROUTE_MODE=off` and use web research + tool commands.

## Development

Run tests:

```bash
source .venv/bin/activate
pytest -q
```
