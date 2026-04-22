"""
tests/test_project_registry.py

TDD — per-project collection layer.

Contract (per Phase 2 kickoff doc Day 4 + Day 4 design decisions):
  - Project slugs are lowercase, underscores, no dashes.
  - register_project() auto-normalizes input (ParallaxEdge → parallaxedge),
    logs a warning if the input required normalization, and stores the
    result in PROJECT_DOMAINS.
  - Default domains on registration: ['domain', 'market'] (decision A).
  - Collection naming: {project_slug}_{domain}, e.g. parallaxedge_domain.
  - Re-registering an existing project is idempotent (no duplicate entry).
  - Explicit domain list overrides the default.
"""
import importlib
import sys
from pathlib import Path

import pytest

SUBMODULE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUBMODULE_ROOT))


def _fresh_kb():
    """Reload knowledge_base so the module-level PROJECT_DOMAINS starts empty."""
    if "knowledge.knowledge_base" in sys.modules:
        importlib.reload(sys.modules["knowledge.knowledge_base"])
    import knowledge.knowledge_base as kb
    return kb


# ------------------------------------------------------------------------
# Slug normalization
# ------------------------------------------------------------------------

def test_normalize_project_slug_importable(clean_env):
    kb = _fresh_kb()
    assert hasattr(kb, "normalize_project_slug")


@pytest.mark.parametrize("raw,expected", [
    ("parallaxedge",       "parallaxedge"),
    ("ParallaxEdge",       "parallaxedge"),
    ("PARALLAXEDGE",       "parallaxedge"),
    ("parallax-edge",      "parallax_edge"),
    ("Parallax Edge",      "parallax_edge"),
    ("PROJ-PARALLAXEDGE",  "proj_parallaxedge"),
    ("My.Cool.Project",    "my_cool_project"),
    ("  trim-me  ",        "trim_me"),
])
def test_normalize_project_slug(clean_env, raw, expected):
    kb = _fresh_kb()
    assert kb.normalize_project_slug(raw) == expected


# ------------------------------------------------------------------------
# PROJECT_DOMAINS registry + register_project
# ------------------------------------------------------------------------

def test_project_domains_registry_starts_empty(clean_env):
    kb = _fresh_kb()
    assert isinstance(kb.PROJECT_DOMAINS, dict)
    assert kb.PROJECT_DOMAINS == {}


def test_register_project_default_domains(clean_env):
    """Decision A: default is ['domain', 'market']."""
    kb = _fresh_kb()
    slug = kb.register_project("parallaxedge")
    assert slug == "parallaxedge"
    assert kb.PROJECT_DOMAINS["parallaxedge"] == ["domain", "market"]


def test_register_project_auto_normalizes(clean_env, caplog):
    """ParallaxEdge → parallaxedge, with a logged warning."""
    kb = _fresh_kb()
    import logging
    caplog.set_level(logging.WARNING)

    slug = kb.register_project("ParallaxEdge")
    assert slug == "parallaxedge"
    assert "parallaxedge" in kb.PROJECT_DOMAINS
    # A normalization warning must have been emitted.
    assert any("normaliz" in rec.message.lower() for rec in caplog.records)


def test_register_project_no_warning_when_already_canonical(clean_env, caplog):
    kb = _fresh_kb()
    import logging
    caplog.set_level(logging.WARNING)

    kb.register_project("parallaxedge")
    assert not any("normaliz" in rec.message.lower() for rec in caplog.records)


def test_register_project_explicit_domains_override(clean_env):
    kb = _fresh_kb()
    slug = kb.register_project(
        "parallaxedge",
        domains=["domain", "market", "nascar_data", "horse_racing"],
    )
    assert kb.PROJECT_DOMAINS[slug] == [
        "domain", "market", "nascar_data", "horse_racing",
    ]


def test_register_project_idempotent(clean_env):
    """Registering twice with the same domains is a no-op, not a dup."""
    kb = _fresh_kb()
    kb.register_project("parallaxedge")
    kb.register_project("parallaxedge")
    assert len(kb.PROJECT_DOMAINS) == 1
    assert kb.PROJECT_DOMAINS["parallaxedge"] == ["domain", "market"]


def test_register_project_second_call_updates_domains(clean_env):
    """Registering again with a new list replaces the previous list."""
    kb = _fresh_kb()
    kb.register_project("parallaxedge")
    kb.register_project("parallaxedge", domains=["domain", "market", "extra"])
    assert kb.PROJECT_DOMAINS["parallaxedge"] == ["domain", "market", "extra"]


# ------------------------------------------------------------------------
# Collection naming integration
# ------------------------------------------------------------------------

def test_project_collection_name_uses_slug(clean_env):
    """
    Collections for a project follow the {slug}_{domain} idiom — same
    naming convention as team collections, just a different namespace.
    """
    kb = _fresh_kb()
    kb.register_project("parallaxedge")
    # Existing _collection_name() should work with (slug, domain) just like (team, domain)
    assert kb._collection_name("parallaxedge", "domain") == "parallaxedge_domain"
    assert kb._collection_name("parallaxedge", "market") == "parallaxedge_market"


# ------------------------------------------------------------------------
# Freshness reporting must include projects
# ------------------------------------------------------------------------

def test_freshness_report_includes_registered_projects(clean_env):
    """
    get_freshness_report() must list every registered project alongside
    teams and top-level domains.
    """
    kb = _fresh_kb()
    kb.register_project("parallaxedge")

    report = kb.get_freshness_report()
    # Report shape per project is the same as per team: {domain: {...}}
    assert "parallaxedge" in report
    assert isinstance(report["parallaxedge"], dict)
    assert set(report["parallaxedge"].keys()) == {"domain", "market"}
