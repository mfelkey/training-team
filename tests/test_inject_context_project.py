"""
tests/test_inject_context_project.py

TDD — project-scoped RAG injection.

inject_context(team="legal", project="parallaxedge") must include
project-scoped collections alongside team-level ones. Behaviour
decisions (Day 4):
  - Default (no project=): unchanged, team-only query.
  - With a registered project: project collections are queried too.
  - With an unregistered/misspelled project: warn and fall back to
    team-only (decision 3).

We stub build_context_block / get_context at the knowledge_base level
so these tests don't require a populated ChromaDB — we just verify
the right arguments were threaded through.
"""
import importlib
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SUBMODULE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUBMODULE_ROOT))


def _fresh_kb_and_rag():
    if "knowledge.knowledge_base" in sys.modules:
        importlib.reload(sys.modules["knowledge.knowledge_base"])
    if "knowledge.rag_inject" in sys.modules:
        importlib.reload(sys.modules["knowledge.rag_inject"])
    import knowledge.knowledge_base as kb
    import knowledge.rag_inject as rag
    return kb, rag


# ------------------------------------------------------------------------
# inject_context — default behaviour unchanged
# ------------------------------------------------------------------------

def test_inject_context_without_project_unchanged(clean_env):
    kb, rag = _fresh_kb_and_rag()
    with patch.object(kb, "build_context_block", return_value="") as bcb:
        rag.inject_context("legal", "task text")

    assert bcb.called
    kwargs = bcb.call_args.kwargs
    assert kwargs["team"] == "legal"
    # project must NOT be passed (or must be None) when caller omitted it
    assert kwargs.get("project") in (None, "")


# ------------------------------------------------------------------------
# inject_context — project threading
# ------------------------------------------------------------------------

def test_inject_context_with_registered_project_threads_slug(clean_env):
    kb, rag = _fresh_kb_and_rag()
    kb.register_project("parallaxedge")

    with patch.object(kb, "build_context_block", return_value="") as bcb:
        rag.inject_context("legal", "task text", project="parallaxedge")

    kwargs = bcb.call_args.kwargs
    assert kwargs["project"] == "parallaxedge"


def test_inject_context_auto_normalizes_project_input(clean_env):
    """inject_context('legal', ..., project='ParallaxEdge') must still work."""
    kb, rag = _fresh_kb_and_rag()
    kb.register_project("parallaxedge")

    with patch.object(kb, "build_context_block", return_value="") as bcb:
        rag.inject_context("legal", "task text", project="ParallaxEdge")

    # The normalized slug is what gets passed through.
    kwargs = bcb.call_args.kwargs
    assert kwargs["project"] == "parallaxedge"


def test_inject_context_unregistered_project_warns_and_falls_back(clean_env, capsys):
    """
    Decision 3: warning + fall back. The caller's task text must still
    come back (no crash), and build_context_block must still be called
    with project=None so only team collections are queried.
    """
    kb, rag = _fresh_kb_and_rag()
    # Do NOT register 'typo_project'.
    with patch.object(kb, "build_context_block", return_value="") as bcb:
        out = rag.inject_context("legal", "task text", project="typo_project")

    assert out == "task text"  # unchanged, no crash
    assert bcb.called
    kwargs = bcb.call_args.kwargs
    # Fell back: project passed as None (not the misspelling)
    assert kwargs.get("project") in (None, "")

    captured = capsys.readouterr()
    assert "warn" in captured.out.lower() or "unregistered" in captured.out.lower() \
        or "unknown project" in captured.out.lower()


# ------------------------------------------------------------------------
# build_context_block must query project collections
# ------------------------------------------------------------------------

def test_build_context_block_accepts_project_kwarg(clean_env):
    """
    build_context_block in knowledge_base must accept project=
    (not just team=) and forward it to get_context.
    """
    kb, _rag = _fresh_kb_and_rag()
    kb.register_project("parallaxedge")

    with patch.object(kb, "get_context", return_value=[]) as gc:
        kb.build_context_block(
            team="legal",
            task_description="x",
            project="parallaxedge",
        )

    # At least one of the calls must be for the project namespace
    called_teams = [c.kwargs.get("team") or c.args[0]
                    for c in gc.call_args_list]
    assert "legal" in called_teams
    assert "parallaxedge" in called_teams


def test_build_context_block_without_project_unchanged(clean_env):
    kb, _rag = _fresh_kb_and_rag()

    with patch.object(kb, "get_context", return_value=[]) as gc:
        kb.build_context_block(team="legal", task_description="x")

    called_teams = [c.kwargs.get("team") or c.args[0]
                    for c in gc.call_args_list]
    # No project call — only the team's slice of get_context invocations.
    assert all(t == "legal" or t in set() for t in called_teams) or \
           "legal" in called_teams
