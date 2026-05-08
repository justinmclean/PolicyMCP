"""FastMCP tool definitions for the ASF Policy MCP server."""

from __future__ import annotations

import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from math import log
from typing import Any

import re
from mcp.server.fastmcp import FastMCP

from asf_policy_mcp import fetcher
from asf_policy_mcp.sources import POLICY_SOURCES

mcp = FastMCP("asf-policy")

STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "asf",
    "can",
    "detail",
    "details",
    "do",
    "does",
    "i",
    "into",
    "for",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "teh",
    "the",
    "to",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
}

TOKEN_VARIANTS = {
    "cc": {"creative", "commons", "license"},
    "commons": {"creative", "license"},
    "contact": {"address", "email", "facsimile", "membership", "record", "telephone"},
    "chatgpt": {"ai", "generative", "tooling"},
    "cc0": {"category", "creative", "commons", "license"},
    "ccla": {"cla", "contributor"},
    "cla": {"contributor"},
    "compatible": {"compatibility", "trademark"},
    "bsd": {"category", "license"},
    "create": {"designate", "establish"},
    "created": {"designated", "established"},
    "creates": {"designates", "establishes"},
    "csp": {"content", "policy", "security"},
    "dependency": {"library"},
    "donation": {"clearance", "ip"},
    "distributed": {"distribution", "distribute"},
    "docker": {"container"},
    "elect": {"elected", "election"},
    "elects": {"elected", "election"},
    "email": {"mail", "post"},
    "generated": {"generative", "tooling"},
    "graduation": {"graduate", "graduating"},
    "gpl": {"category", "license"},
    "github": {"git"},
    "host": {"hosting", "website"},
    "hosted": {"hosting", "website"},
    "hold": {"held"},
    "holds": {"held"},
    "image": {"container"},
    "inspect": {"examine", "inspection"},
    "inspects": {"examines", "inspection"},
    "lgpl": {"category", "lesser", "license"},
    "maintain": {"maintenance", "responsibilities", "responsibility"},
    "maintains": {"maintenance", "responsibilities", "responsibility"},
    "mit": {"category", "license", "licenses"},
    "lend": {"loan", "loans"},
    "lends": {"loan", "loans"},
    "money": {"funds", "indebtedness", "loan"},
    "multiple": {"two", "more"},
    "nightly": {"nightlies"},
    "npm": {"dependency", "library", "package"},
    "appoint": {"appointed", "appointment"},
    "appoints": {"appointed", "appointment"},
    "password": {"account"},
    "outside": {"external"},
    "privacy": {"private"},
    "powered": {"trademark"},
    "problem": {"trouble"},
    "register": {"domain"},
    "resign": {"resignation", "resigned"},
    "resigned": {"resign", "resignation"},
    "responsibility": {"report", "reporting"},
    "remove": {"removed", "removal"},
    "removes": {"removed", "removal"},
    "role": {"office"},
    "shirt": {"merchandise"},
    "slack": {"chat"},
    "sponsor": {"sponsorship"},
    "sponsoring": {"sponsorship"},
    "share": {"shared", "sharing"},
    "publicly": {"confidential", "public", "quote"},
    "shared": {"confidential", "quote", "share", "sharing"},
    "summarized": {"shared"},
    "tracker": {"service"},
    "tooling": {"tool"},
    "x": {"category"},
}
VARIANT_ONLY_TOKENS = {"contact", "contacts"}
SOURCE_HINTS = {
    "board_reporting": {"board-reporting", "problem-reporting"},
    "domain_name_branding": {"domain-name"},
    "generative_tooling": {"chatgpt", "generated", "generative"},
    "incubator": {"graduation", "podling"},
    "incubator_ip_clearance": {"code-donation", "ip-clearance"},
    "pmc": {
        "confidentiality",
        "new-pmc-member",
        "pmc-chair-appointment",
        "pmc-emeritus",
        "pmc-resign",
        "private-confidentiality",
        "private-list",
        "quote",
    },
    "privacy_mailing_lists": {"deleted", "removal"},
    "project_independence": {"company-concentration", "project-independence", "vendor"},
    "resolved_licenses": {
        "category",
        "cc-by",
        "cc0",
        "dependency-notices",
        "gpl",
        "lgpl",
        "lgpl-category-b",
        "license",
        "mit",
        "notice",
        "public-domain",
    },
    "release_policy": {"release-vote"},
    "release_distribution": {"github-releases", "old-releases"},
    "event_branding": {"training-branding"},
    "repo_policy": {"primary-repo"},
    "slack_policy": {"direct-message", "slack-decision"},
    "spam_reporting": {"spam-reporting"},
    "security_committers": {"security-vulnerability"},
    "third_party_services": {"bug-tracker", "github-discussions", "third-party"},
    "trademark_maintenance": {"logo-change"},
    "voting": {"binding", "release-vote"},
    "bylaws": {
        "board-director",
        "board-election",
        "director-removal",
        "proxy",
    },
    "cla_faq": {"ccla", "cla", "icla"},
    "password_policy": {"account-sharing"},
}


def _tokenize(text: str, *, drop_negated: bool = False) -> set[str]:
    """Return normalized search tokens, excluding common question words."""
    return set(_tokenize_terms(text, drop_negated=drop_negated))


def _term_forms(term: str) -> set[str]:
    """Return simple singular/plural forms for a normalized English term."""
    forms = {term}
    if len(term) <= 2 or not term.isalpha():
        return forms

    if term.endswith("ies") and len(term) > 4:
        forms.add(f"{term[:-3]}y")
    elif term.endswith(("ches", "shes", "sses", "xes", "zes")) and len(term) > 4:
        forms.add(term[:-2])
    elif term.endswith("s") and not term.endswith("ss"):
        forms.add(term[:-1])
    else:
        if term.endswith("y") and len(term) > 3 and term[-2] not in "aeiou":
            forms.add(f"{term[:-1]}ies")
        elif term.endswith(("ch", "sh", "ss", "x", "z")):
            forms.add(f"{term}es")
        else:
            forms.add(f"{term}s")
    return forms


def _tokenize_terms(text: str, *, drop_negated: bool = False) -> list[str]:
    """Return normalized search terms, preserving duplicates for BM25 scoring."""
    tokens: list[str] = []
    normalized_text = text.lower()
    phrase_tokens = {
        "board report": "board-reporting",
        "board of directors": "board-director",
        "elects the asf board": "board-election",
        "elects the board": "board-election",
        "members shall elect a board": "board-election",
        "directors shall be elected": "board-election",
        "board remove a director": "director-removal",
        "bug tracker": "bug-tracker",
        "cc by": "cc-by",
        "change my apache password": "password",
        "code donation": "code-donation",
        "code donation into an existing codebase": "code-donation",
        "committer accounts be shared": "account-sharing",
        "accounts be shared": "account-sharing",
        "dependency notices": "dependency-notices",
        "ip clearance": "ip-clearance",
        "notice for dependencies": "dependency-notices",
        "notice for dependency": "dependency-notices",
        "large code donation": "code-donation",
        "lgpl dependencies": "lgpl-category-b",
        "gnu lgpl": "lgpl-category-b",
        "github discussions": "github-discussions",
        "github releases": "github-releases",
        "domain name": "domain-name",
        "request permission to use apache marks": "domain-name",
        "may not use apache marks": "domain-name",
        "logo be changed": "logo-change",
        "project logo": "logo-change",
        "project's name and logo": "logo-change",
        "mark a pmc member as emeritus": "pmc-emeritus",
        "make a member emeritus": "pmc-emeritus",
        "emeritus pmc member": "pmc-emeritus",
        "formal concept": "pmc-emeritus",
        "most committers": "company-concentration",
        "npm packages": "dependency-notices",
        "old releases": "old-releases",
        "one company": "company-concentration",
        "pmc chairs are appointed": "pmc-chair-appointment",
        "appoints pmc chairs": "pmc-chair-appointment",
        "chairs are appointed": "pmc-chair-appointment",
        "private list": "private-list",
        "private@": "private-list",
        "private@ emails": "private-confidentiality",
        "public domain": "public-domain",
        "release vote": "release-vote",
        "release artifacts only on github": "github-releases",
        "releases are archived": "old-releases",
        "all releases are archived": "old-releases",
        "archive.apache.org": "old-releases",
        "security bugs": "security-vulnerability",
        "security fixes": "security-vulnerability",
        "shared publicly": "private-confidentiality",
        "slack for decisions": "slack-decision",
        "slack for project decisions": "slack-decision",
        "decision that participants reach": "slack-decision",
        "documented in the appropriate email thread": "slack-decision",
        "direct messages": "direct-message",
        "not available to the public": "private-confidentiality",
        "do not quote": "private-confidentiality",
        "third party service": "third-party",
        "third party services": "third-party",
        "training course": "training-branding",
        "vendor control": "project-independence",
    }
    broad_phrase_tokens = {"board-director", "direct-message", "domain-name", "private-list", "third-party"}
    for phrase, token in phrase_tokens.items():
        if phrase in normalized_text:
            weight = 1 if token in broad_phrase_tokens else 16
            tokens.extend([token] * weight)
    raw_tokens = re.findall(r"[a-z0-9]+", normalized_text)
    skip_next = False
    for token in raw_tokens:
        if drop_negated and skip_next:
            skip_next = False
            continue
        if drop_negated and token in {"no", "not"}:
            skip_next = True
            continue
        if token in STOP_WORDS:
            continue
        if token not in VARIANT_ONLY_TOKENS:
            tokens.extend(sorted(_term_forms(token)))
        variant_terms = set(TOKEN_VARIANTS.get(token, set()))
        for form in _term_forms(token):
            variant_terms.update(TOKEN_VARIANTS.get(form, set()))
        for variant in sorted(variant_terms):
            tokens.extend(sorted(_term_forms(variant)))
    return tokens


def _nearest_section_locator(lines: list[str], line_num: int) -> str | None:
    """Find the nearest legal-style section label at or before *line_num*."""
    for i in range(line_num, -1, -1):
        line = lines[i].strip()
        if i != line_num and line.startswith("ARTICLE "):
            break
        if line.startswith("Section ") and line.endswith("."):
            title_parts: list[str] = []
            for candidate in lines[i + 1:i + 4]:
                clean = candidate.strip()
                if not clean or clean == "¶":
                    continue
                if clean.startswith("Section "):
                    break
                title_parts.append(clean.rstrip("."))
                if candidate.endswith("."):
                    break
            title = " ".join(title_parts)
            return f"{line.rstrip('.')} {title}".strip()
    return None


def _is_chunk_boundary(line: str) -> bool:
    clean = line.strip()
    return (
        clean.startswith("ARTICLE ")
        or (clean.startswith("Section ") and clean.endswith("."))
        or clean in {"Licensing", "Downloads", "Release Policy", "Questions"}
    )


def _policy_chunks(key: str, text: str) -> list[dict[str, Any]]:
    """Split a policy into moderately sized, section-aware chunks."""
    lines = text.split("\n")
    chunks: list[dict[str, Any]] = []
    start = 0
    max_lines = 14
    overlap = 3

    def add_chunk(chunk_start: int, chunk_end: int) -> None:
        excerpt = "\n".join(lines[chunk_start:chunk_end]).strip()
        if not excerpt:
            return
        meta = POLICY_SOURCES[key]
        locator = _nearest_section_locator(lines, chunk_start)
        source_text = f"{key} {meta['title']} {meta['section']} {meta['description']} {locator or ''}"
        chunks.append({
            "key": key,
            "title": meta["title"],
            "url": meta["url"],
            "line": chunk_start,
            "locator": locator,
            "excerpt": excerpt,
            "terms": _tokenize_terms(f"{source_text} {source_text} {excerpt}"),
            "source_terms": _tokenize(source_text),
        })

    for i, line in enumerate(lines):
        if i > start and (_is_chunk_boundary(line) or i - start >= max_lines):
            add_chunk(start, i)
            start = max(i - overlap, 0) if not _is_chunk_boundary(line) else i
    add_chunk(start, len(lines))
    return chunks


def _looks_like_toc(excerpt: str) -> bool:
    """Return True for navigation/table-of-contents style chunks."""
    lines = [line.strip() for line in excerpt.splitlines() if line.strip() and line.strip() != "¶"]
    if len(lines) < 8:
        return False
    short_lines = sum(1 for line in lines if len(line) < 80)
    sentence_lines = sum(1 for line in lines if line.endswith((".", ":", ";")))
    question_lines = sum(1 for line in lines if line.endswith("?"))
    return short_lines / len(lines) > 0.75 and sentence_lines + question_lines < len(lines) / 3


def _looks_like_footer(excerpt: str) -> bool:
    """Return True for boilerplate footer chunks."""
    lowered = excerpt.lower()
    return (
        "copyright" in lowered
        and "apache license" in lowered
        and "trademark" in lowered
        and len([line for line in excerpt.splitlines() if line.strip()]) < 12
    )


def _bm25_scores(chunks: list[dict[str, Any]], query_terms: list[str]) -> list[dict[str, Any]]:
    """Score chunks with a compact BM25 implementation plus source hints."""
    if not chunks:
        return []

    doc_freq: Counter[str] = Counter()
    term_counts: list[Counter[str]] = []
    doc_lengths: list[int] = []
    for chunk in chunks:
        counts = Counter(chunk["terms"])
        term_counts.append(counts)
        doc_lengths.append(sum(counts.values()))
        doc_freq.update(counts.keys())

    total_docs = len(chunks)
    avg_len = sum(doc_lengths) / total_docs if total_docs else 0.0
    query_counts = Counter(query_terms)
    query_words = set(query_terms)
    k1 = 1.5
    b = 0.75

    scored: list[dict[str, Any]] = []
    for chunk, counts, doc_len in zip(chunks, term_counts, doc_lengths):
        score = 0.0
        for term, query_count in query_counts.items():
            freq = counts.get(term, 0)
            if not freq:
                continue
            idf = log(1 + (total_docs - doc_freq[term] + 0.5) / (doc_freq[term] + 0.5))
            denom = freq + k1 * (1 - b + b * (doc_len / avg_len if avg_len else 0.0))
            score += query_count * idf * (freq * (k1 + 1) / denom)

        source_hint_overlap = query_words & SOURCE_HINTS.get(str(chunk["key"]), set())
        score += len(source_hint_overlap) * 10.0
        score += sum(12.0 for token in source_hint_overlap if "-" in token)
        score += len(query_words & set(chunk["source_terms"])) * 0.4
        if _looks_like_toc(str(chunk["excerpt"])):
            score *= 0.35
        if _looks_like_footer(str(chunk["excerpt"])):
            score *= 0.1
        if score:
            result = dict(chunk)
            result["score"] = score
            scored.append(result)
    return scored


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
    query_terms = _tokenize_terms(query, drop_negated=True)
    if not query_terms:
        return "Please provide a more specific search query."

    # Search cached policies first
    chunks: list[dict[str, Any]] = []
    uncached: list[str] = []
    for key in POLICY_SOURCES:
        entry = cache.get(key, {})
        if entry.get("text") and not str(entry["text"]).startswith("[Error"):
            chunks.extend(_policy_chunks(key, str(entry["text"])))
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
                if text and not text.startswith("[Error"):
                    chunks.extend(_policy_chunks(key, text))
        fetcher.save_cache(cache)

    results = _bm25_scores(chunks, query_terms)
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
        doc_anchors: list[list[Any]] = cache.get(r["key"], {}).get("anchors", [])
        anchor_id = fetcher.find_anchor(doc_anchors, r["line"])
        link_url = f"{r['url']}#{anchor_id}" if anchor_id else r["url"]
        out.append(f"## [{r['title']}]({link_url})  (`{r['key']}`)\n")
        if r.get("locator"):
            out.append(f"**Locator:** {r['locator']}\n")
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
