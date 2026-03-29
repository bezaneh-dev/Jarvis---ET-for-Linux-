from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)
TOKEN = "change-me"


def test_health_ok() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "ok"


def test_shutdown_requires_confirmation() -> None:
    resp = client.post(
        f"/assistant/message?x_token={TOKEN}",
        json={"message": "shutdown"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["action_required"] is True
    assert payload["pending_action_id"]


def test_cancel_pending_action() -> None:
    create_resp = client.post(
        f"/assistant/message?x_token={TOKEN}",
        json={"message": "shutdown"},
    )
    action_id = create_resp.json()["pending_action_id"]

    cancel_resp = client.post(
        f"/assistant/confirm?x_token={TOKEN}",
        json={"action_id": action_id, "approve": False},
    )
    assert cancel_resp.status_code == 200
    payload = cancel_resp.json()
    assert payload["ok"] is True
    assert "canceled" in payload["summary"].lower()
