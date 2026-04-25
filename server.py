#!/usr/bin/env python3
"""SearXNG MCP server — exposes web search + page fetch backed by a local
SearXNG container, so Claude Code (and any MCP-compatible client) can do real
web research without going through Anthropic's WebSearch (which is a no-op
against a local vllm-mlx server).

Default backend: http://127.0.0.1:8080  (works on any host that ran the
included docker compose, regardless of OrbStack DNS plumbing).
Override via env:  SEARXNG_URL=https://searxng.docker.orb.local
"""

from __future__ import annotations

import os
import re

import httpx
from mcp.server.fastmcp import FastMCP

SEARXNG_URL = os.environ.get("SEARXNG_URL", "http://127.0.0.1:8080").rstrip("/")
HTTP_TIMEOUT = float(os.environ.get("SEARXNG_TIMEOUT", "30"))

# Loopback containers usually use self-signed certs; verify=False is fine.
# Set SEARXNG_VERIFY=1 to enable strict TLS (e.g., when pointing at a
# public-internet SearXNG).
VERIFY_TLS = os.environ.get("SEARXNG_VERIFY", "0") == "1"

mcp = FastMCP("searxng")


@mcp.tool()
def search(query: str, count: int = 5, language: str = "en") -> str:
    """Search the web via the local SearXNG instance.

    Args:
        query: The search query string.
        count: How many results to return (default 5, max 20).
        language: Two-letter language code (default 'en').

    Returns a numbered list of results with title, URL, and snippet.
    """
    count = max(1, min(int(count), 20))
    params = {"q": query, "format": "json", "language": language}
    try:
        with httpx.Client(verify=VERIFY_TLS, timeout=HTTP_TIMEOUT) as client:
            r = client.get(f"{SEARXNG_URL}/search", params=params)
            r.raise_for_status()
            data = r.json()
    except httpx.HTTPError as exc:
        return f"[searxng error] {exc}"

    results = data.get("results", [])[:count]
    if not results:
        return f"No results for: {query!r}"

    lines: list[str] = []
    for i, item in enumerate(results, 1):
        title = item.get("title", "(no title)").strip()
        url = item.get("url", "")
        snippet = (item.get("content") or "").strip()
        if len(snippet) > 280:
            snippet = snippet[:277] + "..."
        lines.append(f"{i}. {title}\n   {url}\n   {snippet}")
    return "\n\n".join(lines)


@mcp.tool()
def fetch(url: str, max_chars: int = 8000) -> str:
    """Fetch a web page by URL and return its text content.

    Strips HTML tags and limits output to ``max_chars`` (default 8000).
    Use this after :func:`search` when you want the full content of a result.

    Args:
        url: The URL to fetch.
        max_chars: Truncate the response body to this many characters.
    """
    max_chars = max(500, min(int(max_chars), 50000))
    try:
        with httpx.Client(
            verify=VERIFY_TLS,
            timeout=HTTP_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": "searxng-mcp/1.0"},
        ) as client:
            r = client.get(url)
            r.raise_for_status()
            body = r.text
    except httpx.HTTPError as exc:
        return f"[fetch error] {exc}"

    # Crude HTML strip: drop scripts/styles, then tags, collapse whitespace.
    body = re.sub(r"<script[^>]*>.*?</script>", " ", body, flags=re.DOTALL | re.IGNORECASE)
    body = re.sub(r"<style[^>]*>.*?</style>", " ", body, flags=re.DOTALL | re.IGNORECASE)
    body = re.sub(r"<[^>]+>", " ", body)
    body = re.sub(r"\s+", " ", body).strip()

    if len(body) > max_chars:
        body = body[:max_chars] + f"\n\n[truncated; total {len(body)} chars]"
    return body or "[empty body]"


if __name__ == "__main__":
    mcp.run()
