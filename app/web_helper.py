from __future__ import annotations

import httpx
from bs4 import BeautifulSoup
from ddgs import DDGS

from app.llm import LLMRouter
from app.models import ToolResult


class WebHelper:
    def __init__(self, llm: LLMRouter) -> None:
        self.llm = llm

    def research(self, query: str, max_results: int = 5) -> ToolResult:
        query = query.strip()
        if not query:
            return ToolResult(ok=False, summary="No research query provided.")

        try:
            with DDGS() as ddgs:
                raw_results = list(ddgs.text(query, max_results=max_results))
        except Exception as exc:
            return ToolResult(ok=False, summary=f"Web search failed: {exc}")

        if not raw_results:
            return ToolResult(ok=False, summary="No web results found.")

        sources: list[dict[str, str]] = []
        snippets: list[str] = []
        for item in raw_results[:max_results]:
            title = str(item.get("title", "")).strip()
            href = str(item.get("href", "")).strip()
            body = str(item.get("body", "")).strip()
            if not href:
                continue
            sources.append({"title": title or href, "url": href})
            if body:
                snippets.append(f"- {title}: {body}")

        page_extract = self._extract_page_text(sources[0]["url"]) if sources else ""
        synthesis_input = "\n".join(snippets[:5])
        if page_extract:
            synthesis_input += "\n\nPrimary page extract:\n" + page_extract[:2000]

        if self.llm.is_enabled():
            llm_prompt = (
                "Summarize this research in 5 bullet points with practical takeaway. "
                "Do not invent facts. Keep it concise.\n\n"
                f"Query: {query}\n\n"
                f"Material:\n{synthesis_input}"
            )
            summary, model = self.llm.ask(llm_prompt)
        else:
            summary = self._summarize_without_llm(query, snippets, page_extract)
            model = None

        return ToolResult(
            ok=True,
            summary="Web research complete.",
            data={
                "query": query,
                "summary": summary,
                "model_used": model,
                "sources": sources,
            },
        )

    def _summarize_without_llm(self, query: str, snippets: list[str], page_extract: str) -> str:
        bullets = [f"- Search query: {query}"]
        for snippet in snippets[:3]:
            bullets.append(snippet)
        if page_extract:
            bullets.append(f"- Page extract: {page_extract[:240].strip()}")
        if len(bullets) == 1:
            bullets.append("- Results found, but the pages did not expose useful summary text.")
        bullets.append("- Practical takeaway: open the source links for exact details before acting on them.")
        return "\n".join(bullets)

    def _extract_page_text(self, url: str) -> str:
        try:
            with httpx.Client(timeout=8.0, follow_redirects=True) as client:
                resp = client.get(url)
                resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup(["script", "style", "noscript"]):
                tag.extract()
            text = " ".join(soup.get_text(" ").split())
            return text[:5000]
        except Exception:
            return ""
