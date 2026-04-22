"""
tests/conftest.py

Shared pytest fixtures for the training-team test suite.

Key isolation guarantees:
  - Each test gets an isolated ChromaDB at a tmp path (via KNOWLEDGE_DB_PATH env var)
  - Each test gets an isolated candidates/ directory
  - Neither the real knowledge/db nor the real knowledge/candidates is ever touched
"""
import os
import sys
import shutil
from pathlib import Path

import pytest

# Put the submodule root on sys.path so `knowledge.*` imports work from tests/.
SUBMODULE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUBMODULE_ROOT))


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    """
    Point KNOWLEDGE_DB_PATH at a per-test tmp directory before any chromadb
    client is created. Reload knowledge_base so its module-level DB_PATH
    picks up the new env var.
    """
    db_dir = tmp_path / "db"
    db_dir.mkdir()
    monkeypatch.setenv("KNOWLEDGE_DB_PATH", str(db_dir))

    # Force re-read of DB_PATH in knowledge_base
    import importlib
    if "knowledge.knowledge_base" in sys.modules:
        importlib.reload(sys.modules["knowledge.knowledge_base"])

    yield db_dir


@pytest.fixture
def isolated_candidates(tmp_path, monkeypatch):
    """
    Point CANDIDATES_DIR at a per-test tmp directory. The knowledge_base
    module reads this env var when writing candidate files.
    """
    cand_dir = tmp_path / "candidates"
    cand_dir.mkdir()
    monkeypatch.setenv("CANDIDATES_DIR", str(cand_dir))

    import importlib
    if "knowledge.knowledge_base" in sys.modules:
        importlib.reload(sys.modules["knowledge.knowledge_base"])

    yield cand_dir


@pytest.fixture
def clean_env(isolated_db, isolated_candidates):
    """Convenience fixture: both DB and candidates isolated."""
    yield {"db": isolated_db, "candidates": isolated_candidates}
