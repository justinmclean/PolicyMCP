"""HTTP fetching, HTML extraction, and disk cache for policy documents."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

import httpx
from bs4 import BeautifulSoup

from asf_policy_mcp.sources import POLICY_SOURCES

# 30 days — ASF policies change infrequently
CACHE_TTL: int = 30 * 24 * 3600
CACHE_FILE: Path = Path.home() / ".cache" / "asf-policy-mcp" / "policy_cache.json"


def html_to_text(html: str) -> str:
    """Extract clean plain text from an HTML string."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()
    main = (
        soup.find("main")
        or soup.find(id="content")
        or soup.find(attrs={"class": "content"})
        or soup.body
    )
    text = (main or soup).get_text(separator="\n", strip=True)
    return re.sub(r"\n{3,}", "\n\n", text)


def fetch_page_text(url: str) -> str:
    """Fetch *url* and return its content as plain text, or an error string."""
    try:
        with httpx.Client(follow_redirects=True, timeout=30) as client:
            resp = client.get(url, headers={"User-Agent": "asf-policy-mcp/0.1.0"})
            resp.raise_for_status()
        return html_to_text(resp.text)
    except Exception as exc:
        return f"[Error fetching {url}: {exc}]"


def load_cache() -> dict[str, Any]:
    """Load the on-disk JSON cache, returning an empty dict on any error."""
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text(encoding="utf-8"))  # type: ignore[no-any-return]
        except Exception:
            pass
    return {}


def save_cache(cache: dict[str, Any]) -> None:
    """Persist the cache dict to disk, creating parent directories as needed."""
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(cache, indent=2), encoding="utf-8")


def get_policy_text(key: str, cache: dict[str, Any], force: bool = False) -> str:
    """Return policy text from *cache*, fetching from the web if stale or missing."""
    entry: dict[str, Any] = cache.get(key, {})
    now = time.time()
    if not force and entry.get("text") and now - float(entry.get("fetched_at", 0)) < CACHE_TTL:
        return str(entry["text"])
    url = POLICY_SOURCES[key]["url"]
    text = fetch_page_text(url)
    cache[key] = {"text": text, "fetched_at": now, "url": url}
    save_cache(cache)
    return text
