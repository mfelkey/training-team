"""
tests/test_approve_candidates.py

TDD — tests for scripts/approve_candidates.py.

This CLI mirrors the umbrella's scripts/approve.py pattern. It reads
from CANDIDATES_DIR and flushes approved candidates into ChromaDB via
store_knowledge().

Test strategy (hybrid):
  - Unit tests: import the script's command handlers directly and
    patch store_knowledge. Fast, deterministic, no ChromaDB required.
  - Integration test: spawn approve_candidates.py as a real subprocess
    that writes to a live ChromaDB. Marked @pytest.mark.integration and
    skipped by default (run with `pytest -m integration`).
"""
import importlib
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SUBMODULE_ROOT = Path(__file__).resolve().parent.parent
APPROVE_SCRIPT = SUBMODULE_ROOT / "scripts" / "approve_candidates.py"

# Ensure scripts/ is importable so we can unit-test the handlers directly.
sys.path.insert(0, str(SUBMODULE_ROOT / "scripts"))


# ------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------

def _fresh_approve_module():
    """
    Reload approve_candidates so it picks up the current CANDIDATES_DIR
    env var (knowledge_base re-reads env on import, and approve_candidates
    imports from knowledge_base).
    """
    if "knowledge.knowledge_base" in sys.modules:
        importlib.reload(sys.modules["knowledge.knowledge_base"])
    if "approve_candidates" in sys.modules:
        return importlib.reload(sys.modules["approve_candidates"])
    import approve_candidates
    return approve_candidates


def _run_subprocess(args, env_db, env_cand):
    """Run approve_candidates.py as a real subprocess (integration only)."""
    env = os.environ.copy()
    env["KNOWLEDGE_DB_PATH"] = str(env_db)
    env["CANDIDATES_DIR"] = str(env_cand)
    env["PYTHONPATH"] = str(SUBMODULE_ROOT)
    return subprocess.run(
        [sys.executable, str(APPROVE_SCRIPT)] + args,
        capture_output=True, text=True, env=env, timeout=30,
    )


# ------------------------------------------------------------------------
# Unit tests — in-process, store_knowledge mocked
# ------------------------------------------------------------------------

def test_approve_candidates_script_exists():
    """The CLI script must be present and runnable."""
    assert APPROVE_SCRIPT.exists(), f"missing {APPROVE_SCRIPT}"


def test_list_empty(clean_env, capsys):
    """cmd_list on empty candidates dir exits 0 with a sensible message."""
    mod = _fresh_approve_module()
    rc = mod.cmd_list()
    assert rc == 0
    out = capsys.readouterr().out.lower()
    assert "no candidates" in out or "pending: 0" in out


def test_list_shows_pending(clean_env, capsys):
    """cmd_list prints pending candidates."""
    from knowledge.knowledge_base import propose_knowledge, PRIORITY_HIGH

    cand_id = propose_knowledge(
        team="legal", domain="uk_gambling_regulation",
        content="UKGC sample", source="UKGC News",
        title="UKGC sample", priority=PRIORITY_HIGH, metadata={},
    )
    mod = _fresh_approve_module()
    rc = mod.cmd_list()
    assert rc == 0
    out = capsys.readouterr().out
    assert cand_id[:12] in out
    assert "UKGC sample" in out


def test_approve_calls_store_knowledge_with_right_args(clean_env):
    """
    cmd_approve must call store_knowledge with the candidate's fields
    and update the candidate's status to 'approved'.
    """
    from knowledge.knowledge_base import propose_knowledge, PRIORITY_HIGH

    cand_id = propose_knowledge(
        team="legal", domain="uk_gambling_regulation",
        content="Approvable content", source="Test Source",
        title="Approvable", priority=PRIORITY_HIGH,
        metadata={"url": "https://example.test/x"},
    )
    mod = _fresh_approve_module()

    with patch.object(mod, "store_knowledge", return_value="fakedocid") as sk:
        rc = mod.cmd_approve(cand_id)

    assert rc == 0
    sk.assert_called_once()
    kwargs = sk.call_args.kwargs
    assert kwargs["team"] == "legal"
    assert kwargs["domain"] == "uk_gambling_regulation"
    assert kwargs["content"] == "Approvable content"
    assert kwargs["source"] == "Test Source"
    assert kwargs["title"] == "Approvable"
    assert kwargs["priority"] == "HIGH"
    assert kwargs["metadata"]["url"] == "https://example.test/x"

    data = json.loads(
        (clean_env["candidates"] / f"{cand_id}.json").read_text()
    )
    assert data["status"] == "approved"
    assert data["chromadb_doc_id"] == "fakedocid"
    assert "approved_at" in data


def test_approve_unknown_id_errors(clean_env):
    """Approving a nonexistent candidate returns nonzero, no store call."""
    mod = _fresh_approve_module()
    with patch.object(mod, "store_knowledge") as sk:
        rc = mod.cmd_approve("deadbeef" * 8)
    assert rc != 0
    sk.assert_not_called()


def test_reject_marks_rejected_no_store(clean_env):
    """cmd_reject updates status and does NOT call store_knowledge."""
    from knowledge.knowledge_base import propose_knowledge, PRIORITY_LOW

    cand_id = propose_knowledge(
        team="legal", domain="data_protection",
        content="Reject me", source="T",
        title="R", priority=PRIORITY_LOW, metadata={},
    )
    mod = _fresh_approve_module()

    with patch.object(mod, "store_knowledge") as sk:
        rc = mod.cmd_reject(cand_id, reason="not relevant")

    assert rc == 0
    sk.assert_not_called()
    data = json.loads(
        (clean_env["candidates"] / f"{cand_id}.json").read_text()
    )
    assert data["status"] == "rejected"
    assert data["rejection_reason"] == "not relevant"
    assert "rejected_at" in data


def test_approve_is_idempotent(clean_env):
    """Re-approving an approved candidate: exit 0, no second flush."""
    from knowledge.knowledge_base import propose_knowledge, PRIORITY_HIGH

    cand_id = propose_knowledge(
        team="legal", domain="uk_gambling_regulation",
        content="Idempotent", source="T",
        title="I", priority=PRIORITY_HIGH, metadata={},
    )
    mod = _fresh_approve_module()

    with patch.object(mod, "store_knowledge", return_value="doc1") as sk:
        rc1 = mod.cmd_approve(cand_id)
        rc2 = mod.cmd_approve(cand_id)

    assert rc1 == 0
    assert rc2 == 0
    assert sk.call_count == 1, "second approve must not re-flush"


def test_cannot_approve_rejected(clean_env):
    """Approving a previously-rejected candidate must fail."""
    from knowledge.knowledge_base import propose_knowledge, PRIORITY_LOW

    cand_id = propose_knowledge(
        team="legal", domain="data_protection",
        content="R", source="S", title="R",
        priority=PRIORITY_LOW, metadata={},
    )
    mod = _fresh_approve_module()

    with patch.object(mod, "store_knowledge") as sk:
        mod.cmd_reject(cand_id)
        rc = mod.cmd_approve(cand_id)

    assert rc != 0
    sk.assert_not_called()


def test_approve_all_above_high_picks_high_and_critical(clean_env):
    """
    cmd_approve_all_above HIGH approves HIGH + CRITICAL pending
    candidates, leaves LOW/MEDIUM untouched.
    """
    from knowledge.knowledge_base import (
        propose_knowledge,
        PRIORITY_LOW, PRIORITY_MEDIUM, PRIORITY_HIGH, PRIORITY_CRITICAL,
    )

    low_id = propose_knowledge(
        team="legal", domain="data_protection",
        content="L", source="S1", title="L",
        priority=PRIORITY_LOW, metadata={},
    )
    med_id = propose_knowledge(
        team="legal", domain="data_protection",
        content="M", source="S2", title="M",
        priority=PRIORITY_MEDIUM, metadata={},
    )
    high_id = propose_knowledge(
        team="legal", domain="data_protection",
        content="H", source="S3", title="H",
        priority=PRIORITY_HIGH, metadata={},
    )
    crit_id = propose_knowledge(
        team="legal", domain="data_protection",
        content="C", source="S4", title="C",
        priority=PRIORITY_CRITICAL, metadata={},
    )

    mod = _fresh_approve_module()
    with patch.object(mod, "store_knowledge", return_value="doc") as sk:
        rc = mod.cmd_approve_all_above("HIGH")

    assert rc == 0
    assert sk.call_count == 2

    def status_of(cid):
        return json.loads(
            (clean_env["candidates"] / f"{cid}.json").read_text()
        )["status"]

    assert status_of(low_id) == "pending"
    assert status_of(med_id) == "pending"
    assert status_of(high_id) == "approved"
    assert status_of(crit_id) == "approved"


def test_approve_all_above_bad_priority_errors(clean_env):
    """Invalid priority name returns nonzero."""
    mod = _fresh_approve_module()
    rc = mod.cmd_approve_all_above("BOGUS")
    assert rc != 0


# ------------------------------------------------------------------------
# Integration — real subprocess + real ChromaDB
# ------------------------------------------------------------------------

@pytest.mark.integration
def test_integration_approve_flushes_to_real_chromadb(clean_env):
    """
    End-to-end: propose → approve via subprocess → ChromaDB row present.
    Requires working ChromaDB embedder (ONNX model reachable).
    Skipped by default; run with: pytest -m integration
    """
    from knowledge.knowledge_base import propose_knowledge, PRIORITY_HIGH

    cand_id = propose_knowledge(
        team="legal", domain="uk_gambling_regulation",
        content="Integration test content", source="IntegSource",
        title="Integ", priority=PRIORITY_HIGH, metadata={},
    )
    result = _run_subprocess(
        ["--approve", cand_id], clean_env["db"], clean_env["candidates"],
    )
    assert result.returncode == 0, \
        f"stdout: {result.stdout}\nstderr: {result.stderr}"

    data = json.loads(
        (clean_env["candidates"] / f"{cand_id}.json").read_text()
    )
    assert data["status"] == "approved"

    import chromadb
    client = chromadb.PersistentClient(path=str(clean_env["db"]))
    coll = client.get_collection("legal_uk_gambling_regulation")
    assert coll.count() == 1
