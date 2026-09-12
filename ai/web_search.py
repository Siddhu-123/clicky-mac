"""
Free real-time web search for Clicky macOS using DuckDuckGo HTML scraping.
No API key required.
"""

from __future__ import annotations

import re
import urllib.parse
from dataclasses import dataclass
from typing import List, Optional

import httpx


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str


class WebSearcher:
    """Performs live web search without API keys."""

    DDG_URL = "https://html.duckduckgo.com/html/"
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
    }

    @classmethod
    async def search(cls, query: str, max_results: int = 4) -> List[SearchResult]:
        if not query.strip():
            return []

        results: List[SearchResult] = []
        data = {"q": query}

        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            try:
                resp = await client.post(cls.DDG_URL, data=data, headers=cls.HEADERS)
                if resp.status_code != 200:
                    return []

                html = resp.text
                # Find result snippets in DuckDuckGo HTML
                # <a class="result__snippet" ...>...</a>
                snippets = re.findall(
                    r'<a class="result__snippet[^>]*>(.*?)</a>',
                    html,
                    re.DOTALL | re.IGNORECASE,
                )
                titles = re.findall(
                    r'<a class="result__url[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
                    html,
                    re.DOTALL | re.IGNORECASE,
                )

                for i in range(min(len(snippets), max_results)):
                    raw_snippet = re.sub(r"<[^>]+>", "", snippets[i]).strip()
                    url = titles[i][0] if i < len(titles) else ""
                    raw_title = re.sub(r"<[^>]+>", "", titles[i][1]).strip() if i < len(titles) else "Result"

                    # Decode DDG redirect URL
                    if "uddg=" in url:
                        match = re.search(r"uddg=([^&]+)", url)
                        if match:
                            url = urllib.parse.unquote(match.group(1))

                    if raw_snippet:
                        results.append(SearchResult(title=raw_title, url=url, snippet=raw_snippet))

            except Exception as e:
                print(f"[WebSearch] Error searching: {e}")

        return results

    @classmethod
    async def format_search_context(cls, query: str) -> str:
        results = await cls.search(query)
        if not results:
            return ""

        context_lines = [f"Live Web Search Results for: '{query}'"]
        for i, r in enumerate(results, 1):
            context_lines.append(f"[{i}] {r.title}\n    {r.snippet}\n    URL: {r.url}")

        return "\n\n".join(context_lines)
