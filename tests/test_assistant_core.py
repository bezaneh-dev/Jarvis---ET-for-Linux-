from app.assistant_core import AssistantCore
from app.models import RiskLevel, ToolResult


def test_research_route_without_network(monkeypatch) -> None:
    core = AssistantCore()

    def fake_research(query: str) -> ToolResult:
        return ToolResult(
            ok=True,
            summary="Web research complete.",
            data={
                "query": query,
                "summary": "Mocked summary",
                "sources": [{"title": "Example", "url": "https://example.com"}],
            },
        )

    monkeypatch.setattr(core.web, "research", fake_research)

    resp = core.handle_message("search web linux performance tuning")
    assert "Web research complete" in resp.reply
    assert "https://example.com" in resp.reply


def test_first_interaction_has_greeting(monkeypatch) -> None:
    core = AssistantCore()

    def fake_research(query: str) -> ToolResult:
        return ToolResult(ok=True, summary="Web research complete.", data={"summary": "ok", "sources": []})

    monkeypatch.setattr(core.web, "research", fake_research)

    first = core.handle_message("search web hello")
    second = core.handle_message("search web hello again")

    assert "Hello" in first.reply
    assert second.reply.count("Hello") == 0


def test_no_llm_mode_returns_local_fallback() -> None:
    core = AssistantCore()
    core.llm.is_enabled = lambda: False  # type: ignore[method-assign]

    def fake_research(_query: str, max_results: int = 3) -> ToolResult:
        return ToolResult(ok=False, summary="Web search failed.")

    core.web.research = fake_research  # type: ignore[method-assign]

    resp = core.handle_message("write me a poem")

    assert "free local mode" in resp.reply
    assert "show cpu and memory" in resp.reply


def test_general_query_prefers_web_research_over_llm(monkeypatch) -> None:
    core = AssistantCore()

    def fake_research(query: str, max_results: int = 3) -> ToolResult:
        return ToolResult(
            ok=True,
            summary="Web research complete.",
            data={
                "query": query,
                "summary": "Internet answer",
                "sources": [{"title": "Example", "url": "https://example.com"}],
            },
        )

    def fail_if_called(_prompt: str) -> tuple[str, str | None]:
        raise AssertionError("LLM should not be used when web research succeeds")

    monkeypatch.setattr(core.web, "research", fake_research)
    monkeypatch.setattr(core.llm, "ask", fail_if_called)

    resp = core.handle_message("what is zram on linux")

    assert "Web research complete" in resp.reply
    assert "Internet answer" in resp.reply


def test_default_settings_are_free_first() -> None:
    env_example = open("/home/kali/Projects/Robot /.env.example", encoding="utf-8").read()
    assert "AI_ROUTE_MODE=off" in env_example
    assert "FASTER_WHISPER_MODEL=base.en" in env_example
    assert "VOICE_ONLY_MODE=true" in env_example


def test_social_greeting_does_not_trigger_web_research(monkeypatch) -> None:
    core = AssistantCore()

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("Web research should not run for a greeting")

    monkeypatch.setattr(core.web, "research", fail_if_called)

    resp = core.handle_message("hey")

    assert "How can I help you right now?" in resp.reply
    assert "Web research complete" not in resp.reply


def test_natural_language_open_request_uses_app_tool(monkeypatch) -> None:
    core = AssistantCore()

    monkeypatch.setattr(
        "app.assistant_core.tool_open_app",
        lambda app_name: (
            RiskLevel.low,
            lambda: ToolResult(ok=True, summary=f"Opened {app_name}."),
        ),
    )

    resp = core.handle_message("Jarvis please launch terminal for me")

    assert "Opened terminal." in resp.reply


def test_voice_help_request_returns_setup_guidance() -> None:
    core = AssistantCore()

    resp = core.handle_message("fix voice")

    assert "Voice setup help" in resp.reply
    assert "app/voice.py" in resp.reply
    assert "console.groq.com/keys" in resp.reply


def test_repeat_last_message_returns_previous_input() -> None:
    core = AssistantCore()
    core.handle_message("open firefox")

    resp = core.handle_message("show me what i said")

    assert "I heard: open firefox" in resp.reply


def test_minimize_window_request_routes_to_window_tool(monkeypatch) -> None:
    core = AssistantCore()

    monkeypatch.setattr(
        "app.assistant_core.tool_window_control",
        lambda action: (
            RiskLevel.medium,
            lambda: ToolResult(ok=True, summary=f"Window action: {action}"),
        ),
    )

    resp = core.handle_message("minimize the current window")

    assert "Window action: minimize" in resp.reply


def test_type_request_requires_confirmation(monkeypatch) -> None:
    core = AssistantCore()

    monkeypatch.setattr(
        "app.assistant_core.tool_type_text",
        lambda text: (
            RiskLevel.high,
            lambda: ToolResult(ok=True, summary=f"Typed: {text}"),
        ),
    )

    resp = core.handle_message("type hello world")

    assert resp.action_required is True
    assert "Type text into the active window" in resp.reply
