"""
tests/test_new_curators.py

TDD — structural + registry tests for the 4 new Day 5 curators
(finance, hr, video, sme).

Covers:
  - curator.py file exists at agents/curators/<team>/curator.py
  - module imports cleanly
  - exposes a module-level SOURCES list (non-empty, shape matches the
    existing curator pattern)
  - has a fetch_and_store(source, topic=None) callable
  - TEAM_DOMAINS in knowledge_base includes each new team with a
    non-empty domain list
  - Every domain key referenced by a SOURCES entry exists in
    TEAM_DOMAINS for that team (catches copy/paste drift)

The HITL invariant (imports propose_knowledge, never calls
store_knowledge) is already covered by the parametrized test in
test_all_curator_migrations.py — adding these 4 teams to that file's
list implicitly adds 12 more invariant tests.
"""
import importlib
import sys
from pathlib import Path

import pytest

SUBMODULE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUBMODULE_ROOT))

CURATORS_DIR = SUBMODULE_ROOT / "agents" / "curators"

NEW_TEAMS = ["finance", "hr", "video", "sme"]


def _import_curator(team: str):
    """Dynamically import agents.curators.<team>.curator."""
    mod_name = f"agents.curators.{team}.curator"
    if mod_name in sys.modules:
        return importlib.reload(sys.modules[mod_name])
    return importlib.import_module(mod_name)


# ------------------------------------------------------------------------
# Per-curator structural tests
# ------------------------------------------------------------------------

@pytest.mark.parametrize("team", NEW_TEAMS)
def test_curator_file_exists(team):
    path = CURATORS_DIR / team / "curator.py"
    assert path.exists(), f"missing {path}"


@pytest.mark.parametrize("team", NEW_TEAMS)
def test_curator_package_has_init(team):
    init = CURATORS_DIR / team / "__init__.py"
    assert init.exists(), f"missing {init}"


@pytest.mark.parametrize("team", NEW_TEAMS)
def test_curator_imports_cleanly(team):
    mod = _import_curator(team)
    assert mod is not None


@pytest.mark.parametrize("team", NEW_TEAMS)
def test_curator_has_sources_list(team):
    mod = _import_curator(team)
    assert hasattr(mod, "SOURCES"), f"{team} curator missing SOURCES"
    assert isinstance(mod.SOURCES, list)
    assert len(mod.SOURCES) > 0, f"{team} SOURCES is empty"


@pytest.mark.parametrize("team", NEW_TEAMS)
def test_curator_sources_have_required_fields(team):
    """
    Every SOURCES entry must have name, url, domain, priority — the
    contract all 7 existing curators already honour.
    """
    mod = _import_curator(team)
    required = {"name", "url", "domain", "priority"}
    for src in mod.SOURCES:
        missing = required - set(src.keys())
        assert not missing, (
            f"{team} source {src.get('name', '?')} missing fields: {missing}"
        )


@pytest.mark.parametrize("team", NEW_TEAMS)
def test_curator_has_fetch_and_store(team):
    mod = _import_curator(team)
    assert callable(getattr(mod, "fetch_and_store", None)), (
        f"{team} curator missing fetch_and_store()"
    )


# ------------------------------------------------------------------------
# TEAM_DOMAINS registration
# ------------------------------------------------------------------------

def test_team_domains_includes_all_new_teams(clean_env):
    """All 4 new teams must be registered in TEAM_DOMAINS."""
    if "knowledge.knowledge_base" in sys.modules:
        importlib.reload(sys.modules["knowledge.knowledge_base"])
    from knowledge.knowledge_base import TEAM_DOMAINS

    for team in NEW_TEAMS:
        assert team in TEAM_DOMAINS, (
            f"{team} missing from TEAM_DOMAINS — "
            f"orchestrator's run_full_refresh won't pick it up"
        )
        assert len(TEAM_DOMAINS[team]) > 0, (
            f"{team} has an empty domain list"
        )


@pytest.mark.parametrize("team", NEW_TEAMS)
def test_source_domains_match_team_domains(clean_env, team):
    """
    Catch copy/paste drift: every domain key referenced in a SOURCES
    entry must be registered in TEAM_DOMAINS for that team.
    """
    if "knowledge.knowledge_base" in sys.modules:
        importlib.reload(sys.modules["knowledge.knowledge_base"])
    from knowledge.knowledge_base import TEAM_DOMAINS

    mod = _import_curator(team)
    registered = set(TEAM_DOMAINS.get(team, []))
    referenced = {src["domain"] for src in mod.SOURCES}
    unregistered = referenced - registered
    assert not unregistered, (
        f"{team} SOURCES reference unregistered domains: {unregistered}. "
        f"Registered: {registered}"
    )


# ------------------------------------------------------------------------
# SME-specific: must cover all 16 sub-domains
# ------------------------------------------------------------------------

def test_sme_covers_all_16_subdomains(clean_env):
    """
    SME spans 16 sports-betting sub-domains. Per Day 5 design decision
    (option A), they all live in one curator. Every one must appear in
    both TEAM_DOMAINS['sme'] and in SOURCES.
    """
    if "knowledge.knowledge_base" in sys.modules:
        importlib.reload(sys.modules["knowledge.knowledge_base"])
    from knowledge.knowledge_base import TEAM_DOMAINS

    expected_sme_domains = {
        "sports_betting",
        "world_football",
        "nba_ncaa_basketball",
        "nfl_ncaa_football",
        "mlb",
        "nhl_ncaa_hockey",
        "mma",
        "tennis",
        "world_rugby",
        "cricket",
        "wnba_ncaa_womens_basketball",
        "thoroughbred_horse_racing",
        "harness_racing",
        "mens_boxing",
        "pga",
        "lpga",
    }
    registered = set(TEAM_DOMAINS.get("sme", []))
    missing = expected_sme_domains - registered
    assert not missing, f"SME TEAM_DOMAINS missing: {missing}"

    mod = _import_curator("sme")
    referenced = {src["domain"] for src in mod.SOURCES}
    uncovered = expected_sme_domains - referenced
    assert not uncovered, (
        f"SME SOURCES has no entry covering these sub-domains: {uncovered}"
    )
