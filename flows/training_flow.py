"""
flows/training_flow.py

Protean Pursuits — Training Team Flow

Usage:
  # Full refresh — all teams
  python3.11 flows/training_flow.py --mode full

  # Single team refresh
  python3.11 flows/training_flow.py --mode team --team legal

  # On-demand — triggered by specific news
  python3.11 flows/training_flow.py --mode on_demand --team legal --topic "UKGC new ruling"

  # Status report
  python3.11 flows/training_flow.py --mode status

  # Show recent critical alerts
  python3.11 flows/training_flow.py --mode alerts --hours 48
"""

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.orchestrator.orchestrator import (
    run_full_refresh, run_curator, show_status, show_alerts,
    notify_critical_updates
)
from knowledge.knowledge_base import TEAM_DOMAINS, get_critical_alerts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Protean Pursuits — Training Team"
    )
    parser.add_argument("--mode",
        choices=["full", "team", "on_demand", "status", "alerts"],
        required=True)
    parser.add_argument("--team", type=str, default=None,
        help=f"Team to update. Options: {list(TEAM_DOMAINS.keys())}")
    parser.add_argument("--topic", type=str, default=None,
        help="Specific topic for on-demand refresh")
    parser.add_argument("--hours", type=int, default=24,
        help="Hours to look back for alerts (default: 24)")
    args = parser.parse_args()

    if args.mode == "full":
        run_full_refresh()

    elif args.mode == "team":
        if not args.team:
            print(f"❌ --team required. Options: {list(TEAM_DOMAINS.keys())}")
            sys.exit(1)
        if args.team not in TEAM_DOMAINS:
            print(f"❌ Unknown team: {args.team}")
            sys.exit(1)
        run_curator(args.team)
        alerts = get_critical_alerts(since_hours=1)
        if alerts:
            notify_critical_updates(alerts)

    elif args.mode == "on_demand":
        if not args.team or not args.topic:
            print("❌ --team and --topic required for on_demand mode")
            sys.exit(1)
        print(f"\n🔔 On-demand refresh: [{args.team.upper()}] {args.topic}")
        run_curator(args.team, on_demand_topic=args.topic)
        alerts = get_critical_alerts(since_hours=1)
        if alerts:
            notify_critical_updates(alerts)

    elif args.mode == "status":
        show_status()

    elif args.mode == "alerts":
        show_alerts(hours=args.hours)
