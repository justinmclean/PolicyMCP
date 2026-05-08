from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import pytest

from asf_policy_mcp import fetcher, tools
from asf_policy_mcp.sources import POLICY_SOURCES


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def isolated_cache(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Redirect cache I/O to a temp dir so tests never touch ~/.cache."""
    monkeypatch.setattr(fetcher, "CACHE_FILE", tmp_path / "policy_cache.json")
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

    def fake_fetch_page(url: str) -> tuple[str, list[Any]]:
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


def test_load_cache_returns_empty_dict_on_corrupt_json(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    p = tmp_path / "bad.json"
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
    cache: dict[str, Any] = {}

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


def test_search_policies_asks_for_more_specific_query_when_only_stopwords() -> None:
    result = tools.search_policies("how do the")
    assert "more specific" in result.lower()


def test_policy_bearing_words_are_not_stopwords() -> None:
    tokens = tools._tokenize("deleted company before accepted main other each not", drop_negated=False)

    assert {"deleted", "company", "before", "accepted", "main", "other", "each", "not"} <= tokens


def test_tokenizer_handles_common_plural_forms_without_explicit_variants() -> None:
    tokens = tools._tokenize("dependencies policies boxes committers")

    assert {"dependency", "dependencies", "policy", "policies", "box", "boxes", "committer", "committers"} <= tokens


def test_tokenizer_applies_variants_to_singular_and_plural_forms() -> None:
    tokens = tools._tokenize("dependencies")

    assert {"dependency", "dependencies", "library", "libraries"} <= tokens


def test_search_policies_deduplicates_nearby_lines() -> None:
    seed_cache("voting", text="\n".join(["vote vote vote"] * 20))

    result = tools.search_policies("vote", max_results=5)

    assert result.count("```") <= 12  # at most 5 pairs + some buffer


def test_search_policies_respects_max_results() -> None:
    seed_cache(*POLICY_SOURCES.keys(), text="license text here")

    result = tools.search_policies("license", max_results=3)

    assert result.count("```") == 6  # 3 results × opening + closing


def test_search_policies_includes_nearest_section_locator() -> None:
    seed_cache("bylaws", text="\n".join([
        "Section 3.9.",
        "Quorum and Voting Requirements.",
        "The directors shall be elected by a plurality of the votes.",
    ]))

    result = tools.search_policies("plurality votes")

    assert "**Locator:** Section 3.9 Quorum and Voting Requirements" in result


def test_nearest_section_locator_returns_none_without_section() -> None:
    assert tools._nearest_section_locator(["No formal section", "matching text"], 1) is None


def test_search_policies_ignores_question_stopwords_for_ranking() -> None:
    seed_cache(
        "pmc",
        text="The chair reports to the board and ultimately to the ASF membership.",
    )
    seed_cache(
        "bylaws",
        text="\n".join([
            "Section 3.2.",
            "Annual Meeting.",
            "At the annual meeting the members shall elect a Board of Directors.",
        ]),
    )

    result = tools.search_policies("How do ASF members elect the board members?", max_results=1)

    assert "(`bylaws`)" in result
    assert "(`pmc`)" not in result


def test_search_policies_uses_source_metadata_for_policy_specific_queries() -> None:
    fetcher.save_cache({
        "release_distribution": {
            "text": "Projects must publish releases through the ASF distribution system.",
            "fetched_at": time.time(),
            "url": POLICY_SOURCES["release_distribution"]["url"],
        },
        "release_policy": {
            "text": "Release artifacts are voted on by PMC members.",
            "fetched_at": time.time(),
            "url": POLICY_SOURCES["release_policy"]["url"],
        },
    })

    result = tools.search_policies("Can releases be distributed only on GitHub releases?", max_results=1)

    assert "(`release_distribution`)" in result
    assert "(`release_policy`)" not in result


def test_search_policies_keeps_graduation_searchable() -> None:
    fetcher.save_cache({
        "incubator": {
            "text": "Guide to successful graduation for podlings.",
            "fetched_at": time.time(),
            "url": POLICY_SOURCES["incubator"]["url"],
        },
        "podling_branding": {
            "text": "Podling branding requirements.",
            "fetched_at": time.time(),
            "url": POLICY_SOURCES["podling_branding"]["url"],
        },
    })

    result = tools.search_policies("What is required for podling graduation?", max_results=1)

    assert "(`incubator`)" in result


def test_search_policies_prefers_resolved_licenses_for_gpl_questions() -> None:
    fetcher.save_cache({
        "release_policy": {
            "text": "Every release must contain appropriately licensed source code.",
            "fetched_at": time.time(),
            "url": POLICY_SOURCES["release_policy"]["url"],
        },
        "resolved_licenses": {
            "text": "GPL is listed in Category X.",
            "fetched_at": time.time(),
            "url": POLICY_SOURCES["resolved_licenses"]["url"],
        },
    })

    result = tools.search_policies("Is GPL code allowed in a release?", max_results=1)

    assert "(`resolved_licenses`)" in result
    assert "(`release_policy`)" not in result


def test_search_policies_prefers_resolved_licenses_for_mit_questions() -> None:
    fetcher.save_cache({
        "release_policy": {
            "text": "Every release must contain appropriately licensed source code.",
            "fetched_at": time.time(),
            "url": POLICY_SOURCES["release_policy"]["url"],
        },
        "resolved_licenses": {
            "text": "MIT is listed in Category A.",
            "fetched_at": time.time(),
            "url": POLICY_SOURCES["resolved_licenses"]["url"],
        },
    })

    result = tools.search_policies("Is MIT code allowed in a release?", max_results=1)

    assert "(`resolved_licenses`)" in result
    assert "(`release_policy`)" not in result


def test_search_policies_prefers_specific_mit_license_excerpt() -> None:
    seed_cache(
        "resolved_licenses",
        text="\n".join([
            "From Java 9 onwards, Javadoc can include JavaScript under MIT or GPL.",
            "It must not be included in source releases.",
            "Category A: What can we include in an ASF Project?",
            "For inclusion in an Apache Software Foundation product, these licenses are similar.",
            "MIT/X11",
        ]),
    )

    result = tools.search_policies("Is MIT code allowed in an Apache release?", max_results=1)

    assert "MIT/X11" in result


def test_search_policies_prefers_specific_lgpl_license_excerpt() -> None:
    seed_cache(
        "resolved_licenses",
        text="\n".join([
            "From Java 9 onwards, Javadoc can include JavaScript under MIT or GPL.",
            "Category B: What can we maybe include in an ASF Project?",
            "Places restrictions on larger works:",
            "GNU LGPL 2, 2.1, 3",
        ]),
    )

    result = tools.search_policies("Can we use LGPL dependencies in a binary release?", max_results=1)

    assert "GNU LGPL" in result


def test_search_policies_uses_phrase_hints_for_common_project_questions() -> None:
    fetcher.save_cache({
        "pmc": {
            "text": "Committers work on the project and earn karma.",
            "fetched_at": time.time(),
            "url": POLICY_SOURCES["pmc"]["url"],
        },
        "project_independence": {
            "text": "Apache projects are independent from vendor control.",
            "fetched_at": time.time(),
            "url": POLICY_SOURCES["project_independence"]["url"],
        },
    })

    result = tools.search_policies("What if most committers work for one company?", max_results=1)

    assert "(`project_independence`)" in result


def test_search_policies_distinguishes_third_party_services_from_license_notices() -> None:
    fetcher.save_cache({
        "third_party_services": {
            "text": "Third party services may be used by projects.",
            "fetched_at": time.time(),
            "url": POLICY_SOURCES["third_party_services"]["url"],
        },
        "resolved_licenses": {
            "text": "Third party license notices belong in LICENSE and NOTICE files.",
            "fetched_at": time.time(),
            "url": POLICY_SOURCES["resolved_licenses"]["url"],
        },
    })

    service_result = tools.search_policies("Can we use a third party service?", max_results=1)
    notice_result = tools.search_policies("Where do third party license notices go?", max_results=1)

    assert "(`third_party_services`)" in service_result
    assert "(`resolved_licenses`)" in notice_result


def test_search_policies_routes_common_notice_ip_and_account_questions() -> None:
    fetcher.save_cache({
        "resolved_licenses": {
            "text": "NOTICE and LICENSE document third-party dependency notices.",
            "fetched_at": time.time(),
            "url": POLICY_SOURCES["resolved_licenses"]["url"],
        },
        "incubator_ip_clearance": {
            "text": "IP clearance requires votes before accepting a code donation.",
            "fetched_at": time.time(),
            "url": POLICY_SOURCES["incubator_ip_clearance"]["url"],
        },
        "password_policy": {
            "text": "Apache accounts and passwords must not be shared.",
            "fetched_at": time.time(),
            "url": POLICY_SOURCES["password_policy"]["url"],
        },
    })

    assert "(`resolved_licenses`)" in tools.search_policies("What needs to be in NOTICE?", max_results=1)
    assert "(`incubator_ip_clearance`)" in tools.search_policies("Who votes on IP clearance?", max_results=1)
    assert "(`password_policy`)" in tools.search_policies("Can committer accounts be shared?", max_results=1)


def test_search_policies_prefers_confidentiality_excerpt_for_private_list_questions() -> None:
    fetcher.save_cache({
        "pmc": {
            "text": "\n".join([
                "Account request form",
                "To: infrastructure",
                "Cc: private@example.apache.org, committer@example.org",
                "Subject: Machine account request",
                "Userid: example",
                "Machine: example",
                "Groups required: example",
                "Reason: account required",
                "Vote: private archive reference",
                "The administrator will reply accordingly.",
                "More account request details.",
                "More account request details.",
                "More account request details.",
                "More account request details.",
                "There are a number of Apache lists whose archives are not available to the public.",
                "Posts to these lists are considered confidential.",
                "Do not quote them on public lists or outside the ASF without permission of the author.",
                "PMC members may search archives of their project's private list.",
            ]),
            "fetched_at": time.time(),
            "url": POLICY_SOURCES["pmc"]["url"],
        },
    })

    result = tools.search_policies("Can private@ emails be shared publicly?", max_results=1)

    assert "Do not quote" in result


def test_search_policies_prefers_board_election_excerpt() -> None:
    seed_cache(
        "bylaws",
        text="\n".join([
            "Section 2.2.",
            "Other States.",
            "The corporation elects to qualify in another state.",
            "Section 3.2.",
            "Annual Meeting.",
            "The members shall elect a Board of Directors and transact other proper business.",
        ]),
    )

    result = tools.search_policies("Who elects the ASF Board of Directors?", max_results=1)

    assert "members shall elect a Board of Directors" in result


def test_search_policies_prefers_pmc_chair_appointment_excerpt() -> None:
    seed_cache(
        "pmc",
        text="\n".join([
            "Chairs may write board reports.",
            "Reports are ultimately the chair's responsibility.",
            "PMC Chairs are appointed by the board to be the Vice President of their top level project.",
        ]),
    )

    result = tools.search_policies("Who appoints PMC chairs?", max_results=1)

    assert "appointed by the board" in result


def test_search_policies_prefers_pmc_emeritus_excerpt_over_bylaws_membership() -> None:
    fetcher.save_cache({
        "bylaws": {
            "text": "Section 4.2.\nEmeritus Members.\nEmeritus members of the corporation may attend meetings.",
            "fetched_at": time.time(),
            "url": POLICY_SOURCES["bylaws"]["url"],
        },
        "pmc": {
            "text": "\n".join([
                "How to mark a PMC member as resigned or emeritus",
                'The ASF does not have any formal concept for an "emeritus PMC member" - an individual is either a member of the PMC or not.',
            ]),
            "fetched_at": time.time(),
            "url": POLICY_SOURCES["pmc"]["url"],
        },
    })

    result = tools.search_policies("Can a PMC make a member emeritus?", max_results=1)

    assert "formal concept" in result
    assert "(`pmc`)" in result


def test_search_policies_prefers_old_release_archive_excerpt() -> None:
    seed_cache(
        "release_distribution",
        text="\n".join([
            "New releases must supply SHA-256 checksums.",
            "All releases, including old releases, are archived automatically.",
            "All releases are archived automatically on archive.apache.org.",
        ]),
    )

    result = tools.search_policies("Where should old releases be kept?", max_results=1)

    assert "archive.apache.org" in result


def test_search_policies_prefers_slack_policy_for_slack_decisions() -> None:
    fetcher.save_cache({
        "pmc": {
            "text": "The PMC makes decisions on mailing lists.",
            "fetched_at": time.time(),
            "url": POLICY_SOURCES["pmc"]["url"],
        },
        "slack_policy": {
            "text": "Any decision reached in Slack direct messages must be documented in the appropriate email thread.",
            "fetched_at": time.time(),
            "url": POLICY_SOURCES["slack_policy"]["url"],
        },
    })

    result = tools.search_policies("Can a project use Slack for decisions?", max_results=1)

    assert "(`slack_policy`)" in result


def test_search_policies_prefers_domain_policy_over_general_branding() -> None:
    fetcher.save_cache({
        "branding": {
            "text": "Project branding includes names and domain references.",
            "fetched_at": time.time(),
            "url": POLICY_SOURCES["branding"]["url"],
        },
        "domain_name_branding": {
            "text": "You may be eligible to request permission to use Apache marks in your domain name.",
            "fetched_at": time.time(),
            "url": POLICY_SOURCES["domain_name_branding"]["url"],
        },
    })

    result = tools.search_policies("Can we register an apache project domain name?", max_results=1)

    assert "(`domain_name_branding`)" in result


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
