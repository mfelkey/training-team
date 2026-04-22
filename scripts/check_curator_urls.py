#!/usr/bin/env python3
"""
scripts/check_curator_urls.py

Probes every SOURCES entry across every curator and reports HTTP
reachability. Intended for one-shot validation after any SOURCES list
change, or before a new curator's first cron run.

Per-source result:
  ✅ 2xx/3xx — URL resolves and returns a success status
  🔒 403/401 — access denied (paywall / bot-block / geo-fence)
  ⚠️  404    — gone (probably moved)
  ❌ DNS/conn/timeout — reachable network issue
  ❓ other    — see detail

Usage:
    # All curators
    python3.11 scripts/check_curator_urls.py

    # One curator
    python3.11 scripts/check_curator_urls.py --team sme

    # Faster probing, fewer retries
    python3.11 scripts/check_curator_urls.py --timeout 5 --head-only

Exit code is the number of non-healthy URLs (0 = all green).

Does NOT call propose_knowledge — purely a reachability probe.
Content scraping / parsing logic is unaffected.
"""
from __future__ import annotations

import argparse
import importlib
import json
import socket
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, asdict
from pathlib import Path


SUBMODULE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUBMODULE_ROOT))


@dataclass
class ProbeResult:
    team:     str
    name:     str
    url:      str
    domain:   str
    priority: str
    status:   str   # "ok" | "denied" | "gone" | "error" | "unknown"
    http:     int   # HTTP status code (0 if network error)
    detail:   str   # short explanation


def _classify(http_code: int, err: str) -> str:
    if 200 <= http_code < 400:
        return "ok"
    if http_code in (401, 403):
        return "denied"
    if http_code == 404:
        return "gone"
    if http_code == 0:
        return "error"
    return "unknown"


def _probe_url(url: str, timeout: int, head_only: bool) -> tuple[int, str]:
    """Single URL probe. Returns (http_code, detail). http_code=0 on net error."""
    method = "HEAD" if head_only else "GET"
    req = urllib.request.Request(
        url,
        method=method,
        headers={"User-Agent": "Mozilla/5.0 Protean-Pursuits-Training-Bot/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, f"{method} {resp.status}"
    except urllib.error.HTTPError as e:
        return e.code, f"HTTPError {e.code}"
    except urllib.error.URLError as e:
        reason = str(e.reason) if hasattr(e, "reason") else str(e)
        return 0, f"URLError: {reason}"
    except socket.timeout:
        return 0, f"timeout after {timeout}s"
    except Exception as e:
        return 0, f"{type(e).__name__}: {e}"


def _curator_teams() -> list[str]:
    """Return team names that have a curator/<team>/curator.py file."""
    base = SUBMODULE_ROOT / "agents" / "curators"
    out = []
    for entry in sorted(base.iterdir()):
        if not entry.is_dir() or entry.name.startswith("_"):
            continue
        if (entry / "curator.py").exists():
            out.append(entry.name)
    return out


def _load_sources(team: str) -> list[dict]:
    """Import curators/<team>/curator.py and return its SOURCES list.
    The LL curator has no SOURCES — return []."""
    mod_name = f"agents.curators.{team}.curator"
    try:
        mod = importlib.import_module(mod_name)
    except Exception as e:
        print(f"  ⚠️  {team}: import failed — {e}", file=sys.stderr)
        return []
    return list(getattr(mod, "SOURCES", []))


_STATUS_GLYPH = {
    "ok":      "✅",
    "denied":  "🔒",
    "gone":    "⚠️",
    "error":   "❌",
    "unknown": "❓",
}


def run(teams: list[str], timeout: int, head_only: bool,
        json_out: bool) -> int:
    all_results: list[ProbeResult] = []
    unhealthy = 0

    for team in teams:
        sources = _load_sources(team)
        if not sources:
            continue
        if not json_out:
            print(f"\n🎓 {team}  ({len(sources)} sources)")
            print("─" * 60)
        for src in sources:
            url = src.get("url", "")
            http, detail = _probe_url(url, timeout, head_only)
            status = _classify(http, detail)
            if status != "ok":
                unhealthy += 1
            result = ProbeResult(
                team=team,
                name=src.get("name", "?"),
                url=url,
                domain=src.get("domain", "?"),
                priority=src.get("priority", "MEDIUM"),
                status=status,
                http=http,
                detail=detail,
            )
            all_results.append(result)
            if not json_out:
                glyph = _STATUS_GLYPH.get(status, "❓")
                print(f"  {glyph} [{src.get('priority', 'MEDIUM'):<8}] "
                      f"{src.get('name', '?'):<38}  {detail}")

    if json_out:
        print(json.dumps([asdict(r) for r in all_results], indent=2))
    else:
        total = len(all_results)
        healthy = total - unhealthy
        print()
        print("━" * 60)
        print(f"SUMMARY: {healthy}/{total} healthy "
              f"({unhealthy} non-ok across "
              f"{len({r.team for r in all_results})} curators)")
        if unhealthy:
            by_status: dict[str, int] = {}
            for r in all_results:
                if r.status != "ok":
                    by_status[r.status] = by_status.get(r.status, 0) + 1
            print("  " + ", ".join(
                f"{_STATUS_GLYPH[k]} {k}: {v}"
                for k, v in sorted(by_status.items())
            ))

    return unhealthy


def main():
    p = argparse.ArgumentParser(
        description="Probe every curator's SOURCES URLs for reachability."
    )
    p.add_argument("--team", default=None,
                   help="Limit to one team (default: every team with a curator.py)")
    p.add_argument("--timeout", type=int, default=10,
                   help="Per-URL timeout in seconds (default: 10)")
    p.add_argument("--head-only", action="store_true",
                   help="Use HTTP HEAD instead of GET (faster; some sites "
                        "don't support it and will 405)")
    p.add_argument("--json", dest="json_out", action="store_true",
                   help="Emit JSON instead of tabular output")
    args = p.parse_args()

    teams = [args.team] if args.team else _curator_teams()
    if not teams:
        print("No curators found.", file=sys.stderr)
        return 2

    unhealthy = run(teams, args.timeout, args.head_only, args.json_out)
    return min(unhealthy, 125)  # exit code capped at 125


if __name__ == "__main__":
    sys.exit(main())
