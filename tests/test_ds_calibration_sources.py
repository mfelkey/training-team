"""
tests/test_ds_calibration_sources.py

Phase 4 follow-up (2026-04-23) — DS curator must carry calibration
and drift-monitoring sources to support LL-045's remediation checklist
items (distribution sanity checks, delta anomaly breakers, holdout
reality-checks).

The three sources added:
  - scikit-learn calibration docs (fundamentals of probability calibration)
  - NannyML (production ML monitoring: drift + calibration degradation)
  - Evidently AI (data/model drift monitoring, complement to NannyML)

All three fit the existing ml_techniques domain tag (which DS already
uses for sklearn releases). This test asserts they are present, well-
formed, and correctly tagged. Also asserts schema invariants for the
whole SOURCES list so new additions can't silently skip fields.
"""
import importlib
import sys
from pathlib import Path

import pytest

SUBMODULE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUBMODULE_ROOT))

from agents.curators.ds import curator  # noqa: E402


REQUIRED_URLS = [
    "https://scikit-learn.org/stable/modules/calibration.html",
    "https://www.nannyml.com/",
    "https://www.evidentlyai.com/",
]

REQUIRED_FIELDS = {"name", "url", "domain", "priority"}


def _find_entry(url: str) -> dict:
    for entry in curator.SOURCES:
        if entry.get("url") == url:
            return entry
    raise AssertionError(f"URL not found in DS SOURCES: {url}")


@pytest.mark.parametrize("url", REQUIRED_URLS)
def test_calibration_url_present(url: str) -> None:
    """Each of the 3 calibration/drift URLs must be in DS SOURCES."""
    entry = _find_entry(url)
    assert entry is not None


@pytest.mark.parametrize("url", REQUIRED_URLS)
def test_calibration_entry_tagged_ml_techniques(url: str) -> None:
    """Each of the 3 URLs must be tagged under the ml_techniques domain."""
    entry = _find_entry(url)
    assert entry["domain"] == "ml_techniques", (
        f"{url} domain is {entry['domain']!r}; expected 'ml_techniques'"
    )


@pytest.mark.parametrize("url", REQUIRED_URLS)
def test_calibration_entry_has_all_required_fields(url: str) -> None:
    """Each of the 3 URLs must have a full {name, url, domain, priority}."""
    entry = _find_entry(url)
    missing = REQUIRED_FIELDS - set(entry.keys())
    assert not missing, f"{url} missing fields: {missing}"


def test_all_sources_have_required_fields() -> None:
    """Schema invariant for the whole DS SOURCES list — catches drift
    from future additions that skip fields."""
    for i, entry in enumerate(curator.SOURCES):
        missing = REQUIRED_FIELDS - set(entry.keys())
        assert not missing, (
            f"DS SOURCES entry #{i} ({entry.get('name', '?')}) "
            f"missing fields: {missing}"
        )


def test_all_sources_use_known_domains() -> None:
    """Every domain referenced in DS SOURCES must exist in
    TEAM_DOMAINS['ds'] in knowledge_base.py — catches copy/paste drift
    that would silently tag content under a typo."""
    from knowledge.knowledge_base import TEAM_DOMAINS
    valid = set(TEAM_DOMAINS["ds"])
    for entry in curator.SOURCES:
        domain = entry["domain"]
        assert domain in valid, (
            f"DS SOURCES entry {entry['name']!r} uses unknown domain "
            f"{domain!r}. Valid: {sorted(valid)}"
        )
