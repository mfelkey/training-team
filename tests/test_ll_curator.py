"""
tests/test_ll_curator.py

TDD — integration tests for the LL curator.

The curator glues parse_ll_file + score_relevance + propose_knowledge.
Invariants:
  - One propose_knowledge call per parsed entry
  - team="__all__" stored at the top-level lessons_learned collection
    (NOT one of the per-team collections — this is a top-level domain)
  - source_type="platform" tag on every proposed candidate
  - relevant_teams metadata is a JSON-encoded list
  - AST: curator imports propose_knowledge, never store_knowledge
"""
import ast
import json
import sys
from pathlib import Path

import pytest

SUBMODULE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUBMODULE_ROOT))

CURATOR_PATH = (
    SUBMODULE_ROOT / "agents" / "curators" / "lessons_learned" / "curator.py"
)
REAL_LL_PATH = SUBMODULE_ROOT.parent.parent / "docs" / "LESSONS_LEARNED.md"


def _collect_ast(path: Path):
    tree = ast.parse(path.read_text())
    imported, called = set(), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                imported.add(alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                called.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                called.add(node.func.attr)
    return imported, called


# ------------------------------------------------------------------------
# AST invariants (mirror the legal curator migration pattern)
# ------------------------------------------------------------------------

def test_curator_module_exists():
    assert CURATOR_PATH.exists(), f"missing {CURATOR_PATH}"


def test_curator_imports_propose_knowledge():
    imported, _ = _collect_ast(CURATOR_PATH)
    assert "propose_knowledge" in imported


def test_curator_calls_propose_knowledge():
    _, called = _collect_ast(CURATOR_PATH)
    assert "propose_knowledge" in called


def test_curator_does_not_call_store_knowledge():
    _, called = _collect_ast(CURATOR_PATH)
    assert "store_knowledge" not in called, (
        "LL curator must not bypass the HITL gate"
    )


# ------------------------------------------------------------------------
# Integration — run the curator against the real LL-040 file
# ------------------------------------------------------------------------

def test_curator_proposes_one_candidate_per_entry(clean_env, monkeypatch):
    """
    run(ll_path=...) should call propose_knowledge exactly once per parsed
    entry. With the current platform file, that's one call for LL-040.
    """
    import importlib
    if "knowledge.knowledge_base" in sys.modules:
        importlib.reload(sys.modules["knowledge.knowledge_base"])

    from agents.curators.lessons_learned import curator
    importlib.reload(curator)

    # Spy on propose_knowledge
    calls = []
    real_propose = curator.propose_knowledge

    def spy(**kwargs):
        calls.append(kwargs)
        return real_propose(**kwargs)

    monkeypatch.setattr(curator, "propose_knowledge", spy)

    n = curator.run(ll_path=REAL_LL_PATH, source_type="platform")
    # The real file accumulates LLs over time (LL-040, LL-041, ...).
    # Assert at least one was proposed and LL-040 is among the calls.
    assert n >= 1, f"expected at least 1 proposed candidate, got {n}"
    assert len(calls) == n
    ll_ids = [c["metadata"]["ll_id"] for c in calls]
    assert "LL-040" in ll_ids


def test_curator_candidate_has_expected_shape(clean_env):
    """
    After curator.run(), the candidate file on disk must have:
      - team == 'lessons_learned' (top-level domain convention)
      - source_type == 'platform'
      - relevant_teams metadata is a list containing expected teams
      - ll_id metadata present
    """
    import importlib
    if "knowledge.knowledge_base" in sys.modules:
        importlib.reload(sys.modules["knowledge.knowledge_base"])

    from agents.curators.lessons_learned import curator
    importlib.reload(curator)

    n = curator.run(ll_path=REAL_LL_PATH, source_type="platform")
    assert n >= 1

    # Find the LL-040 candidate specifically (the file may contain other LLs).
    files = list(clean_env["candidates"].glob("*.json"))
    assert len(files) == n
    ll040_data = None
    for f in files:
        d = json.loads(f.read_text())
        if d.get("metadata", {}).get("ll_id") == "LL-040":
            ll040_data = d
            break
    assert ll040_data is not None, "no LL-040 candidate found on disk"
    data = ll040_data

    # The top-level domain sentinel — not a {team}_{domain} collection.
    assert data["team"] == "lessons_learned"
    assert data["domain"] == "platform"
    assert data["metadata"]["source_type"] == "platform"
    assert data["metadata"]["ll_id"] == "LL-040"
    # relevant_teams is JSON-encoded (ChromaDB rejects list-valued metadata).
    relevant = json.loads(data["metadata"]["relevant_teams"])
    assert isinstance(relevant, list)
    # LL-040 is universal — all 11 teams
    assert "legal" in relevant
    assert "dev" in relevant
    assert "ds" in relevant


def test_curator_missing_file_is_nonfatal(clean_env, tmp_path):
    """Curator.run() on a missing file returns 0 and does not raise."""
    import importlib
    if "knowledge.knowledge_base" in sys.modules:
        importlib.reload(sys.modules["knowledge.knowledge_base"])

    from agents.curators.lessons_learned import curator
    importlib.reload(curator)

    missing = tmp_path / "nope.md"
    n = curator.run(ll_path=missing, source_type="project")
    assert n == 0
