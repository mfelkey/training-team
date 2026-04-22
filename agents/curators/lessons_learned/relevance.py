"""
agents/curators/lessons_learned/relevance.py

Rule-based per-team relevance scoring for LL entries.

Design (per kickoff doc + Day 2 locked-design conversation):
  - Rule-based, keyword substring matching, case-insensitive.
  - UNIVERSAL_KEYWORDS (architectural lessons) hit ALL 11 teams.
  - Team-specific keywords in TEAM_KEYWORDS hit only that team.
  - Entries with no hits return [] (stored anyway, with empty teams —
    the curator decides whether to keep or drop).

The scorer is deliberately shallow. If precision ever becomes the
bottleneck, the kickoff doc allows a hybrid upgrade (LLM-scored
fallback for ambiguous entries).
"""
from __future__ import annotations


# Architectural / cross-cutting lessons — hit every team.
UNIVERSAL_KEYWORDS = [
    "submodule",
    "dispatch",
    "runtime",
    "tier_model", "tier1_model", "tier2_model",
    "invoke_team_flow",
    "base factory",
    "orchestrator",
    "pp_flow",
    "intake_flow",
    "verification script",
    "hitl gate",
    "propose_knowledge",
    "store_knowledge",
    "knowledge_base",
    "chromadb",
    "crewai",
    "ollama",
]


# Team-specific vocabulary. Kept short and distinctive to avoid false
# positives — "code" would match every LL, so we pick terms that
# actually signal team ownership.
TEAM_KEYWORDS: dict[str, list[str]] = {
    "legal": [
        "ukgc", "gambling commission", "gdpr", "ico",
        "data protection", "regulatory", "regulation",
        "asa", "cap code", "acma", "iagr", "edpb",
        "licence", "license compliance",
        "privacy policy", "responsible gambling",
    ],
    "dev": [
        "cve", "vulnerability", "dependency",
        "framework release", "api change", "subprocess",
        "npm audit", "pip", "git am",
        "patch", "build", "deploy", "vercel", "eas",
    ],
    "ds": [
        "xg", "brier", "bayesian", "mle",
        "model training", "feature engineering",
        "calibration", "regression", "statsbomb",
        "understat", "backtest",
    ],
    "design": [
        "wcag", "accessibility", "design system",
        "figma", "component library", "ux research",
        "color token", "typography", "wireframe",
    ],
    "marketing": [
        "meta ad", "instagram", "reddit ad",
        "tiktok", "campaign", "gambling ad",
        "platform policy", "ad certification",
        "ai-generated content", "brand reveal",
    ],
    "strategy": [
        "market intelligence", "competitor",
        "industry trend", "go-to-market",
        "investor", "strategic plan",
    ],
    "qa": [
        "owasp", "testing framework", "pen test",
        "load test", "test suite", "test coverage",
        "regression test", "cve", "security advisory",
    ],
    "hr": [
        "recruiting", "onboarding", "performance review",
        "compensation", "benefits", "culture",
        "employment law", "policy and compliance",
    ],
    "finance": [
        "cost analyst", "roi", "pricing",
        "billing", "stripe", "budget",
        "revenue", "financial statement",
        "cap table", "runway",
    ],
    "video": [
        "video script", "avatar", "voiceover",
        "motion graphic", "explainer",
        "screen recording", "youtube", "tiktok video",
    ],
    "sme": [
        "sports betting", "pga", "lpga",
        "nba", "nfl", "mlb", "nhl", "mma",
        "cricket", "rugby", "tennis",
        "horse racing", "harness racing",
        "boxing", "soccer betting",
    ],
}


def _haystack(entry: dict) -> str:
    """Concatenate all searchable fields into one lowercase string."""
    parts = [
        entry.get("title", ""),
        entry.get("severity", ""),
        entry.get("affected", ""),
        entry.get("body", ""),
    ]
    return " ".join(parts).lower()


def score_relevance(entry: dict) -> list[str]:
    """
    Return the list of team keys relevant to this LL entry.

    Order of returned teams is stable (sorted), which makes the output
    deterministic and test-friendly.
    """
    hay = _haystack(entry)

    # Universal keywords: any match means all 11 teams.
    for kw in UNIVERSAL_KEYWORDS:
        if kw.lower() in hay:
            return sorted(TEAM_KEYWORDS.keys())

    hit: set[str] = set()
    for team, kws in TEAM_KEYWORDS.items():
        for kw in kws:
            if kw.lower() in hay:
                hit.add(team)
                break

    return sorted(hit)
