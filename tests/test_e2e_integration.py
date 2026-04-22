"""
tests/test_e2e_integration.py

End-to-end integration tests for the full Phase 2 round-trip:

    curator proposes candidate
        -> approve_candidates.py --approve flushes to ChromaDB
        -> rag_inject.get_latest_context() retrieves the content

Marked @pytest.mark.integration and deselected by default (requires a
working ChromaDB embedder). Run with:

    pytest -m integration

These tests validate that every Phase 2 component (Days 1-6) wires
together correctly. A failure here indicates a regression in the
round-trip even if unit tests pass.
"""
import importlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SUBMODULE_ROOT = Path(__file__).resolve().parent.parent
APPROVE_SCRIPT = SUBMODULE_ROOT / "scripts" / "approve_candidates.py"
FLOW_SCRIPT = SUBMODULE_ROOT / "flows" / "training_flow.py"
REAL_LL_PATH = SUBMODULE_ROOT.parent.parent / "docs" / "LESSONS_LEARNED.md"

sys.path.insert(0, str(SUBMODULE_ROOT))


def _fresh_kb():
    if "knowledge.knowledge_base" in sys.modules:
        importlib.reload(sys.modules["knowledge.knowledge_base"])
    import knowledge.knowledge_base as kb
    return kb


def _run_approve(args, env_db, env_cand):
    env = os.environ.copy()
    env["KNOWLEDGE_DB_PATH"] = str(env_db)
    env["CANDIDATES_DIR"] = str(env_cand)
    env["PYTHONPATH"] = str(SUBMODULE_ROOT)
    return subprocess.run(
        [sys.executable, str(APPROVE_SCRIPT)] + args,
        capture_output=True, text=True, env=env, timeout=60,
    )


def _run_flow(args, env_db, env_cand):
    env = os.environ.copy()
    env["KNOWLEDGE_DB_PATH"] = str(env_db)
    env["CANDIDATES_DIR"] = str(env_cand)
    env["PYTHONPATH"] = str(SUBMODULE_ROOT)
    return subprocess.run(
        [sys.executable, str(FLOW_SCRIPT)] + args,
        capture_output=True, text=True, env=env, timeout=60,
        cwd=str(SUBMODULE_ROOT),
    )


# ------------------------------------------------------------------------
# Round-trip: propose -> approve -> RAG
# ------------------------------------------------------------------------

@pytest.mark.integration
def test_e2e_propose_approve_rag_roundtrip(clean_env):
    """
    Full round-trip with a synthesized candidate:
      1. propose_knowledge writes a candidate
      2. approve_candidates --approve flushes to ChromaDB
      3. get_latest_context retrieves the content
    """
    kb = _fresh_kb()
    cand_id = kb.propose_knowledge(
        team="legal",
        domain="uk_gambling_regulation",
        content=(
            "The UKGC issued new guidance on affordability checks requiring "
            "operators to flag customers depositing over £125 per month "
            "without income verification. Effective immediately."
        ),
        source="UK Gambling Commission News",
        title="UKGC affordability £125 threshold",
        priority=kb.PRIORITY_HIGH,
        metadata={"url": "https://example.test/ukgc-125"},
    )

    result = _run_approve(
        ["--approve", cand_id],
        clean_env["db"], clean_env["candidates"],
    )
    assert result.returncode == 0, (
        f"approve failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )

    # Candidate is now approved on disk
    data = json.loads(
        (clean_env["candidates"] / f"{cand_id}.json").read_text()
    )
    assert data["status"] == "approved"

    # Re-import rag_inject so it sees the fresh DB_PATH
    if "knowledge.rag_inject" in sys.modules:
        importlib.reload(sys.modules["knowledge.rag_inject"])
    import knowledge.rag_inject as rag

    latest = rag.get_latest_context(
        team="legal",
        query="affordability checks UKGC",
        domains=["uk_gambling_regulation"],
    )
    assert latest, "RAG returned empty context"
    assert "affordability" in latest.lower() or "£125" in latest
    assert "UKGC" in latest or "Gambling Commission" in latest


# ------------------------------------------------------------------------
# LL ingest round-trip
# ------------------------------------------------------------------------

@pytest.mark.integration
def test_e2e_ll_ingest_approve_rag_roundtrip(clean_env):
    """
    LL-specific round-trip:
      1. flow --mode ll parses docs/LESSONS_LEARNED.md -> candidates
      2. approve-all-above HIGH flushes everything HIGH+
      3. get_latest_context retrieves lessons from the top-level
         lessons_learned collection
    """
    # Step 1: parse real LL file via the flow
    result = _run_flow(
        ["--mode", "ll", "--ll-path", str(REAL_LL_PATH),
         "--source-type", "platform"],
        clean_env["db"], clean_env["candidates"],
    )
    assert result.returncode == 0, (
        f"flow ll failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )

    candidates = list(clean_env["candidates"].glob("*.json"))
    assert len(candidates) >= 1, "no LL candidates proposed"

    # Step 2: bulk-approve anything HIGH+ (LL-040 is HIGH, LL-041 is MEDIUM)
    result = _run_approve(
        ["--approve-all-above", "MEDIUM"],
        clean_env["db"], clean_env["candidates"],
    )
    assert result.returncode == 0, (
        f"approve-all-above failed:\nstdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )

    # Step 3: RAG should find the lesson in the top-level collection
    if "knowledge.rag_inject" in sys.modules:
        importlib.reload(sys.modules["knowledge.rag_inject"])
    import knowledge.rag_inject as rag

    latest = rag.get_latest_context(
        team="lessons_learned",
        query="submodule dispatch runtime",
        domains=["platform"],
    )
    assert latest, "RAG returned empty context for LL query"
    # Should include LL-040's content (dispatch/submodule keywords)
    assert "dispatch" in latest.lower() or "submodule" in latest.lower()


# ------------------------------------------------------------------------
# Freshness report sees all collections
# ------------------------------------------------------------------------

@pytest.mark.integration
def test_e2e_freshness_report_sees_populated_collections(clean_env):
    """
    After approving across team + top-level + project collections,
    get_freshness_report must return non-zero counts for each.
    """
    kb = _fresh_kb()

    # Register a project and approve one candidate in each of three namespaces
    kb.register_project("parallaxedge")

    scenarios = [
        # (team, domain)
        ("legal", "uk_gambling_regulation"),        # team
        ("lessons_learned", "platform"),             # top-level
        ("parallaxedge", "domain"),                  # project
    ]

    for team, domain in scenarios:
        cand_id = kb.propose_knowledge(
            team=team, domain=domain,
            content=f"Populated test content for {team}/{domain}",
            source=f"{team} test source",
            title=f"{team}/{domain} populated",
            priority=kb.PRIORITY_HIGH,
            metadata={},
        )
        rc = _run_approve(
            ["--approve", cand_id],
            clean_env["db"], clean_env["candidates"],
        )
        assert rc.returncode == 0

    # Reload knowledge_base with the same project registration preserved
    # in the test process (we didn't cross a subprocess boundary here)
    report = kb.get_freshness_report()

    # Team
    assert report["legal"]["uk_gambling_regulation"]["count"] >= 1

    # Top-level
    assert report["lessons_learned"]["platform"]["count"] >= 1

    # Project
    assert "parallaxedge" in report
    assert report["parallaxedge"]["domain"]["count"] >= 1
