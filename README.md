# Protean Pursuits — Training Team

Keeps all 7 agent teams up to date with the latest knowledge in their domains.

## Architecture

- **7 Domain Curators** — one per team, each watching domain-specific sources
- **ChromaDB Knowledge Base** — partitioned by team and topic
- **Push injection** — knowledge automatically prepended to every agent task
- **Pull hook** — agents call `get_latest_context()` before finalising outputs
- **Pushover alerts** — CRITICAL updates trigger immediate notification

## Run Modes

```bash
# Full refresh — all teams (also runs nightly via cron)
python3.11 flows/training_flow.py --mode full

# Single team refresh
python3.11 flows/training_flow.py --mode team --team legal

# On-demand — triggered by specific news
python3.11 flows/training_flow.py --mode on_demand --team legal --topic "UKGC new ruling"

# Knowledge freshness status
python3.11 flows/training_flow.py --mode status

# Recent critical alerts
python3.11 flows/training_flow.py --mode alerts --hours 48
```

## Cron Setup

```bash
# Install nightly 2AM cron job
python3.11 scripts/setup_cron.py --install

# Check status
python3.11 scripts/setup_cron.py --status
```

## Knowledge Domains

| Team | Domains |
|---|---|
| Legal | UK/US/EU/AU gambling regulation, data protection, IP, financial promotion |
| DS | xG modeling, soccer analytics, sports betting models, ML techniques, data providers |
| Dev | Framework releases, CVEs, API changes, best practices |
| Marketing | Platform policies, gambling ad regulation, industry news |
| Strategy | Market intelligence, competitor analysis, industry trends |
| Design | WCAG updates, accessibility law, design system releases |
| QA | OWASP updates, testing frameworks, compliance standards |

## Using RAG in Agent Flows

```python
from knowledge.rag_inject import inject_context, get_latest_context

# PUSH — prepend context to task (call before creating Task objects)
task_description = inject_context("legal", task_description,
                                   domains=["uk_gambling_regulation"])

# PULL — agent calls before finalising output
latest = get_latest_context("legal", "UK Gambling Commission updates")
```
