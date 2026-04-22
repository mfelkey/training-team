"""
tests/test_legal_curator_migration.py

TDD — verify the legal curator was migrated from store_knowledge to
propose_knowledge as part of the HITL gate rollout.

This is a cross-cutting change: EVERY existing curator will eventually
need this migration. Legal is the Day 1 proof case. Subsequent sessions
should add analogous tests for the other six curators (dev, ds, design,
marketing, qa, strategy) as they migrate.
"""
import ast
from pathlib import Path

import pytest

SUBMODULE_ROOT = Path(__file__).resolve().parent.parent
LEGAL_CURATOR = SUBMODULE_ROOT / "agents" / "curators" / "legal" / "curator.py"


def _collect_names(path: Path) -> tuple[set[str], set[str]]:
    """
    Parse the curator and return (imported_names, called_names).
    We use AST so we're not tricked by code in comments or strings.
    """
    tree = ast.parse(path.read_text())

    imported = set()
    called = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                imported.add(alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name)
        elif isinstance(node, ast.Call):
            # Capture plain function calls: foo(...)
            if isinstance(node.func, ast.Name):
                called.add(node.func.id)
            # Capture attribute calls: mod.foo(...)
            elif isinstance(node.func, ast.Attribute):
                called.add(node.func.attr)

    return imported, called


def test_legal_curator_imports_propose_knowledge():
    imported, _ = _collect_names(LEGAL_CURATOR)
    assert "propose_knowledge" in imported, (
        "legal curator must import propose_knowledge from knowledge_base"
    )


def test_legal_curator_calls_propose_knowledge():
    _, called = _collect_names(LEGAL_CURATOR)
    assert "propose_knowledge" in called, (
        "legal curator must call propose_knowledge() on each source"
    )


def test_legal_curator_does_not_call_store_knowledge():
    """
    HITL gate invariant: curators never write directly to ChromaDB.
    The only caller of store_knowledge() is approve_candidates.py during
    the flush step.
    """
    _, called = _collect_names(LEGAL_CURATOR)
    assert "store_knowledge" not in called, (
        "legal curator must not call store_knowledge directly — "
        "that bypasses the HITL gate. Use propose_knowledge instead."
    )
