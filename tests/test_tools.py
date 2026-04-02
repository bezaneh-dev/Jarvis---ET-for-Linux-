from app.tools import tool_open_app, tool_type_text, tool_window_control


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


def test_window_minimize_uses_xdotool_when_present(monkeypatch) -> None:
    launched: list[list[str]] = []

    def fake_run(cmd: list[str], **_kwargs):
        launched.append(cmd)

        class Result:
            returncode = 0
            stdout = ""
            stderr = ""

        return Result()

    monkeypatch.setattr("app.tools.shutil.which", lambda name: f"/usr/bin/{name}" if name == "xdotool" else None)
    monkeypatch.setattr("app.tools.subprocess.run", fake_run)

    risk, executor = tool_window_control("minimize")
    result = executor()

    assert risk.value == "medium"
    assert result.ok is True
    assert launched[0][-1] == "windowminimize"


def test_type_text_requires_confirmation_level(monkeypatch) -> None:
    launched: list[list[str]] = []

    def fake_run(cmd: list[str], **_kwargs):
        launched.append(cmd)

        class Result:
            returncode = 0
            stdout = ""
            stderr = ""

        return Result()

    monkeypatch.setattr("app.tools.shutil.which", lambda name: f"/usr/bin/{name}" if name == "xdotool" else None)
    monkeypatch.setattr("app.tools.subprocess.run", fake_run)

    risk, executor = tool_type_text("hello world")
    result = executor()

    assert risk.value == "high"
    assert result.ok is True
    assert launched[0][-1] == "hello world"
