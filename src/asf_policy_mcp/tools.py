"""FastMCP tool definitions for the ASF Policy MCP server."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from mcp.server.fastmcp import FastMCP

from asf_policy_mcp import fetcher
from asf_policy_mcp.sources import POLICY_SOURCES

mcp = FastMCP("asf-policy")


@mcp.tool()
def list_policies() -> str:
    """List all available ASF policy documents organised by section."""
    cache = fetcher.load_cache()
    by_section: dict[str, list[tuple[str, dict[str, str]]]] = {}
    for key, meta in POLICY_SOURCES.items():
        by_section.setdefault(meta["section"], []).append((key, meta))

    lines = ["# ASF Policy Documents\n"]
    for section, items in by_section.items():
        lines.append(f"## {section}")
        for key, meta in items:
            entry: dict[str, Any] = cache.get(key, {})
            if entry.get("text"):
                age_h = int((time.time() - float(entry.get("fetched_at", 0))) // 3600)
                age = f" — cached {age_h}h ago"
            else:
                age = " — not yet fetched"
            lines.append(f"- **`{key}`**: {meta['title']}{age}")
            lines.append(f"  {meta['description']}")
            lines.append(f"  <{meta['url']}>")
        lines.append("")
    return "\n".join(lines)


@mcp.tool()
def get_policy(key: str, force_refresh: bool = False) -> str:
    """Retrieve the full text of a specific ASF policy document.

    Use list_policies to discover valid policy keys such as 'release_policy',
    'branding', 'resolved_licenses', 'incubator', etc.
    """
    if key not in POLICY_SOURCES:
        available = ", ".join(f"`{k}`" for k in POLICY_SOURCES)
        return f"Unknown policy key **{key!r}**. Available keys: {available}"
    cache = fetcher.load_cache()
    meta = POLICY_SOURCES[key]
    text = fetcher.get_policy_text(key, cache, force=force_refresh)
    return (
        f"# {meta['title']}\n\n"
        f"**Source:** <{meta['url']}>\n"
        f"**Section:** {meta['section']}\n\n---\n\n"
    ) + text


@mcp.tool()
def search_policies(query: str, max_results: int = 10) -> str:
    """Search across all ASF policy documents for a query term or phrase.

    Returns ranked excerpts with surrounding context.  Policies not yet in the
    local cache are fetched automatically so every policy is always searched.
    """
    if not query.strip():
        return "Please provide a search query."

    cache = fetcher.load_cache()
    query_words = set(query.lower().split())

    def score_text(key: str) -> list[dict[str, Any]]:
        entry = cache.get(key, {})
        text = str(entry.get("text", ""))
        if not text or text.startswith("[Error"):
            return []
        lines = text.split("\n")
        hits: list[dict[str, Any]] = []
        for i, line in enumerate(lines):
            score = sum(1 for w in query_words if w in line.lower())
            if score:
                start = max(0, i - 2)
                end = min(len(lines), i + 3)
                hits.append({
                    "key": key,
                    "title": POLICY_SOURCES[key]["title"],
                    "url": POLICY_SOURCES[key]["url"],
                    "score": score,
                    "excerpt": "\n".join(lines[start:end]).strip(),
                    "line": i,
                })
        return hits

    # Search cached policies first
    results: list[dict[str, Any]] = []
    uncached: list[str] = []
    for key in POLICY_SOURCES:
        entry = cache.get(key, {})
        if entry.get("text") and not str(entry["text"]).startswith("[Error"):
            results.extend(score_text(key))
        else:
            uncached.append(key)

    # Fetch any uncached policies in parallel then search them too
    if uncached:
        def fetch_one(key: str) -> tuple[str, str, list[list[Any]]]:
            text, anchors = fetcher.fetch_page(POLICY_SOURCES[key]["url"])
            return key, text, anchors

        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = {pool.submit(fetch_one, k): k for k in uncached}
            for future in as_completed(futures):
                key, text, anchors = future.result()
                cache[key] = {"text": text, "fetched_at": time.time(), "url": POLICY_SOURCES[key]["url"], "anchors": anchors}
                results.extend(score_text(key))
        fetcher.save_cache(cache)

    results.sort(key=lambda r: -r["score"])

    seen: dict[str, list[int]] = {}
    deduped: list[dict[str, Any]] = []
    for r in results:
        prior = seen.get(r["key"], [])
        if not any(abs(r["line"] - p) < 5 for p in prior):
            deduped.append(r)
            seen.setdefault(r["key"], []).append(r["line"])
        if len(deduped) >= max_results:
            break

    if not deduped:
        return f"No results found for **{query!r}**."

    out = [f"# Search Results for '{query}'\n"]
    for r in deduped:
        anchors: list[list[Any]] = cache.get(r["key"], {}).get("anchors", [])
        anchor_id = fetcher.find_anchor(anchors, r["line"])
        link_url = f"{r['url']}#{anchor_id}" if anchor_id else r["url"]
        out.append(f"## [{r['title']}]({link_url})  (`{r['key']}`)\n")
        out.append("```")
        out.append(r["excerpt"])
        out.append("```\n")
    return "\n".join(out)


@mcp.tool()
def refresh_cache(keys: list[str] | None = None) -> str:
    """Re-fetch policy documents from the ASF website in parallel, bypassing the 30-day cache.

    Omit keys to refresh all policies.
    """
    unknown = [k for k in (keys or []) if k not in POLICY_SOURCES]
    targets = [k for k in (keys or list(POLICY_SOURCES.keys())) if k in POLICY_SOURCES]

    # Load once; each worker writes its own entry then we merge and save once at the end
    cache = fetcher.load_cache()

    def fetch_one(key: str) -> tuple[str, str, list[list[Any]]]:
        text, anchors = fetcher.fetch_page(POLICY_SOURCES[key]["url"])
        return key, text, anchors

    refreshed: list[str] = []
    errors: list[str] = [f"Unknown key: `{k}`" for k in unknown]

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(fetch_one, k): k for k in targets}
        for future in as_completed(futures):
            key, text, anchors = future.result()
            if text.startswith("[Error"):
                errors.append(f"{key}: {text}")
            else:
                cache[key] = {"text": text, "fetched_at": time.time(), "url": POLICY_SOURCES[key]["url"], "anchors": anchors}
                refreshed.append(key)

    fetcher.save_cache(cache)

    msg = f"Refreshed {len(refreshed)} policies: {', '.join(sorted(refreshed))}"
    if errors:
        msg += "\n\nErrors:\n" + "\n".join(errors)
    return msg
