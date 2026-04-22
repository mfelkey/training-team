"""
tests/test_ll_mode.py

TDD — training_flow.py must support an 'll' mode that invokes the
lessons_learned curator.

Per Day 6 design decision: extend the existing flow rather than create
a separate flows/training_ll_ingest.py. This keeps one entry point for
the training-team and matches the existing --mode {full,team,on_demand,
status,alerts} idiom.

Contract:
  - 'll' is a valid --mode choice (argparse accepts it)
  - Running with --mode ll invokes agents.curators.lessons_learned.curator.run
  - Default ll-path points at the umbrella's docs/LESSONS_LEARNED.md
  - --ll-path overrides the default
  - --source-type {platform,project} is forwarded
  - Missing file is non-fatal (exit 0, message printed)
"""
import subprocess
import sys
from pathlib import Path

import pytest

SUBMODULE_ROOT = Path(__file__).resolve().parent.parent
FLOW_SCRIPT = SUBMODULE_ROOT / "flows" / "training_flow.py"
REAL_LL_PATH = SUBMODULE_ROOT.parent.parent / "docs" / "LESSONS_LEARNED.md"


def _run_flow(args, env_db, env_cand):
    """Run training_flow.py as a real subprocess with isolated env."""
    import os
    env = os.environ.copy()
    env["KNOWLEDGE_DB_PATH"] = str(env_db)
    env["CANDIDATES_DIR"] = str(env_cand)
    env["PYTHONPATH"] = str(SUBMODULE_ROOT)
    return subprocess.run(
        [sys.executable, str(FLOW_SCRIPT)] + args,
        capture_output=True, text=True, env=env, timeout=30,
        cwd=str(SUBMODULE_ROOT),
    )


def test_flow_accepts_ll_mode(clean_env, tmp_path):
    """--mode ll must not error out on argparse validation."""
    # Use a temp empty file so we don't depend on the real docs/
    empty_ll = tmp_path / "LESSONS_LEARNED.md"
    empty_ll.write_text("# Empty\n")

    result = _run_flow(
        ["--mode", "ll", "--ll-path", str(empty_ll)],
        clean_env["db"], clean_env["candidates"],
    )
    assert result.returncode == 0, (
        f"argparse should accept 'll' mode.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_ll_mode_processes_real_platform_file(clean_env):
    """--mode ll on the real umbrella LL file proposes LL-040."""
    result = _run_flow(
        ["--mode", "ll", "--ll-path", str(REAL_LL_PATH),
         "--source-type", "platform"],
        clean_env["db"], clean_env["candidates"],
    )
    assert result.returncode == 0, (
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    # At least one candidate was written (LL-040)
    files = list(clean_env["candidates"].glob("*.json"))
    assert len(files) >= 1


def test_ll_mode_missing_file_is_nonfatal(clean_env, tmp_path):
    """Missing LL file returns 0, no crash."""
    missing = tmp_path / "nope.md"
    result = _run_flow(
        ["--mode", "ll", "--ll-path", str(missing)],
        clean_env["db"], clean_env["candidates"],
    )
    assert result.returncode == 0
    assert list(clean_env["candidates"].glob("*.json")) == []


def test_ll_mode_source_type_project(clean_env, tmp_path):
    """--source-type project flows through to the curator metadata."""
    ll = tmp_path / "LESSONS_LEARNED.md"
    ll.write_text("""# Test

## LL-999 — Test entry

**Date:** 2026-04-22
**Severity:** MEDIUM
**Affected:** test

### Symptom
dummy
""")
    result = _run_flow(
        ["--mode", "ll", "--ll-path", str(ll),
         "--source-type", "project"],
        clean_env["db"], clean_env["candidates"],
    )
    assert result.returncode == 0, (
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )

    import json
    files = list(clean_env["candidates"].glob("*.json"))
    assert len(files) == 1
    data = json.loads(files[0].read_text())
    assert data["domain"] == "project"
    assert data["metadata"]["source_type"] == "project"
