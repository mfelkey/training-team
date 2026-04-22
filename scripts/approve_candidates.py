#!/usr/bin/env python3
"""
scripts/approve_candidates.py

Training-Team — HITL approval CLI for knowledge candidates.

Mirrors the umbrella's scripts/approve.py idiom. Reads candidates
written by knowledge.knowledge_base.propose_knowledge(), and either
flushes them to ChromaDB (via store_knowledge) on approval, or marks
them rejected.

Usage:
    python3.11 scripts/approve_candidates.py --list
    python3.11 scripts/approve_candidates.py --approve <candidate_id>
    python3.11 scripts/approve_candidates.py --reject  <candidate_id>
    python3.11 scripts/approve_candidates.py --approve-all-above <PRIORITY>
    python3.11 scripts/approve_candidates.py --watch   (tail for new pending)

Environment:
    CANDIDATES_DIR       override candidates dir (defaults to
                         ~/projects/protean-pursuits/teams/training-team/knowledge/candidates)
    KNOWLEDGE_DB_PATH    override ChromaDB path (same default tree)
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Put submodule root on sys.path so `knowledge.*` imports resolve.
SUBMODULE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUBMODULE_ROOT))

from knowledge.knowledge_base import (  # noqa: E402
    store_knowledge,
    CANDIDATES_DIR,
    PRIORITY_LOW, PRIORITY_MEDIUM, PRIORITY_HIGH, PRIORITY_CRITICAL,
)

PRIORITY_ORDER = [PRIORITY_LOW, PRIORITY_MEDIUM, PRIORITY_HIGH, PRIORITY_CRITICAL]


def _candidates_path() -> Path:
    """Always read fresh from env; tests override via monkeypatch."""
    return Path(os.getenv("CANDIDATES_DIR", CANDIDATES_DIR))


def _load(cand_id: str) -> tuple[Path, dict]:
    path = _candidates_path() / f"{cand_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"no candidate with id {cand_id}")
    with open(path) as f:
        return path, json.load(f)


def _save(path: Path, data: dict) -> None:
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def _all_candidates() -> list[dict]:
    d = _candidates_path()
    if not d.exists():
        return []
    out = []
    for p in sorted(d.glob("*.json")):
        try:
            with open(p) as f:
                data = json.load(f)
            data["_path"] = str(p)
            out.append(data)
        except Exception:
            continue
    return out


def cmd_list() -> int:
    cands = _all_candidates()
    pending = [c for c in cands if c.get("status") == "pending"]
    resolved = [c for c in cands if c.get("status") != "pending"]

    print(f"\n🎓 Training-Team — Knowledge Candidates")
    print(f"Candidates dir: {_candidates_path()}")
    print(f"Total: {len(cands)} | Pending: {len(pending)} | "
          f"Resolved: {len(resolved)}\n")

    if not cands:
        print("No candidates found. (0 pending)")
        return 0

    if pending:
        print("── Pending ──")
        for c in pending:
            print(f"  [{c['priority']:<8}] {c['candidate_id'][:12]}  "
                  f"{c['team']}/{c['domain']}  — {c['title']}")
    if resolved:
        print("\n── Resolved ──")
        for c in resolved:
            print(f"  [{c['status']:<8}] {c['candidate_id'][:12]}  "
                  f"{c['team']}/{c['domain']}  — {c['title']}")
    return 0


def _flush_to_chromadb(cand: dict) -> str:
    """Promote an approved candidate into ChromaDB via store_knowledge."""
    return store_knowledge(
        team=cand["team"],
        domain=cand["domain"],
        content=cand["content"],
        source=cand["source"],
        title=cand["title"],
        priority=cand["priority"],
        metadata=cand.get("metadata") or {},
    )


def cmd_approve(cand_id: str) -> int:
    try:
        path, data = _load(cand_id)
    except FileNotFoundError as e:
        print(f"❌ {e}", file=sys.stderr)
        return 1

    if data.get("status") == "approved":
        print(f"ℹ️  {cand_id[:12]} already approved (no-op)")
        return 0
    if data.get("status") == "rejected":
        print(f"❌ {cand_id[:12]} was previously rejected; cannot approve",
              file=sys.stderr)
        return 1

    doc_id = _flush_to_chromadb(data)
    data["status"] = "approved"
    data["approved_at"] = datetime.utcnow().isoformat()
    data["chromadb_doc_id"] = doc_id
    _save(path, data)
    print(f"✅ {cand_id[:12]} approved → ChromaDB doc {doc_id}")
    return 0


def cmd_reject(cand_id: str, reason: str = "") -> int:
    try:
        path, data = _load(cand_id)
    except FileNotFoundError as e:
        print(f"❌ {e}", file=sys.stderr)
        return 1

    if data.get("status") == "rejected":
        print(f"ℹ️  {cand_id[:12]} already rejected (no-op)")
        return 0
    if data.get("status") == "approved":
        print(f"❌ {cand_id[:12]} was already approved; cannot reject",
              file=sys.stderr)
        return 1

    data["status"] = "rejected"
    data["rejected_at"] = datetime.utcnow().isoformat()
    if reason:
        data["rejection_reason"] = reason
    _save(path, data)
    print(f"🚫 {cand_id[:12]} rejected")
    return 0


def cmd_approve_all_above(min_priority: str) -> int:
    if min_priority not in PRIORITY_ORDER:
        print(f"❌ priority must be one of {PRIORITY_ORDER}", file=sys.stderr)
        return 2
    threshold = PRIORITY_ORDER.index(min_priority)

    approved = 0
    failed = 0
    for cand in _all_candidates():
        if cand.get("status") != "pending":
            continue
        cand_prio = cand.get("priority", PRIORITY_MEDIUM)
        if cand_prio not in PRIORITY_ORDER:
            continue
        if PRIORITY_ORDER.index(cand_prio) < threshold:
            continue
        rc = cmd_approve(cand["candidate_id"])
        if rc == 0:
            approved += 1
        else:
            failed += 1
    print(f"\nBulk approve ≥{min_priority}: "
          f"{approved} approved, {failed} failed")
    return 0 if failed == 0 else 1


def cmd_watch(interval: int = 10) -> int:
    seen: set[str] = set()
    print(f"👀 Watching {_candidates_path()} (every {interval}s). Ctrl-C to exit.")
    try:
        while True:
            for cand in _all_candidates():
                if cand["candidate_id"] in seen:
                    continue
                if cand.get("status") == "pending":
                    print(f"  NEW pending  [{cand['priority']}]  "
                          f"{cand['candidate_id'][:12]}  "
                          f"{cand['team']}/{cand['domain']} — {cand['title']}")
                seen.add(cand["candidate_id"])
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n👋 watch stopped")
        return 0


def main():
    p = argparse.ArgumentParser(
        description="Training-Team HITL approval CLI for knowledge candidates."
    )
    p.add_argument("--list", action="store_true",
                   help="List all candidates (pending + resolved)")
    p.add_argument("--approve", metavar="CAND_ID",
                   help="Approve candidate and flush to ChromaDB")
    p.add_argument("--reject", metavar="CAND_ID",
                   help="Mark candidate rejected")
    p.add_argument("--reason", metavar="STR", default="",
                   help="Optional reason for --reject")
    p.add_argument("--approve-all-above", metavar="PRIORITY",
                   help="Bulk-approve every pending candidate at or above "
                        "this priority (LOW|MEDIUM|HIGH|CRITICAL)")
    p.add_argument("--watch", action="store_true",
                   help="Poll candidates dir and print new pending entries")
    p.add_argument("--interval", type=int, default=10,
                   help="Poll interval for --watch (seconds)")
    args = p.parse_args()

    if args.list:
        return cmd_list()
    if args.approve:
        return cmd_approve(args.approve)
    if args.reject:
        return cmd_reject(args.reject, args.reason)
    if args.approve_all_above:
        return cmd_approve_all_above(args.approve_all_above)
    if args.watch:
        return cmd_watch(args.interval)

    p.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
