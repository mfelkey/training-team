"""
knowledge/knowledge_base.py

Protean Pursuits — Training Team Knowledge Base

ChromaDB-backed knowledge store partitioned by team and topic.
Serves as the single source of truth for all agent RAG context.

Collections follow naming convention: {team}_{topic}
e.g. legal_regulation, ds_xg_models, dev_frameworks
"""

import os
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv("config/.env")

DB_PATH = os.getenv("KNOWLEDGE_DB_PATH",
                    os.path.expanduser("~/projects/protean-pursuits/teams/training-team/knowledge/db"))

# Priority levels for knowledge items
PRIORITY_LOW      = "LOW"
PRIORITY_MEDIUM   = "MEDIUM"
PRIORITY_HIGH     = "HIGH"
PRIORITY_CRITICAL = "CRITICAL"

# Knowledge domains per team
TEAM_DOMAINS = {
    "legal": [
        "uk_gambling_regulation",
        "us_gambling_regulation",
        "eu_regulation",
        "au_regulation",
        "data_protection",
        "ip_licensing",
        "financial_promotion",
        "responsible_gambling",
    ],
    "ds": [
        "xg_modeling",
        "soccer_analytics",
        "sports_betting_models",
        "ml_techniques",
        "data_providers",
        "statistical_methods",
    ],
    "dev": [
        "framework_releases",
        "security_vulnerabilities",
        "api_changes",
        "best_practices",
        "dependency_updates",
    ],
    "marketing": [
        "platform_policies",
        "gambling_ad_regulation",
        "content_strategy",
        "industry_news",
        "competitor_activity",
    ],
    "strategy": [
        "market_intelligence",
        "competitor_analysis",
        "industry_trends",
        "regulatory_landscape",
        "investor_landscape",
    ],
    "design": [
        "wcag_updates",
        "accessibility_law",
        "design_system_releases",
        "ux_research",
        "component_patterns",
    ],
    "qa": [
        "owasp_updates",
        "testing_frameworks",
        "compliance_standards",
        "security_advisories",
        "performance_benchmarks",
    ],
}


def _get_chroma_client():
    """Get or create ChromaDB client."""
    try:
        import chromadb
        Path(DB_PATH).mkdir(parents=True, exist_ok=True)
        return chromadb.PersistentClient(path=DB_PATH)
    except ImportError:
        raise ImportError(
            "chromadb not installed. Run: pip install chromadb"
        )


def _collection_name(team: str, domain: str) -> str:
    return f"{team}_{domain}"


def _doc_id(content: str, source: str) -> str:
    """Generate stable document ID from content hash."""
    return hashlib.sha256(f"{source}:{content[:200]}".encode()).hexdigest()[:16]


def store_knowledge(team: str, domain: str, content: str,
                    source: str, title: str,
                    priority: str = PRIORITY_MEDIUM,
                    metadata: dict = None) -> str:
    """
    Store a knowledge item in the team's domain collection.
    Returns the document ID.
    """
    client = _get_chroma_client()
    collection = client.get_or_create_collection(
        name=_collection_name(team, domain),
        metadata={"team": team, "domain": domain}
    )

    doc_id = _doc_id(content, source)
    meta = {
        "team":      team,
        "domain":    domain,
        "source":    source,
        "title":     title,
        "priority":  priority,
        "stored_at": datetime.utcnow().isoformat(),
    }
    if metadata:
        meta.update(metadata)

    collection.upsert(
        ids=[doc_id],
        documents=[content],
        metadatas=[meta]
    )
    return doc_id


def get_context(team: str, query: str,
                domains: list = None,
                n_results: int = 5,
                min_priority: str = None) -> list:
    """
    Retrieve relevant knowledge for a team given a query.

    team:         which team's knowledge to search
    query:        semantic search query
    domains:      limit to specific domains (None = all team domains)
    n_results:    max results per collection
    min_priority: filter by minimum priority (LOW/MEDIUM/HIGH/CRITICAL)

    Returns list of dicts: {content, source, title, priority, domain, stored_at}
    """
    client = _get_chroma_client()
    search_domains = domains or TEAM_DOMAINS.get(team, [])
    results = []
    priority_order = [PRIORITY_LOW, PRIORITY_MEDIUM,
                      PRIORITY_HIGH, PRIORITY_CRITICAL]
    min_idx = priority_order.index(min_priority) if min_priority else 0

    for domain in search_domains:
        collection_name = _collection_name(team, domain)
        try:
            collection = client.get_collection(collection_name)
            count = collection.count()
            if count == 0:
                continue
            res = collection.query(
                query_texts=[query],
                n_results=min(n_results, count)
            )
            for i, doc in enumerate(res["documents"][0]):
                meta = res["metadatas"][0][i]
                priority = meta.get("priority", PRIORITY_MEDIUM)
                if priority_order.index(priority) >= min_idx:
                    results.append({
                        "content":   doc,
                        "source":    meta.get("source", ""),
                        "title":     meta.get("title", ""),
                        "priority":  priority,
                        "domain":    domain,
                        "stored_at": meta.get("stored_at", ""),
                    })
        except Exception:
            continue

    # Sort by priority (highest first) then recency
    results.sort(
        key=lambda x: (
            -priority_order.index(x.get("priority", PRIORITY_MEDIUM)),
            x.get("stored_at", "")
        ),
        reverse=False
    )
    return results[:n_results * 2]


def build_context_block(team: str, task_description: str,
                        domains: list = None,
                        max_items: int = 8) -> str:
    """
    Build a formatted context block to prepend to agent task prompts.
    This is the PUSH mechanism — called before every agent task.

    Returns a markdown-formatted string ready to inject into prompts.
    """
    items = get_context(team, task_description, domains,
                        n_results=max_items)
    if not items:
        return ""

    lines = [
        "## 📚 Knowledge Base Context",
        f"*Relevant knowledge for {team} team — retrieved {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}*\n",
    ]

    # Group by priority
    critical = [i for i in items if i["priority"] == PRIORITY_CRITICAL]
    high     = [i for i in items if i["priority"] == PRIORITY_HIGH]
    other    = [i for i in items if i["priority"]
                not in (PRIORITY_CRITICAL, PRIORITY_HIGH)]

    if critical:
        lines.append("### 🚨 CRITICAL — Act on this immediately")
        for item in critical:
            lines.append(f"**{item['title']}** ({item['source']})")
            lines.append(item["content"][:500])
            lines.append("")

    if high:
        lines.append("### ⚠️  HIGH PRIORITY")
        for item in high:
            lines.append(f"**{item['title']}** ({item['source']})")
            lines.append(item["content"][:400])
            lines.append("")

    if other:
        lines.append("### ℹ️  Background Knowledge")
        for item in other:
            lines.append(f"**{item['title']}** ({item['source']})")
            lines.append(item["content"][:300])
            lines.append("")

    lines.append("---\n")
    return "\n".join(lines)


def get_freshness_report() -> dict:
    """Return a report of knowledge freshness per team/domain."""
    client = _get_chroma_client()
    report = {}
    for team, domains in TEAM_DOMAINS.items():
        report[team] = {}
        for domain in domains:
            try:
                collection = client.get_collection(_collection_name(team, domain))
                count = collection.count()
                # Get most recent item
                if count > 0:
                    results = collection.get(limit=1,
                        where={"team": team})
                    latest = results["metadatas"][0]["stored_at"] \
                        if results["metadatas"] else "unknown"
                else:
                    latest = None
                report[team][domain] = {"count": count, "latest": latest}
            except Exception:
                report[team][domain] = {"count": 0, "latest": None}
    return report


def get_critical_alerts(since_hours: int = 24) -> list:
    """Return all CRITICAL priority items stored in the last N hours."""
    from datetime import timedelta
    cutoff = (datetime.utcnow() - timedelta(hours=since_hours)).isoformat()
    client = _get_chroma_client()
    alerts = []
    for team, domains in TEAM_DOMAINS.items():
        for domain in domains:
            try:
                collection = client.get_collection(_collection_name(team, domain))
                results = collection.get(
                    where={"$and": [
                        {"priority": {"$eq": PRIORITY_CRITICAL}},
                        {"stored_at": {"$gte": cutoff}}
                    ]}
                )
                for i, doc in enumerate(results["documents"]):
                    meta = results["metadatas"][i]
                    alerts.append({
                        "team":   team,
                        "domain": domain,
                        "title":  meta.get("title", ""),
                        "source": meta.get("source", ""),
                        "stored_at": meta.get("stored_at", ""),
                        "content": doc[:300],
                    })
            except Exception:
                continue
    return alerts
