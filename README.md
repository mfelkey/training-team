# Protean Pursuits — Training Team

Keeps all 11 Protean Pursuits teams current with the latest knowledge in
their domains. Every ingestion is human-approved; no curator writes to
ChromaDB directly.

## Architecture

- **11 Domain Curators** — one per team, each watching domain-specific sources
- **1 Lessons Learned Curator** — parses `LESSONS_LEARNED.md` files into
  cross-team candidates stored in the `lessons_learned` top-level collection
- **ChromaDB Knowledge Base** — partitioned by team, by project, and by
  top-level cross-cutting domain
- **HITL gate** — curators call `propose_knowledge()` which writes to
  `knowledge/candidates/*.json`; `scripts/approve_candidates.py` is the
  only path into ChromaDB
- **Push injection** — approved knowledge auto-prepended to agent tasks
- **Pull hook** — agents call `get_latest_context()` before finalising
- **Pushover alerts** — CRITICAL updates trigger immediate notification

## Collection layers (Phase 2)

1. **Team collections** — `{team}_{domain}`, e.g. `legal_uk_gambling_regulation`.
   Queried by that team's agents.
2. **Top-level collections** — cross-cutting knowledge, e.g. `lessons_learned_platform`.
   Queried by every agent by default.
3. **Project collections** — `{project_slug}_{domain}`, e.g.
   `parallaxedge_domain`. Queried only when an agent explicitly passes
   `project=<slug>` to `inject_context()`.

## Run Modes

```bash
# Full refresh — all teams (also runs nightly via cron)
python3.11 flows/training_flow.py --mode full

# Single team refresh
python3.11 flows/training_flow.py --mode team --team legal

# On-demand — triggered by specific news
python3.11 flows/training_flow.py --mode on_demand --team legal --topic "UKGC new ruling"

# Ingest Lessons Learned (platform or project)
python3.11 flows/training_flow.py --mode ll \
    --ll-path ~/projects/protean-pursuits/docs/LESSONS_LEARNED.md \
    --source-type platform

# Knowledge freshness status (teams + top-level + registered projects)
python3.11 flows/training_flow.py --mode status

# Recent critical alerts
python3.11 flows/training_flow.py --mode alerts --hours 48
```

## HITL approval workflow

Curators never write to ChromaDB directly. Every ingestion lands in
`knowledge/candidates/*.json` with `status: pending`. Use:

```bash
# List pending candidates
python3.11 scripts/approve_candidates.py --list

# Approve one
python3.11 scripts/approve_candidates.py --approve <candidate_id>

# Reject one (optional reason)
python3.11 scripts/approve_candidates.py --reject <candidate_id> --reason "duplicate"

# Bulk-approve everything at or above a priority threshold
python3.11 scripts/approve_candidates.py --approve-all-above HIGH

# Watch for new pending candidates and get Pushover-notified
python3.11 scripts/approve_candidates.py --watch
```

Only `--approve` flushes a candidate to ChromaDB via
`knowledge.knowledge_base.store_knowledge`.

## Cron Setup

```bash
# Install nightly 2AM cron job
python3.11 scripts/setup_cron.py --install

# Check status
python3.11 scripts/setup_cron.py --status
```

## Knowledge Domains (11 teams)

| Team       | Domains |
|------------|---------|
| Legal      | UK/US/EU/AU gambling regulation, data protection, IP, financial promotion |
| DS         | xG modeling, soccer analytics, sports betting models, ML techniques, data providers |
| Dev        | Framework releases, CVEs, API changes, best practices, dependency updates |
| Marketing  | Platform policies, gambling ad regulation, industry news |
| Strategy   | Market intelligence, competitor analysis, industry trends, investor landscape |
| Design     | WCAG updates, accessibility law, design system releases, UX research |
| QA         | OWASP updates, testing frameworks, compliance standards, security advisories |
| Finance    | SEC filings, FASB standards, tax updates, SaaS metrics, payment processing |
| HR         | Employment law (US/intl), compensation, benefits, HR tech, culture research |
| Video      | Platform policies, AI video tools, content guidelines, SEO, ad standards |
| SME        | 16 sports-betting sub-domains (PGA, LPGA, NFL/NCAA, NBA/NCAA, MLB, NHL, MMA, tennis, rugby, cricket, WNBA, horse racing, harness racing, boxing, soccer, cross-sport) |

## Using RAG in Agent Flows

```python
from knowledge.rag_inject import inject_context, get_latest_context

# Push — team-only (default)
task_description = inject_context("legal", task_description,
                                   domains=["uk_gambling_regulation"])

# Push — team + project scope (Phase 2)
task_description = inject_context("legal", task_description,
                                   project="parallaxedge")

# Pull — agent calls before finalising
latest = get_latest_context("legal", "UK Gambling Commission updates")
```

## Registering a project (Phase 2)

Projects need to be registered before `inject_context(project=...)` will
pick up their collections:

```python
from knowledge.knowledge_base import register_project

slug = register_project("ParallaxEdge")
# slug == 'parallaxedge', domains default to ['domain', 'market']

# With explicit domains
register_project("ParallaxEdge",
                 domains=["domain", "market", "nascar_data"])
```

Registration auto-normalizes the input to a canonical slug
(lowercase/underscores/alphanumerics only) and logs a warning if
normalization changed the input.

## Testing

```bash
# Fast unit tests (default)
python3.11 -m pytest tests/                  # 135 tests, ~7s

# Integration tests (requires working ChromaDB embedder)
python3.11 -m pytest tests/ -m integration
```

## Phase 2 roadmap status

See the Phase 2 kickoff doc for full scope. As of Day 6:

- ✅ HITL gate (Day 1)
- ✅ Lessons Learned curator + parser + rule-based relevance scorer (Day 2)
- ✅ All 7 existing curators migrated to `propose_knowledge` (Day 3)
- ✅ Training team lead + `TEAM_TEMPLATES` complete with all 10 teams (Day 3)
- ✅ Per-project collection layer (Day 4)
- ✅ 4 new team curators (finance, hr, video, sme) (Day 5)
- ✅ `ll` mode on the flow + docs + post-commit hook helper (Day 6)
- ⏳ End-to-end hardening (Day 7)
