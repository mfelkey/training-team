"""
tests/test_all_curator_migrations.py

TDD — AST invariant tests verifying that every production curator
routes through the HITL gate (propose_knowledge), never bypassing it
with store_knowledge.

Pattern mirrors test_legal_curator_migration.py. Consolidated into
one parameterised file so future additions (finance/hr/video/sme in
Day 5) are a one-line change.

Exclusion: the lessons_learned curator is structurally different
(takes a file path, not a SOURCES list) but also calls
propose_knowledge — its invariants live in test_ll_curator.py.
"""
import ast
from pathlib import Path

import pytest


SUBMODULE_ROOT = Path(__file__).resolve().parent.parent
CURATORS_DIR = SUBMODULE_ROOT / "agents" / "curators"

# All source-fetching curators that must route through propose_knowledge.
# Order matches TEAM_DOMAINS in knowledge_base.py for readability.
SOURCE_FETCH_CURATORS = [
    "legal",
    "ds",
    "dev",
    "marketing",
    "strategy",
    "design",
    "qa",
]


def _collect_names(path: Path) -> tuple[set[str], set[str]]:
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


@pytest.mark.parametrize("team", SOURCE_FETCH_CURATORS)
def test_curator_imports_propose_knowledge(team):
    path = CURATORS_DIR / team / "curator.py"
    assert path.exists(), f"missing curator: {path}"
    imported, _ = _collect_names(path)
    assert "propose_knowledge" in imported, (
        f"{team} curator must import propose_knowledge"
    )


@pytest.mark.parametrize("team", SOURCE_FETCH_CURATORS)
def test_curator_calls_propose_knowledge(team):
    path = CURATORS_DIR / team / "curator.py"
    _, called = _collect_names(path)
    assert "propose_knowledge" in called, (
        f"{team} curator must call propose_knowledge()"
    )


@pytest.mark.parametrize("team", SOURCE_FETCH_CURATORS)
def test_curator_does_not_call_store_knowledge(team):
    """
    HITL invariant: curators never write directly to ChromaDB.
    store_knowledge is only called by approve_candidates.py during
    the flush step.
    """
    path = CURATORS_DIR / team / "curator.py"
    _, called = _collect_names(path)
    assert "store_knowledge" not in called, (
        f"{team} curator must not call store_knowledge directly — "
        "that bypasses the HITL gate. Use propose_knowledge instead."
    )
