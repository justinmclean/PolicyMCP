"""HTTP fetching, HTML extraction, and disk cache for policy documents."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

import httpx
from bs4 import BeautifulSoup, Tag

from asf_policy_mcp.sources import POLICY_SOURCES

# 30 days — ASF policies change infrequently
CACHE_TTL: int = 30 * 24 * 3600
CACHE_FILE: Path = Path.home() / ".cache" / "asf-policy-mcp" / "policy_cache.json"


def html_to_text(html: str) -> str:
    """Extract clean plain text from an HTML string."""
    text, _ = html_to_text_with_anchors(html)
    return text


def html_to_text_with_anchors(html: str) -> tuple[str, list[list[Any]]]:
    """Extract plain text and a list of [line_number, anchor_id] pairs from HTML.

    Anchors come from heading elements (h1-h6) that carry an id attribute.
    """
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()
    main = (
        soup.find("main")
        or soup.find(id="content")
        or soup.find(attrs={"class": "content"})
        or soup.body
    )
    root: Tag = main if isinstance(main, Tag) else soup
    text = root.get_text(separator="\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    lines = text.split("\n")

    anchors: list[list[Any]] = []
    for heading in root.find_all(re.compile(r"^h[1-6]$")):
        if not isinstance(heading, Tag):
            continue
        anchor_id = heading.get("id")
        if not anchor_id:
            continue
        heading_text = heading.get_text(strip=True)
        if not heading_text:
            continue
        for i, line in enumerate(lines):
            if line.strip() == heading_text:
                anchors.append([i, anchor_id])
                break

    return text, anchors


def find_anchor(anchors: list[list[Any]], line_num: int) -> str | None:
    """Return the anchor id of the nearest heading at or before *line_num*."""
    best: str | None = None
    for line, anchor_id in anchors:
        if line <= line_num:
            best = anchor_id
        else:
            break
    return best


def fetch_page_text(url: str) -> str:
    """Fetch *url* and return its content as plain text, or an error string."""
    text, _ = fetch_page(url)
    return text


def fetch_page(url: str) -> tuple[str, list[list[Any]]]:
    """Fetch *url* and return ``(plain_text, anchors)``.

    *anchors* is a list of ``[line_number, anchor_id]`` pairs derived from
    heading elements.  On error the text is an error string and anchors is empty.
    """
    try:
        with httpx.Client(follow_redirects=True, timeout=30) as client:
            resp = client.get(url, headers={"User-Agent": "asf-policy-mcp/0.1.0"})
            resp.raise_for_status()
        return html_to_text_with_anchors(resp.text)
    except Exception as exc:
        return f"[Error fetching {url}: {exc}]", []


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
    text, anchors = fetch_page(url)
    cache[key] = {"text": text, "fetched_at": now, "url": url, "anchors": anchors}
    save_cache(cache)
    return text
