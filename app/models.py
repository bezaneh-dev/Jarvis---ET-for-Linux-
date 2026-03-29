from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class AssistantMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class AssistantMessageResponse(BaseModel):
    reply: str
    model_used: str | None = None
    action_required: bool = False
    pending_action_id: str | None = None


class ConfirmActionRequest(BaseModel):
    action_id: str
    approve: bool


class VoiceRecordRequest(BaseModel):
    seconds: int = Field(default=4, ge=1, le=20)


class VoiceSpeakRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class VoiceChatRequest(BaseModel):
    seconds: int = Field(default=4, ge=1, le=20)
    speak_reply: bool = True


class ToolResult(BaseModel):
    ok: bool
    summary: str
    data: dict[str, Any] = Field(default_factory=dict)
