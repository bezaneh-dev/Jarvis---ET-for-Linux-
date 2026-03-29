from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any, Callable

from app.models import RiskLevel, ToolResult


@dataclass
class PendingAction:
    action_id: str
    created_at: float
    expires_at: float
    summary: str
    executor: Callable[[], ToolResult]


class ConfirmationManager:
    def __init__(self, ttl_seconds: int = 90) -> None:
        self.ttl_seconds = ttl_seconds
        self._pending: dict[str, PendingAction] = {}

    def create(self, summary: str, executor: Callable[[], ToolResult]) -> str:
        action_id = str(uuid.uuid4())
        now = time.time()
        self._pending[action_id] = PendingAction(
            action_id=action_id,
            created_at=now,
            expires_at=now + self.ttl_seconds,
            summary=summary,
            executor=executor,
        )
        return action_id

    def confirm(self, action_id: str, approve: bool) -> ToolResult:
        action = self._pending.pop(action_id, None)
        if action is None:
            return ToolResult(ok=False, summary="Unknown or already handled action.")

        if time.time() > action.expires_at:
            return ToolResult(ok=False, summary="Action expired. Please ask again.")

        if not approve:
            return ToolResult(ok=True, summary="Action canceled.")

        return action.executor()


def needs_confirmation(risk: RiskLevel) -> bool:
    return risk == RiskLevel.high
