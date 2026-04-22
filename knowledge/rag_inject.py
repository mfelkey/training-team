"""
knowledge/rag_inject.py

Protean Pursuits — RAG context injection

PUSH mechanism: automatically prepends relevant knowledge to every
agent task description before the LLM sees it.

PULL hook: agents call get_latest_context() before finalising outputs
to ensure they have the most current information.

Usage in any agent flow:
    from knowledge.rag_inject import inject_context, get_latest_context

    # Push — prepend context to task description
    task_description = inject_context("legal", task_description,
                                       domains=["uk_gambling_regulation"])

    # Pull — agent calls this before finalising
    latest = get_latest_context("legal", "UK Gambling Commission updates")
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv("config/.env")

# Make knowledge_base importable
_TRAINING_TEAM_PATH = os.getenv(
    "TRAINING_TEAM_PATH",
    os.path.expanduser("~/projects/protean-pursuits/teams/training-team")
)
if _TRAINING_TEAM_PATH not in sys.path:
    sys.path.insert(0, _TRAINING_TEAM_PATH)


def inject_context(team: str, task_description: str,
                   domains: list = None,
                   max_items: int = 8,
                   min_priority: str = None,
                   project: str = None) -> str:
    """
    PUSH: Prepend relevant knowledge context to a task description.

    Called by agent orchestrators before creating Task objects.
    The agent sees the knowledge block at the top of its instructions.

    If `project` is passed, the project's scoped collections are
    queried alongside the team's. Unknown / unregistered projects are
    warned to stdout and the call falls back to team-only context
    (per Day 4 decision 3).

    Returns the task_description with knowledge block prepended.
    If the knowledge base is unavailable, returns task_description unchanged.
    """
    try:
        from knowledge.knowledge_base import (
            build_context_block,
            normalize_project_slug,
            PROJECT_DOMAINS,
        )

        resolved_project = None
        if project:
            candidate = normalize_project_slug(project)
            if candidate in PROJECT_DOMAINS:
                resolved_project = candidate
            else:
                print(
                    f"⚠️  RAG inject: unknown project {project!r} "
                    f"(normalized to {candidate!r}). Falling back to "
                    f"team-only context."
                )

        context_block = build_context_block(
            team=team,
            task_description=task_description,
            domains=domains,
            max_items=max_items,
            project=resolved_project,
        )
        if context_block:
            return f"{context_block}\n{task_description}"
        return task_description
    except Exception as e:
        print(f"⚠️  RAG inject unavailable: {e}")
        return task_description


def get_latest_context(team: str, query: str,
                       domains: list = None,
                       n_results: int = 5) -> str:
    """
    PULL: Agent calls this before finalising outputs to get
    the most current knowledge on a specific topic.

    Returns formatted string of relevant knowledge items,
    or empty string if knowledge base unavailable.
    """
    try:
        from knowledge.knowledge_base import get_context
        items = get_context(team, query, domains, n_results)
        if not items:
            return ""

        lines = [
            f"\n## Latest Knowledge: {query}",
            f"*Retrieved: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}*\n"
        ]
        for item in items:
            priority_icon = {
                "CRITICAL": "🚨", "HIGH": "⚠️",
                "MEDIUM": "ℹ️", "LOW": "📝"
            }.get(item["priority"], "ℹ️")
            lines.append(
                f"{priority_icon} **{item['title']}** "
                f"({item['source']}, {item['stored_at'][:10]})"
            )
            lines.append(item["content"][:400])
            lines.append("")
        return "\n".join(lines)
    except Exception as e:
        print(f"⚠️  RAG pull unavailable: {e}")
        return ""


def check_knowledge_available(team: str) -> bool:
    """Check if knowledge base has content for a team."""
    try:
        from knowledge.knowledge_base import get_freshness_report
        report = get_freshness_report()
        team_report = report.get(team, {})
        return any(v["count"] > 0 for v in team_report.values())
    except Exception:
        return False
