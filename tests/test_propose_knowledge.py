"""
tests/test_propose_knowledge.py

TDD — failing tests for propose_knowledge(), the HITL-gated alternative
to store_knowledge(). Instead of writing directly to ChromaDB, it should
write a candidate JSON to knowledge/candidates/<candidate_id>.json with
status=pending. The candidate is later promoted to ChromaDB by the
approve_candidates.py CLI.

Schema contract (per Phase 2 kickoff doc, Decision 4):
    candidate_id   — sha256 hash of (source + content[:200])
    proposed_at    — ISO timestamp
    team           — e.g. "legal"
    domain         — e.g. "uk_gambling_regulation"
    source         — human-readable source name
    title          — short title of the item
    content        — full content text
    priority       — LOW | MEDIUM | HIGH | CRITICAL
    metadata       — dict of extras (url, fetched_at, etc.)
    status         — "pending" | "approved" | "rejected"
"""
import json
import os
from pathlib import Path

import pytest


def test_propose_knowledge_is_importable(clean_env):
    """propose_knowledge must be a public symbol in knowledge_base."""
    from knowledge.knowledge_base import propose_knowledge  # noqa: F401


def test_propose_knowledge_writes_candidate_file(clean_env):
    """A single call should produce exactly one JSON file in candidates/."""
    from knowledge.knowledge_base import propose_knowledge, PRIORITY_HIGH

    cand_id = propose_knowledge(
        team="legal",
        domain="uk_gambling_regulation",
        content="UKGC published new guidance on affordability checks.",
        source="UK Gambling Commission News",
        title="UKGC affordability guidance 2026-04-21",
        priority=PRIORITY_HIGH,
        metadata={"url": "https://example.test/ukgc"},
    )

    assert cand_id, "propose_knowledge should return a non-empty candidate_id"
    files = list(clean_env["candidates"].glob("*.json"))
    assert len(files) == 1, f"expected 1 candidate file, got {len(files)}"


def test_propose_knowledge_candidate_schema(clean_env):
    """Candidate file must contain every required schema field."""
    from knowledge.knowledge_base import propose_knowledge, PRIORITY_CRITICAL

    cand_id = propose_knowledge(
        team="dev",
        domain="security_vulnerabilities",
        content="CVE-2026-XXXX critical RCE in example-lib",
        source="NVD Feed",
        title="CVE-2026-XXXX",
        priority=PRIORITY_CRITICAL,
        metadata={"cve_id": "CVE-2026-XXXX"},
    )

    files = list(clean_env["candidates"].glob("*.json"))
    with open(files[0]) as f:
        data = json.load(f)

    required = {
        "candidate_id", "proposed_at", "team", "domain",
        "source", "title", "content", "priority", "metadata", "status",
    }
    missing = required - set(data.keys())
    assert not missing, f"missing required fields: {missing}"

    assert data["candidate_id"] == cand_id
    assert data["team"] == "dev"
    assert data["domain"] == "security_vulnerabilities"
    assert data["priority"] == "CRITICAL"
    assert data["status"] == "pending"
    assert data["metadata"]["cve_id"] == "CVE-2026-XXXX"


def test_propose_knowledge_stable_id(clean_env):
    """Same (source, content[:200]) should hash to the same candidate_id."""
    from knowledge.knowledge_base import propose_knowledge, PRIORITY_MEDIUM

    args = dict(
        team="legal",
        domain="data_protection",
        content="ICO issues new fine for X",
        source="ICO News",
        title="ICO fine",
        priority=PRIORITY_MEDIUM,
        metadata={},
    )
    cand_a = propose_knowledge(**args)
    cand_b = propose_knowledge(**args)
    assert cand_a == cand_b, "identical inputs must yield identical candidate_id"


def test_propose_knowledge_different_sources_different_ids(clean_env):
    """Distinct inputs must yield distinct ids."""
    from knowledge.knowledge_base import propose_knowledge, PRIORITY_MEDIUM

    a = propose_knowledge(
        team="legal", domain="data_protection",
        content="Content A", source="Source One",
        title="A", priority=PRIORITY_MEDIUM, metadata={},
    )
    b = propose_knowledge(
        team="legal", domain="data_protection",
        content="Content B", source="Source Two",
        title="B", priority=PRIORITY_MEDIUM, metadata={},
    )
    assert a != b


def test_propose_knowledge_iso_timestamp(clean_env):
    """proposed_at must be parseable ISO-8601."""
    from datetime import datetime
    from knowledge.knowledge_base import propose_knowledge, PRIORITY_LOW

    propose_knowledge(
        team="ds", domain="xg_modeling",
        content="Test content", source="ArXiv",
        title="T", priority=PRIORITY_LOW, metadata={},
    )
    files = list(clean_env["candidates"].glob("*.json"))
    data = json.loads(files[0].read_text())
    # Will raise if not parseable
    datetime.fromisoformat(data["proposed_at"])


def test_propose_knowledge_does_not_touch_chromadb(clean_env):
    """
    The whole point of the HITL gate: propose must NOT write to ChromaDB.
    The db directory should stay empty after proposing.
    """
    from knowledge.knowledge_base import propose_knowledge, PRIORITY_HIGH

    propose_knowledge(
        team="legal", domain="uk_gambling_regulation",
        content="Should not reach chromadb", source="Test",
        title="T", priority=PRIORITY_HIGH, metadata={},
    )

    # ChromaDB creates its sqlite files on first use. If propose wrote
    # to the db, we'd see chromadb artifacts. Candidates dir should have
    # exactly one file; db dir should have nothing chromadb-shaped.
    db_contents = list(clean_env["db"].rglob("*"))
    # Filter out dirs created by the fixture itself
    db_files = [p for p in db_contents if p.is_file()]
    assert not db_files, f"db was written to: {db_files}"


def test_propose_knowledge_defaults_priority_medium(clean_env):
    """Omitting priority should default to MEDIUM, matching store_knowledge."""
    from knowledge.knowledge_base import propose_knowledge

    propose_knowledge(
        team="legal", domain="data_protection",
        content="Default priority test", source="Test",
        title="T",
    )
    files = list(clean_env["candidates"].glob("*.json"))
    data = json.loads(files[0].read_text())
    assert data["priority"] == "MEDIUM"
