# Environment Setup Guide

This project reads its environment variables from:

- `/home/kali/Projects/Robot /.env`

If `.env` does not exist yet, copy from:

- `/home/kali/Projects/Robot /.env.example`

Example:

```bash
cd '/home/kali/Projects/Robot '
cp .env.example .env
```

## Best Setup For Your Weak Machine

Use Groq for cloud AI, cloud speech-to-text, and cloud text-to-speech.

```env
ASSISTANT_TOKEN=make-your-own-random-secret
REFRESH_INTERVAL=1.0
CPU_THRESHOLD=90
MEMORY_THRESHOLD=90
TOOL_TIMEOUT_SECONDS=8

OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.1:8b

CLOUD_PROVIDER=groq
OPENAI_API_KEY=paste-your-groq-api-key-here
OPENAI_BASE_URL=https://api.groq.com/openai/v1
OPENAI_MODEL=llama-3.3-70b-versatile
AI_ROUTE_MODE=cloud

GREETING_ENABLED=true
STARTUP_VOICE_GREETING=true
VOICE_ONLY_MODE=true
VOICE_INPUT_SECONDS=6
ASSISTANT_NAME=Jarvis
USER_NAME=Boss

STT_MODE=cloud
STT_LANGUAGE=en
FASTER_WHISPER_MODEL=base.en
OPENAI_STT_MODEL=whisper-large-v3-turbo

TTS_MODE=cloud
OPENAI_TTS_MODEL=canopylabs/orpheus-v1-english
OPENAI_TTS_VOICE=austin
PIPER_BIN=piper
PIPER_MODEL_PATH=
PIPER_SPEAKER_ID=0

ALLOWED_COMMANDS=ls,pwd,whoami,date,uptime,free,df,ps
```

## Where To Get Each Value

### Needs a website

`OPENAI_API_KEY`

- For Groq, create it here: https://console.groq.com/keys
- Groq says API keys are managed on its API Keys page: https://console.groq.com/keys

`OPENAI_BASE_URL`

- For Groq, use: `https://api.groq.com/openai/v1`
- Official Groq quickstart/docs: https://console.groq.com/docs/quickstart
- Groq speech-to-text endpoint docs: https://console.groq.com/docs/speech-to-text
- Groq text-to-speech endpoint docs: https://console.groq.com/docs/text-to-speech

`OPENAI_MODEL`

- For Groq chat, this project currently uses `llama-3.3-70b-versatile`
- Check Groq docs/models here: https://console.groq.com/docs/quickstart
- If you change this later, make sure the model is enabled in your Groq project

`OPENAI_STT_MODEL`

- Recommended Groq speech-to-text model: `whisper-large-v3-turbo`
- Official Groq speech-to-text docs: https://console.groq.com/docs/speech-to-text
- That page lists the `/audio/transcriptions` endpoint and supported STT models

`OPENAI_TTS_MODEL`

- Recommended Groq text-to-speech model: `canopylabs/orpheus-v1-english`
- Official Groq text-to-speech docs: https://console.groq.com/docs/text-to-speech
- This model may require one-time terms acceptance in the Groq playground before API calls work

`OPENAI_TTS_VOICE`

- Example voice from Groq docs: `austin`
- Other voices are documented from the Groq TTS/Orpheus docs entry point: https://console.groq.com/docs/text-to-speech

`PIPER_MODEL_PATH`

- Only needed if you want local/offline voice output with Piper
- Download Piper voice files here: https://huggingface.co/rhasspy/piper-voices
- After downloading, put the absolute path to the `.onnx` voice file in `PIPER_MODEL_PATH`

`OLLAMA_BASE_URL`

- Only needed if you want local AI
- Default local URL is usually `http://127.0.0.1:11434`
- Install Ollama for Linux here: https://ollama.com/download/linux

`OLLAMA_MODEL`

- Only needed if you want local AI
- Find Ollama models here: https://ollama.com/search

### Created by you locally

`ASSISTANT_TOKEN`

- This is not from a website
- Make your own random secret string
- Example command:

```bash
python3 - <<'PY'
import secrets
print(secrets.token_hex(16))
PY
```

`ASSISTANT_NAME`

- Any name you want, for example `Jarvis`

`USER_NAME`

- Your own name or nickname

### Usually keep the default

`CLOUD_PROVIDER`

- Use `groq` for your cloud setup
- Use `none` if you do not want cloud AI

`AI_ROUTE_MODE`

- Use `cloud` for Groq
- Use `off` if you want no AI
- Use `local` or `hybrid` only if you later add Ollama

`STT_MODE`

- Use `cloud` for Groq transcription
- Use `local` if you install `faster-whisper`
- Use `hybrid` if you want local first and cloud fallback

`TTS_MODE`

- Use `cloud` for Groq speech output
- Use `local` for Piper
- Use `hybrid` if you want local first and cloud fallback

`STT_LANGUAGE`

- Usually `en`
- Use ISO-639-1 language codes

`FASTER_WHISPER_MODEL`

- Only matters for local STT
- Good values: `tiny`, `base.en`

`PIPER_BIN`

- Usually leave as `piper`

`PIPER_SPEAKER_ID`

- Usually `0` unless the downloaded voice supports multiple speakers

`GREETING_ENABLED`

- `true` or `false`

`STARTUP_VOICE_GREETING`

- `true` or `false`

`VOICE_ONLY_MODE`

- `true` means the terminal starts listening for voice
- `false` means you can type normally

`VOICE_INPUT_SECONDS`

- How long to record each mic input
- Good values: `4` to `8`

`REFRESH_INTERVAL`

- Leave at `1.0` unless you know you want faster/slower monitoring

`CPU_THRESHOLD`

- Monitoring threshold, usually `90`

`MEMORY_THRESHOLD`

- Monitoring threshold, usually `90`

`TOOL_TIMEOUT_SECONDS`

- Timeout for local tool commands
- Usually `8`

`ALLOWED_COMMANDS`

- Safe shell allowlist
- Leave default unless you know exactly what extra commands you want Jarvis to run

## Sites You Will Actually Use

For your setup, the important sites are:

1. Groq API keys: https://console.groq.com/keys
2. Groq quickstart/docs: https://console.groq.com/docs/quickstart
3. Groq speech-to-text docs: https://console.groq.com/docs/speech-to-text
4. Groq text-to-speech docs: https://console.groq.com/docs/text-to-speech
5. Groq Orpheus terms/playground approval: https://console.groq.com/playground?model=canopylabs%2Forpheus-v1-english
6. Piper voices: https://huggingface.co/rhasspy/piper-voices
7. Ollama download: https://ollama.com/download/linux
8. Ollama model search: https://ollama.com/search

## Linux Packages You Still Need

These are local packages, not API keys:

```bash
sudo apt update
sudo apt install -y alsa-utils pulseaudio-utils speech-dispatcher espeak-ng xdotool wmctrl ffmpeg
```

## Fastest Way To Finish Setup

1. Copy `.env.example` to `.env`
2. Open https://console.groq.com/keys
3. Create a Groq API key
4. Paste that key into `OPENAI_API_KEY`
5. Keep `OPENAI_BASE_URL=https://api.groq.com/openai/v1`
6. Set `AI_ROUTE_MODE=cloud`
7. Set `STT_MODE=cloud`
8. Set `TTS_MODE=cloud`
9. Install the Linux packages above

## Notes

- The project uses `OPENAI_*` variable names for compatibility, but with your setup they point to Groq, not OpenAI.
- If you stay on Groq, you do not need an OpenAI account.
- If you want fully offline voices later, fill in `PIPER_MODEL_PATH`.
