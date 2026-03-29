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
