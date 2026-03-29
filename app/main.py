from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.assistant_core import AssistantCore
from app.capabilities import detect_capabilities
from app.config import settings
from app.models import (
    AssistantMessageRequest,
    AssistantMessageResponse,
    ConfirmActionRequest,
    VoiceChatRequest,
    VoiceRecordRequest,
    VoiceSpeakRequest,
)
from app.monitoring import get_basic_metrics
from app.voice import VoiceService
from app.web_helper import WebHelper

app = FastAPI(title="Jarvis Lite Linux", version="0.1.0")
core = AssistantCore()
voice = VoiceService()
web = WebHelper(core.llm)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def verify_token(x_token: Optional[str] = Query(None, alias="x_token")) -> None:
    if settings.assistant_token and x_token != settings.assistant_token:
        raise HTTPException(status_code=401, detail="Invalid token")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "jarvis-lite"}


@app.get("/capabilities", dependencies=[Depends(verify_token)])
async def capabilities() -> dict:
    snapshot = detect_capabilities()
    return {"ok": True, "summary": "Capability detection complete.", "data": snapshot.as_dict()}


@app.get("/metrics", dependencies=[Depends(verify_token)])
async def metrics() -> dict:
    return get_basic_metrics()


@app.post("/assistant/message", dependencies=[Depends(verify_token)], response_model=AssistantMessageResponse)
async def assistant_message(body: AssistantMessageRequest) -> AssistantMessageResponse:
    return core.handle_message(body.message)


@app.post("/assistant/confirm", dependencies=[Depends(verify_token)])
async def assistant_confirm(body: ConfirmActionRequest) -> dict:
    result = core.confirm_action(action_id=body.action_id, approve=body.approve)
    return {"ok": result.ok, "summary": result.summary, "data": result.data}


@app.post("/voice/record-transcribe", dependencies=[Depends(verify_token)])
async def voice_record_transcribe(body: VoiceRecordRequest) -> dict:
    ok, summary, wav_path = voice.record_wav(seconds=body.seconds)
    if not ok or wav_path is None:
        return {"ok": False, "summary": summary, "text": ""}

    try:
        t_ok, text, err = voice.transcribe_file(wav_path)
        if not t_ok:
            return {"ok": False, "summary": err, "text": ""}
        return {"ok": True, "summary": "Voice transcription complete.", "text": text}
    finally:
        Path(wav_path).unlink(missing_ok=True)


@app.post("/voice/speak", dependencies=[Depends(verify_token)])
async def voice_speak(body: VoiceSpeakRequest) -> dict:
    ok, summary = voice.speak_text(body.text)
    return {"ok": ok, "summary": summary}


@app.post("/voice/chat", dependencies=[Depends(verify_token)])
async def voice_chat(body: VoiceChatRequest) -> dict:
    ok, summary, wav_path = voice.record_wav(seconds=body.seconds)
    if not ok or wav_path is None:
        return {"ok": False, "summary": summary}

    try:
        t_ok, text, err = voice.transcribe_file(wav_path)
        if not t_ok:
            return {"ok": False, "summary": err, "heard": ""}

        response = core.handle_message(text)
        speak_summary = ""
        if body.speak_reply:
            s_ok, s_summary = voice.speak_text(response.reply)
            speak_summary = s_summary
            if not s_ok:
                speak_summary = f"Reply ready but TTS failed: {s_summary}"

        return {
            "ok": True,
            "summary": "Voice chat complete.",
            "heard": text,
            "reply": response.reply,
            "action_required": response.action_required,
            "pending_action_id": response.pending_action_id,
            "pending_action_expires_in": response.pending_action_expires_in,
            "tts": speak_summary,
        }
    finally:
        Path(wav_path).unlink(missing_ok=True)


@app.get("/web/research", dependencies=[Depends(verify_token)])
async def web_research(query: str) -> dict:
    result = web.research(query)
    return {"ok": result.ok, "summary": result.summary, "data": result.data}


@app.websocket("/ws/metrics")
async def ws_metrics(ws: WebSocket, x_token: Optional[str] = Query(None, alias="x_token")) -> None:
    if settings.assistant_token and x_token != settings.assistant_token:
        await ws.close(code=4001)
        return

    await ws.accept()
    high_cpu_count = 0
    high_mem_count = 0
    persistence = 5
    cooldown_seconds = 60
    last_alert = {"cpu": 0.0, "memory": 0.0}

    try:
        while True:
            data = get_basic_metrics()
            now = time.time()
            alerts: list[str] = []

            if data.get("cpu_percent", 0) > settings.cpu_threshold:
                high_cpu_count += 1
            else:
                high_cpu_count = 0

            if data.get("memory_percent", 0) > settings.memory_threshold:
                high_mem_count += 1
            else:
                high_mem_count = 0

            if high_cpu_count >= persistence and (now - last_alert["cpu"]) > cooldown_seconds:
                alerts.append(f"High CPU: {data.get('cpu_percent')}%")
                last_alert["cpu"] = now

            if high_mem_count >= persistence and (now - last_alert["memory"]) > cooldown_seconds:
                alerts.append(f"High Memory: {data.get('memory_percent')}%")
                last_alert["memory"] = now

            if alerts:
                data["alerts"] = alerts

            await ws.send_json(data)
            await asyncio.sleep(settings.refresh_interval)
    except WebSocketDisconnect:
        return


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8010, reload=False)
