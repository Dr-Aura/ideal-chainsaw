"""Optional web search via DuckDuckGo (no API key)."""

from __future__ import annotations

import logging

log = logging.getLogger("chainsaw.search")

try:
    from duckduckgo_search import DDGS
except ImportError:  # pragma: no cover
    DDGS = None  # type: ignore


def is_available() -> bool:
    return DDGS is not None


def search(query: str, max_results: int = 5) -> str:
    if not DDGS:
        return "Web search is not available (duckduckgo-search not installed)."
    q = (query or "").strip()[:500]
    if not q:
        return "Empty query."
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(q, max_results=max_results))
        if not results:
            return "No results found."
        lines = []
        for i, r in enumerate(results, 1):
            title = (r.get("title") or "")[:200]
            href = (r.get("href") or "")[:300]
            body = (r.get("body") or "")[:400]
            lines.append(f"{i}. **{title}**\n   {href}\n   {body}")
        return "\n\n".join(lines)
    except Exception as e:
        log.error("search failed: %s", e)
        return f"Search error: {type(e).__name__}"


def should_search(prompt: str) -> bool:
    p = prompt.lower()
    triggers = (
        "search",
        "look up",
        "lookup",
        "what is",
        "who is",
        "latest",
        "news",
        "current",
        "when did",
        "how many",
    )
    return any(t in p for t in triggers)
