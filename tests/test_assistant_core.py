from app.assistant_core import AssistantCore
from app.models import ToolResult


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
    assert "FASTER_WHISPER_MODEL=tiny" in env_example
