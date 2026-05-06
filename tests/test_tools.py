from __future__ import annotations

import time

import pytest

from asf_policy_mcp import fetcher, tools
from asf_policy_mcp.sources import POLICY_SOURCES


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def isolated_cache(monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory) -> None:
    """Redirect cache I/O to a temp dir so tests never touch ~/.cache."""
    monkeypatch.setattr(fetcher, "CACHE_FILE", tmp_path / "policy_cache.json")  # type: ignore[arg-type]
    monkeypatch.setattr(fetcher, "CACHE_TTL", 30 * 24 * 3600)


def seed_cache(*keys: str, text: str = "Policy text here.", age: float = 0.0) -> None:
    """Write a pre-populated cache file for the given policy keys."""
    fetcher.save_cache({
        key: {"text": text, "fetched_at": time.time() - age, "url": POLICY_SOURCES[key]["url"]}
        for key in keys
    })


def patch_fetch(monkeypatch: pytest.MonkeyPatch, responses: dict[str, str]) -> list[str]:
    """Replace fetcher.fetch_page and fetch_page_text with stubs returning *responses[url]*."""
    calls: list[str] = []

    def fake_fetch_page(url: str) -> tuple[str, list]:
        calls.append(url)
        return responses.get(url, f"[stub: no response for {url}]"), []

    def fake_fetch_page_text(url: str) -> str:
        text, _ = fake_fetch_page(url)
        return text

    monkeypatch.setattr(fetcher, "fetch_page", fake_fetch_page)
    monkeypatch.setattr(fetcher, "fetch_page_text", fake_fetch_page_text)
    return calls


# ---------------------------------------------------------------------------
# html_to_text
# ---------------------------------------------------------------------------

def test_html_to_text_extracts_body_text() -> None:
    # BS4 inserts the separator at tag boundaries, so inline elements split onto their own line
    result = fetcher.html_to_text("<p>Hello <strong>world</strong></p>")
    assert "Hello" in result
    assert "world" in result


def test_html_to_text_strips_nav_and_script() -> None:
    html = "<nav>Skip</nav><script>alert(1)</script><main><p>Content</p></main>"
    assert fetcher.html_to_text(html) == "Content"


def test_html_to_text_collapses_blank_lines() -> None:
    result = fetcher.html_to_text("<p>A</p>\n\n\n\n\n<p>B</p>")
    assert "\n\n\n" not in result


def test_html_to_text_decodes_entities() -> None:
    result = fetcher.html_to_text("<p>A &amp; B</p>")
    assert "&amp;" not in result
    assert "A & B" in result


# ---------------------------------------------------------------------------
# cache load / save
# ---------------------------------------------------------------------------

def test_load_cache_returns_empty_dict_when_file_missing() -> None:
    assert fetcher.load_cache() == {}


def test_load_cache_returns_empty_dict_on_corrupt_json(monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory) -> None:  # type: ignore[override]
    p = tmp_path / "bad.json"  # type: ignore[operator]
    p.write_text("{bad json", encoding="utf-8")
    monkeypatch.setattr(fetcher, "CACHE_FILE", p)
    assert fetcher.load_cache() == {}


def test_save_and_load_cache_roundtrip() -> None:
    cache = {"release_policy": {"text": "hello", "fetched_at": 1.0, "url": "https://example.com"}}
    fetcher.save_cache(cache)
    assert fetcher.load_cache() == cache


# ---------------------------------------------------------------------------
# get_policy_text — cache hit / miss / TTL
# ---------------------------------------------------------------------------

def test_get_policy_text_returns_cached_value_without_fetching(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = patch_fetch(monkeypatch, {})
    seed_cache("release_policy", text="Cached content")
    cache = fetcher.load_cache()

    result = fetcher.get_policy_text("release_policy", cache)

    assert result == "Cached content"
    assert calls == []


def test_get_policy_text_fetches_when_cache_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    url = POLICY_SOURCES["release_policy"]["url"]
    calls = patch_fetch(monkeypatch, {url: "Fresh content"})
    cache: dict = {}

    result = fetcher.get_policy_text("release_policy", cache)

    assert result == "Fresh content"
    assert calls == [url]
    assert cache["release_policy"]["text"] == "Fresh content"


def test_get_policy_text_fetches_when_entry_is_stale(monkeypatch: pytest.MonkeyPatch) -> None:
    url = POLICY_SOURCES["branding"]["url"]
    patch_fetch(monkeypatch, {url: "Refreshed"})
    seed_cache("branding", text="Old", age=31 * 24 * 3600)
    cache = fetcher.load_cache()

    result = fetcher.get_policy_text("branding", cache)

    assert result == "Refreshed"


def test_get_policy_text_force_bypasses_fresh_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    url = POLICY_SOURCES["voting"]["url"]
    patch_fetch(monkeypatch, {url: "Force-refreshed"})
    seed_cache("voting", text="Still fresh")
    cache = fetcher.load_cache()

    result = fetcher.get_policy_text("voting", cache, force=True)

    assert result == "Force-refreshed"


# ---------------------------------------------------------------------------
# tools.list_policies
# ---------------------------------------------------------------------------

def test_list_policies_includes_all_keys() -> None:
    result = tools.list_policies()
    for key in POLICY_SOURCES:
        assert key in result


def test_list_policies_shows_cache_age_for_cached_entries() -> None:
    seed_cache("release_policy", age=7200)
    result = tools.list_policies()
    assert "cached" in result


def test_list_policies_shows_not_fetched_for_empty_cache() -> None:
    result = tools.list_policies()
    assert "not yet fetched" in result


# ---------------------------------------------------------------------------
# tools.get_policy
# ---------------------------------------------------------------------------

def test_get_policy_returns_cached_content(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_fetch(monkeypatch, {})
    seed_cache("incubator", text="Incubator policy text")

    result = tools.get_policy("incubator")

    assert "Incubator policy text" in result
    assert POLICY_SOURCES["incubator"]["url"] in result


def test_get_policy_returns_error_for_unknown_key() -> None:
    result = tools.get_policy("nonexistent_key")
    assert "Unknown policy key" in result
    assert "nonexistent_key" in result


def test_get_policy_includes_section_and_source(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_fetch(monkeypatch, {})
    seed_cache("branding", text="Branding rules")

    result = tools.get_policy("branding")

    assert "Branding" in result
    assert "Source:" in result


def test_get_policy_force_refresh_re_fetches(monkeypatch: pytest.MonkeyPatch) -> None:
    url = POLICY_SOURCES["release_policy"]["url"]
    calls = patch_fetch(monkeypatch, {url: "Updated text"})
    seed_cache("release_policy", text="Old text")

    result = tools.get_policy("release_policy", force_refresh=True)

    assert "Updated text" in result
    assert calls == [url]


# ---------------------------------------------------------------------------
# tools.search_policies
# ---------------------------------------------------------------------------

def test_search_policies_finds_matching_text() -> None:
    seed_cache("release_policy", text="A release must be voted on by the PMC.")

    result = tools.search_policies("voted PMC")

    assert "release_policy" in result
    assert "voted" in result


def test_search_policies_returns_no_results_message() -> None:
    seed_cache("release_policy", text="unrelated text")

    result = tools.search_policies("xyzzy_not_found_anywhere")

    assert "No results" in result


def test_search_policies_fetches_uncached_policies(monkeypatch: pytest.MonkeyPatch) -> None:
    # Only seed one policy — uncached ones should be auto-fetched and searched
    seed_cache("voting", text="voting rules here")
    patch_fetch(monkeypatch, {meta["url"]: "xyzzy unique content" for meta in POLICY_SOURCES.values()})

    result = tools.search_policies("xyzzy unique content")

    # Should find results from the auto-fetched policies, not report them as skipped
    assert "No results" not in result
    assert "uncached" not in result


def test_search_policies_empty_query_returns_prompt() -> None:
    result = tools.search_policies("   ")
    assert "provide a search query" in result.lower()


def test_search_policies_deduplicates_nearby_lines() -> None:
    seed_cache("voting", text="\n".join(["vote vote vote"] * 20))

    result = tools.search_policies("vote", max_results=5)

    assert result.count("```") <= 12  # at most 5 pairs + some buffer


def test_search_policies_respects_max_results() -> None:
    seed_cache(*POLICY_SOURCES.keys(), text="license text here")

    result = tools.search_policies("license", max_results=3)

    assert result.count("```") == 6  # 3 results × opening + closing


# ---------------------------------------------------------------------------
# tools.refresh_cache
# ---------------------------------------------------------------------------

def test_refresh_cache_updates_stored_content(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_fetch(monkeypatch, {POLICY_SOURCES["security"]["url"]: "Updated security guidance"})

    result = tools.refresh_cache(["security"])

    assert "security" in result
    assert fetcher.load_cache()["security"]["text"] == "Updated security guidance"


def test_refresh_cache_reports_unknown_key() -> None:
    result = tools.refresh_cache(["does_not_exist"])
    assert "Unknown key" in result
    assert "does_not_exist" in result


def test_refresh_cache_all_when_keys_is_none(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_fetch(monkeypatch, {meta["url"]: "ok" for meta in POLICY_SOURCES.values()})

    result = tools.refresh_cache()

    assert f"Refreshed {len(POLICY_SOURCES)} policies" in result
    assert len(fetcher.load_cache()) == len(POLICY_SOURCES)
