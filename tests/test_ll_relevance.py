"""
tests/test_ll_relevance.py

TDD — tests for per-team relevance scoring.

The scorer takes an entry dict (from parse_ll_file) and returns a list of
team keys whose keywords appear in the entry's title/severity/affected/body.

Contract:
  - Universal keywords (submodule, dispatch, runtime, tier_model, etc.)
    hit ALL 11 teams.
  - Team-specific keywords hit only that team.
  - Scoring is case-insensitive, substring-based.
  - An entry with no hits returns [].
"""
from textwrap import dedent

import pytest


TEAM_KEYS = {
    "dev", "ds", "design", "legal", "marketing",
    "strategy", "qa", "hr", "finance", "video", "sme",
}


def _make_entry(**kwargs):
    """Build a minimal entry dict with sensible defaults."""
    return {
        "ll_id":    kwargs.get("ll_id", "LL-TEST"),
        "title":    kwargs.get("title", ""),
        "date":     kwargs.get("date", "2026-01-01"),
        "severity": kwargs.get("severity", "MEDIUM"),
        "affected": kwargs.get("affected", ""),
        "body":     kwargs.get("body", ""),
    }


# ------------------------------------------------------------------------
# Import check
# ------------------------------------------------------------------------

def test_relevance_is_importable():
    from agents.curators.lessons_learned.relevance import (  # noqa: F401
        score_relevance,
        TEAM_KEYWORDS,
        UNIVERSAL_KEYWORDS,
    )


def test_universal_hits_all_teams():
    from agents.curators.lessons_learned.relevance import score_relevance

    entry = _make_entry(
        title="Something about submodule dispatch",
        body="talk about runtime and tier_model choices",
    )
    teams = set(score_relevance(entry))
    assert teams == TEAM_KEYS


def test_real_ll040_shape_hits_all_teams():
    """
    LL-040 talks about submodule/dispatch/runtime — classic universal
    architectural lesson. Must produce the full 11-team list.
    """
    from agents.curators.lessons_learned.relevance import score_relevance

    entry = _make_entry(
        ll_id="LL-040",
        title="Verify runtime dispatch path before patching a submodule-based system",
        affected="All reasoning agents on design, legal, strategy, QA, and marketing teams",
        body=dedent("""\
            The first-attempt patch changed templates/, which invoke_team_flow never touches.
            Before patching a submodule-dispatched system, trace the dispatch path.
            The base factory was routing every design agent to TIER2_MODEL when design
            is reasoning/visual judgment work that belongs on TIER1_MODEL.
        """),
    )
    teams = set(score_relevance(entry))
    assert teams == TEAM_KEYS


def test_legal_only_ukgc_entry():
    """A UKGC entry must hit legal and no one else."""
    from agents.curators.lessons_learned.relevance import score_relevance

    entry = _make_entry(
        title="UKGC affordability guidance updated",
        affected="Legal team",
        body="The UK Gambling Commission published new guidance on affordability.",
    )
    teams = score_relevance(entry)
    assert "legal" in teams
    # Should not spuriously drag in other teams
    assert "ds" not in teams
    assert "dev" not in teams
    assert "marketing" not in teams


def test_cve_hits_dev_and_qa():
    from agents.curators.lessons_learned.relevance import score_relevance

    entry = _make_entry(
        title="CVE-2025-XXXX in example-lib",
        affected="Dev, QA",
        body="Critical dependency vulnerability; OWASP top-10 category.",
    )
    teams = set(score_relevance(entry))
    assert "dev" in teams
    assert "qa" in teams


def test_ds_only_xg_entry():
    from agents.curators.lessons_learned.relevance import score_relevance

    entry = _make_entry(
        title="xG model Brier score drift",
        body="Bayesian update mid-season caused calibration regression.",
    )
    teams = score_relevance(entry)
    assert "ds" in teams
    assert "legal" not in teams
    assert "marketing" not in teams


def test_marketing_only_platform_policy_entry():
    from agents.curators.lessons_learned.relevance import score_relevance

    entry = _make_entry(
        title="Meta gambling ad policy change",
        body="Instagram/Reddit AI-generated content disclosure requirement.",
    )
    teams = score_relevance(entry)
    assert "marketing" in teams
    assert "legal" not in teams  # ambiguous — but ad policy is primarily marketing


def test_empty_entry_returns_empty_list():
    from agents.curators.lessons_learned.relevance import score_relevance

    entry = _make_entry(title="", body="", affected="", severity="")
    assert score_relevance(entry) == []


def test_case_insensitive():
    from agents.curators.lessons_learned.relevance import score_relevance

    entry = _make_entry(
        title="UKGC COMPLIANCE",  # all caps
        body="ukgc is shouting",  # all lower
    )
    assert "legal" in score_relevance(entry)


def test_team_keywords_cover_all_11_teams():
    """Every team in the 11-team architecture must have a keyword list."""
    from agents.curators.lessons_learned.relevance import TEAM_KEYWORDS
    assert set(TEAM_KEYWORDS.keys()) == TEAM_KEYS, (
        f"missing teams: {TEAM_KEYS - set(TEAM_KEYWORDS.keys())}, "
        f"extra teams: {set(TEAM_KEYWORDS.keys()) - TEAM_KEYS}"
    )
