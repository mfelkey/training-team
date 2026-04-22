"""
agents/orchestrator/orchestrator.py

Protean Pursuits — Training Team Orchestrator

Coordinates all 7 domain curators, manages the knowledge refresh
schedule, sends Pushover alerts for CRITICAL updates, and ensures
every agent team has fresh, relevant knowledge before running.

Run modes:
  FULL        — refresh all 7 team knowledge bases
  TEAM        — refresh one team's knowledge base
  ON_DEMAND   — targeted refresh triggered by a specific news item
  STATUS      — show knowledge freshness report
  ALERTS      — show critical alerts from last 24h
"""

import os
import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv("config/.env")

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from knowledge.knowledge_base import (
    get_freshness_report, get_critical_alerts,
    PRIORITY_HIGH, PRIORITY_CRITICAL, TEAM_DOMAINS
)

TRAINING_TEAM_PATH = Path(__file__).resolve().parents[2]


def send_pushover(subject: str, message: str, priority: int = 1) -> bool:
    """Send Pushover notification."""
    import urllib.request
    import urllib.parse
    user_key  = os.getenv("PUSHOVER_USER_KEY", "")
    api_token = os.getenv("PUSHOVER_API_TOKEN", "")
    if not user_key or not api_token:
        print(f"⚠️  Pushover not configured")
        return False
    try:
        data = urllib.parse.urlencode({
            "token": api_token, "user": user_key,
            "title": subject[:250], "message": message[:1024],
            "priority": priority,
        }).encode("utf-8")
        import urllib.request
        req = urllib.request.Request(
            "https://api.pushover.net/1/messages.json",
            data=data, method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            return result.get("status") == 1
    except Exception as e:
        print(f"⚠️  Pushover failed: {e}")
        return False


def notify_critical_updates(alerts: list) -> None:
    """Send Pushover alerts for CRITICAL knowledge updates."""
    if not alerts:
        return
    critical = [a for a in alerts if a.get("priority") == PRIORITY_CRITICAL]
    high     = [a for a in alerts if a.get("priority") == PRIORITY_HIGH]

    if critical:
        for alert in critical:
            send_pushover(
                subject=f"🚨 CRITICAL: {alert['team'].upper()} — {alert['title'][:50]}",
                message=(
                    f"Domain: {alert['domain']}\n"
                    f"Source: {alert['source']}\n"
                    f"{alert['content'][:300]}"
                ),
                priority=2  # Pushover emergency — requires acknowledgement
            )

    if high:
        summary = "\n".join([
            f"• [{a['team'].upper()}] {a['title'][:60]}"
            for a in high[:5]
        ])
        send_pushover(
            subject=f"⚠️  {len(high)} HIGH priority knowledge updates",
            message=summary,
            priority=1
        )


def run_curator(team: str, on_demand_topic: str = None) -> dict:
    """Run a domain curator for a specific team."""
    curator_path = TRAINING_TEAM_PATH / "agents" / "curators" / team / "curator.py"
    if not curator_path.exists():
        print(f"⚠️  No curator found for team: {team}")
        return {"team": team, "status": "NO_CURATOR"}

    cmd = [sys.executable, str(curator_path)]
    if on_demand_topic:
        cmd += ["--topic", on_demand_topic]

    print(f"\n🎓 [{team.upper()}] Running knowledge curator...")
    try:
        result = subprocess.run(
            cmd, cwd=str(TRAINING_TEAM_PATH),
            text=True, timeout=1800
        )
        status = "COMPLETE" if result.returncode == 0 else "ERROR"
        print(f"  {'✅' if status == 'COMPLETE' else '❌'} {team}: {status}")
        return {"team": team, "status": status}
    except subprocess.TimeoutExpired:
        print(f"  ⏰ {team}: TIMEOUT")
        return {"team": team, "status": "TIMEOUT"}
    except Exception as e:
        print(f"  ❌ {team}: {e}")
        return {"team": team, "status": "ERROR", "error": str(e)}


def run_full_refresh(teams: list = None) -> dict:
    """Run all curators for a full knowledge refresh."""
    teams_to_run = teams or list(TEAM_DOMAINS.keys())
    started_at = datetime.utcnow().isoformat()
    results = []

    print(f"\n{'='*60}")
    print(f"🎓 Training Team — Full Knowledge Refresh")
    print(f"   Teams: {', '.join(teams_to_run)}")
    print(f"   Started: {started_at}")
    print(f"{'='*60}")

    for team in teams_to_run:
        result = run_curator(team)
        results.append(result)

    # Check for critical alerts after refresh
    alerts = get_critical_alerts(since_hours=2)
    if alerts:
        print(f"\n🚨 {len(alerts)} critical/high alerts found — sending notifications")
        notify_critical_updates(alerts)

    completed = sum(1 for r in results if r["status"] == "COMPLETE")
    summary = {
        "started_at": started_at,
        "completed_at": datetime.utcnow().isoformat(),
        "teams_run": len(results),
        "completed": completed,
        "errors": len(results) - completed,
        "critical_alerts": len(alerts),
        "results": results
    }

    # Save run log
    log_path = TRAINING_TEAM_PATH / "logs" / f"refresh_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    log_path.parent.mkdir(exist_ok=True)
    with open(log_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)

    print(f"\n✅ Refresh complete — {completed}/{len(results)} teams updated")
    if alerts:
        print(f"🚨 {len(alerts)} critical/high priority alerts sent to Pushover")

    return summary


def show_status() -> None:
    """Display knowledge freshness report."""
    report = get_freshness_report()
    print(f"\n{'─'*65}")
    print(f"  {'TEAM':<12} {'DOMAIN':<28} {'ITEMS':<8} LAST UPDATED")
    print(f"{'─'*65}")
    for team, domains in report.items():
        for domain, info in domains.items():
            count = info["count"]
            latest = info["latest"][:10] if info["latest"] else "never"
            icon = "✅" if count > 0 else "❌"
            print(f"  {icon} {team:<10} {domain:<28} {count:<8} {latest}")
    print(f"{'─'*65}\n")


def show_alerts(hours: int = 24) -> None:
    """Show critical alerts from the last N hours."""
    alerts = get_critical_alerts(since_hours=hours)
    if not alerts:
        print(f"\n✅ No critical/high alerts in the last {hours}h\n")
        return
    print(f"\n🚨 {len(alerts)} alerts in the last {hours}h:\n")
    for alert in alerts:
        print(f"  [{alert['team'].upper()}] {alert['title']}")
        print(f"  Source: {alert['source']} | {alert['stored_at'][:16]}")
        print(f"  {alert['content'][:150]}...")
        print()
