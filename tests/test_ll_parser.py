"""
tests/test_ll_parser.py

TDD — tests for the LESSONS_LEARNED.md parser.

The parser must:
  - Detect ## LL-NNN — <title> headings as entry boundaries
  - Extract id, title, date, severity, affected, body per entry
  - Handle the current single-entry file (LL-040 only)
  - Handle multi-entry files gracefully
  - Fail softly on malformed entries (skip + warn, never crash the curator)
"""
from pathlib import Path
from textwrap import dedent

import pytest


SUBMODULE_ROOT = Path(__file__).resolve().parent.parent
REAL_LL_PATH = (
    SUBMODULE_ROOT.parent.parent / "docs" / "LESSONS_LEARNED.md"
)


# ------------------------------------------------------------------------
# Fixtures — synthetic LL content for multi-entry parsing tests
# ------------------------------------------------------------------------

SYNTH_MULTI = dedent("""\
    # Synthetic — Lessons Learned

    > Pointer blurb; ignored by parser.

    ---

    ## LL-001 — UKGC affordability checks shifted mid-season

    **Date:** 2025-08-14
    **Discovered via:** legal review
    **Severity:** MEDIUM
    **Affected:** Legal team, ParallaxEdge customer flows

    ### Symptom

    UKGC updated affordability guidance; our wording had to change.

    ### Fix

    Updated copy in landing page.

    ---

    ## LL-002 — CVE-2025-XXXX in example-lib

    **Date:** 2025-12-03
    **Severity:** CRITICAL
    **Affected:** Dev, QA

    ### Symptom

    Transitive dependency vulnerable to RCE.

    ### Fix

    Pinned to 2.4.7.

    ---
""")


SYNTH_MALFORMED = dedent("""\
    # Has a weird prologue but no valid entry heading

    Lorem ipsum dolor sit amet.

    ## Not an LL heading

    just noise

    ## LL-ZZZ — not a numeric id

    should be skipped
""")


@pytest.fixture
def write_tmp_ll(tmp_path):
    """Write a given string to a temp file and return its path."""
    def _write(content: str, name: str = "LL.md") -> Path:
        p = tmp_path / name
        p.write_text(content)
        return p
    return _write


# ------------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------------

def test_parser_is_importable():
    from agents.curators.lessons_learned.parser import parse_ll_file  # noqa: F401


def test_parser_reads_real_platform_file():
    """Must parse the real docs/LESSONS_LEARNED.md (which has LL-040)."""
    from agents.curators.lessons_learned.parser import parse_ll_file

    entries = parse_ll_file(REAL_LL_PATH)
    assert len(entries) >= 1, "expected at least LL-040"
    ids = {e["ll_id"] for e in entries}
    assert "LL-040" in ids


def test_parser_extracts_metadata_from_real_ll040():
    """Validate every metadata field against the known LL-040 content."""
    from agents.curators.lessons_learned.parser import parse_ll_file

    entries = parse_ll_file(REAL_LL_PATH)
    ll040 = next(e for e in entries if e["ll_id"] == "LL-040")

    assert ll040["title"].startswith(
        "Verify runtime dispatch path before patching"
    )
    assert ll040["date"] == "2026-04-21"
    assert "HIGH" in ll040["severity"]
    # "Affected" line mentions design, legal, strategy, QA, marketing
    assert "design" in ll040["affected"].lower()
    assert "legal" in ll040["affected"].lower()
    # Full body is captured (the "real lesson" phrase is in the Prevention section)
    assert "dispatch path" in ll040["body"].lower()


def test_parser_handles_multiple_entries(write_tmp_ll):
    from agents.curators.lessons_learned.parser import parse_ll_file

    path = write_tmp_ll(SYNTH_MULTI)
    entries = parse_ll_file(path)

    assert len(entries) == 2
    ids = [e["ll_id"] for e in entries]
    assert ids == ["LL-001", "LL-002"]

    ll001 = entries[0]
    assert ll001["title"].startswith("UKGC affordability")
    assert ll001["date"] == "2025-08-14"
    assert "MEDIUM" in ll001["severity"]
    assert "legal" in ll001["affected"].lower()

    ll002 = entries[1]
    assert ll002["title"].startswith("CVE-2025")
    assert "CRITICAL" in ll002["severity"]
    assert "dev" in ll002["affected"].lower()


def test_parser_skips_malformed_entries(write_tmp_ll):
    """Non-numeric IDs and non-LL headings must not produce entries."""
    from agents.curators.lessons_learned.parser import parse_ll_file

    path = write_tmp_ll(SYNTH_MALFORMED)
    entries = parse_ll_file(path)

    # LL-ZZZ is not a valid numeric id; must be rejected.
    ids = [e["ll_id"] for e in entries]
    assert "LL-ZZZ" not in ids
    # The # heading and ## "Not an LL heading" are not LL-NNN form either.
    assert entries == []


def test_parser_missing_file_returns_empty(tmp_path):
    """Missing file must not crash the curator; return [] and move on."""
    from agents.curators.lessons_learned.parser import parse_ll_file

    missing = tmp_path / "does_not_exist.md"
    assert not missing.exists()
    assert parse_ll_file(missing) == []


def test_parser_captures_body_up_to_next_entry(write_tmp_ll):
    """An entry's body must include all ### subsections up to the next LL."""
    from agents.curators.lessons_learned.parser import parse_ll_file

    path = write_tmp_ll(SYNTH_MULTI)
    entries = parse_ll_file(path)

    # LL-001 body must contain its ### Symptom and ### Fix but NOT LL-002
    body_001 = entries[0]["body"]
    assert "### Symptom" in body_001
    assert "### Fix" in body_001
    assert "LL-002" not in body_001
    assert "CVE-2025" not in body_001
