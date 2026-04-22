"""
agents/curators/lessons_learned/curator.py

Lessons Learned Curator — Training-Team Phase 2 Day 2.

Parses a LESSONS_LEARNED.md file, scores each entry for per-team
relevance, and writes one candidate per entry via propose_knowledge().
Candidates land in the top-level `lessons_learned` collection
(team="lessons_learned", domain="platform" | "project"), with the
relevant_teams list stored as JSON-encoded metadata so ChromaDB's
flat metadata store accepts it (chromadb rejects list-valued metadata).

Usage:
    # Platform lessons
    python3.11 agents/curators/lessons_learned/curator.py \\
        --ll-path ~/projects/protean-pursuits/docs/LESSONS_LEARNED.md \\
        --source-type platform

    # Project lessons (e.g. ParallaxEdge)
    python3.11 agents/curators/lessons_learned/curator.py \\
        --ll-path ~/projects/parallaxedge/docs/LESSONS_LEARNED.md \\
        --source-type project

Every proposed candidate carries:
    team          = "lessons_learned"   (top-level, not per-team)
    domain        = "platform" | "project"
    title         = "LL-NNN — <title>"
    content       = full markdown body
    priority      = derived from severity (CRITICAL/HIGH → HIGH;
                    MEDIUM → MEDIUM; LOW → LOW; unknown → MEDIUM)
    metadata:
        ll_id             LL-NNN
        ll_date           ISO date
        severity          full severity line
        affected          full affected line
        source_type       "platform" | "project"
        source_file       absolute path to the LL file
        relevant_teams    JSON-encoded list of team keys
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# Put submodule root on sys.path so `knowledge.*` resolves.
_SUBMODULE_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_SUBMODULE_ROOT))

from knowledge.knowledge_base import (  # noqa: E402
    propose_knowledge,
    PRIORITY_LOW, PRIORITY_MEDIUM, PRIORITY_HIGH,
)
from agents.curators.lessons_learned.parser import parse_ll_file  # noqa: E402
from agents.curators.lessons_learned.relevance import score_relevance  # noqa: E402

logger = logging.getLogger(__name__)


# The top-level collection name (per knowledge_base.TOP_LEVEL_DOMAINS).
# We route all LL candidates to team="lessons_learned" with the
# source_type as the domain, which keeps the {team}_{domain} idiom
# intact — e.g. "lessons_learned_platform", "lessons_learned_project".
TOP_LEVEL_TEAM = "lessons_learned"


def _severity_to_priority(severity: str) -> str:
    sev = (severity or "").upper()
    if "CRITICAL" in sev or "HIGH" in sev:
        return PRIORITY_HIGH
    if "LOW" in sev:
        return PRIORITY_LOW
    return PRIORITY_MEDIUM


def run(ll_path: Path | str, source_type: str = "platform") -> int:
    """
    Parse the given LL file and propose one candidate per entry.
    Returns the number of candidates proposed.
    """
    p = Path(ll_path).expanduser()
    entries = parse_ll_file(p)
    if not entries:
        logger.info(f"  ℹ️  no entries found at {p}")
        return 0

    proposed = 0
    for entry in entries:
        relevant_teams = score_relevance(entry)
        priority = _severity_to_priority(entry["severity"])

        try:
            propose_knowledge(
                team=TOP_LEVEL_TEAM,
                domain=source_type,
                content=entry["body"],
                source=f"{source_type}:LESSONS_LEARNED.md",
                title=f"{entry['ll_id']} — {entry['title']}",
                priority=priority,
                metadata={
                    "ll_id":          entry["ll_id"],
                    "ll_date":        entry["date"],
                    "severity":       entry["severity"],
                    "affected":       entry["affected"],
                    "source_type":    source_type,
                    "source_file":    str(p),
                    # ChromaDB rejects list-valued metadata; encode as JSON.
                    "relevant_teams": json.dumps(relevant_teams),
                },
            )
            proposed += 1
            print(
                f"  ✅ {entry['ll_id']} proposed "
                f"(teams: {','.join(relevant_teams) or 'none'})"
            )
        except Exception as e:
            logger.warning(f"  ⚠️  {entry['ll_id']}: {e}")

    return proposed


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Lessons Learned Curator — parse LL files into HITL candidates."
    )
    ap.add_argument(
        "--ll-path", type=str, required=True,
        help="Path to a LESSONS_LEARNED.md file",
    )
    ap.add_argument(
        "--source-type", choices=["platform", "project"],
        default="platform",
        help="'platform' for protean-pursuits/docs, 'project' for project repos",
    )
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    print(f"\n🎓 LL Curator — {args.source_type}")
    n = run(ll_path=args.ll_path, source_type=args.source_type)
    print(f"✅ LL ({args.source_type}): {n} entries proposed (pending HITL approval)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
