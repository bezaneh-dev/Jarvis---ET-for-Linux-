from app.tools import tool_open_app


def test_open_chrome_uses_alias_when_binary_exists(monkeypatch) -> None:
    launched: list[list[str]] = []

    class FakePopen:
        def __init__(self, cmd: list[str], **_kwargs) -> None:
            launched.append(cmd)

    monkeypatch.setattr("app.tools.subprocess.Popen", FakePopen)

    risk, executor = tool_open_app("chrome")
    result = executor()

    assert risk.value == "medium"
    assert result.ok is True
    assert launched[0][0] == "google-chrome"
