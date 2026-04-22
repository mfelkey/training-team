"""sme domain knowledge curator"""
import os, sys, argparse, datetime, urllib.request
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from knowledge.knowledge_base import propose_knowledge, PRIORITY_HIGH, PRIORITY_MEDIUM, PRIORITY_LOW

TEAM = "sme"

SOURCES = [
    # FIXME: returns 403 to our User-Agent. Important SME source. See TODO_URLS.md.
    {"name": "Legal Sports Report", "url": "https://www.legalsportsreport.com/news/", "domain": "sports_betting", "priority": PRIORITY_HIGH},
    # Removed 2026-04-22: Covers /sports URL 404s and the site has restructured.
    {"name": "ESPN FC", "url": "https://www.espn.com/soccer/", "domain": "world_football", "priority": PRIORITY_MEDIUM},
    {"name": "Football Benchmark", "url": "https://www.footballbenchmark.com/library", "domain": "world_football", "priority": PRIORITY_LOW},
    {"name": "NBA.com News", "url": "https://www.nba.com/news", "domain": "nba_ncaa_basketball", "priority": PRIORITY_MEDIUM},
    # Removed 2026-04-22: NCAA MBB news URL 404s. NBA.com covers college in March.
    {"name": "NFL.com News", "url": "https://www.nfl.com/news/", "domain": "nfl_ncaa_football", "priority": PRIORITY_MEDIUM},
    # Removed 2026-04-22: NCAA FB news URL 404s. Use ESPN or SI as replacement later.
    {"name": "MLB.com News", "url": "https://www.mlb.com/news", "domain": "mlb", "priority": PRIORITY_MEDIUM},
    {"name": "NHL.com News", "url": "https://www.nhl.com/news", "domain": "nhl_ncaa_hockey", "priority": PRIORITY_MEDIUM},
    {"name": "MMA Junkie", "url": "https://mmajunkie.usatoday.com/", "domain": "mma", "priority": PRIORITY_MEDIUM},
    {"name": "ATP Tour News", "url": "https://www.atptour.com/en/news", "domain": "tennis", "priority": PRIORITY_MEDIUM},
    {"name": "World Rugby News", "url": "https://www.world.rugby/news", "domain": "world_rugby", "priority": PRIORITY_LOW},
    # FIXME: returns 403. Major cricket source. See TODO_URLS.md.
    {"name": "ESPN Cricinfo", "url": "https://www.espncricinfo.com/", "domain": "cricket", "priority": PRIORITY_MEDIUM},
    {"name": "WNBA.com News", "url": "https://www.wnba.com/news/", "domain": "wnba_ncaa_womens_basketball", "priority": PRIORITY_MEDIUM},
    # FIXME: returns 403. Key thoroughbred source. See TODO_URLS.md.
    {"name": "Paulick Report", "url": "https://paulickreport.com/news/", "domain": "thoroughbred_horse_racing", "priority": PRIORITY_MEDIUM},
    {"name": "Harness Racing Update", "url": "https://harnessracingupdate.com/", "domain": "harness_racing", "priority": PRIORITY_LOW},
    {"name": "BoxingScene", "url": "https://www.boxingscene.com/news", "domain": "mens_boxing", "priority": PRIORITY_MEDIUM},
    {"name": "PGA Tour News", "url": "https://www.pgatour.com/news", "domain": "pga", "priority": PRIORITY_MEDIUM},
    {"name": "LPGA News", "url": "https://www.lpga.com/news", "domain": "lpga", "priority": PRIORITY_MEDIUM},
]


def fetch_and_store(source, topic=None):
    try:
        from html.parser import HTMLParser
        class TextExtractor(HTMLParser):
            def __init__(self):
                super().__init__()
                self.text = []
            def handle_data(self, data):
                if data.strip(): self.text.append(data.strip())
            def get_text(self): return " ".join(self.text[:150])
        req = urllib.request.Request(source["url"],
            headers={"User-Agent": "Mozilla/5.0 Protean-Pursuits-Training-Bot/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        parser = TextExtractor()
        parser.feed(html)
        text = parser.get_text()
        if len(text) < 50: return 0
        propose_knowledge(team=TEAM, domain=source["domain"],
            content=text[:2000], source=source["name"],
            title=f"{source['name']} — {datetime.date.today()}",
            priority=source["priority"],
            metadata={"url": source["url"], "fetched_at": datetime.datetime.utcnow().isoformat()})
        print(f"  ✅ {source['name']}: proposed (pending HITL approval)")
        return 1
    except Exception as e:
        print(f"  ⚠️  {source['name']}: {e}")
        return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", type=str, default=None)
    args = parser.parse_args()
    print(f"\n🎓 {TEAM.title()} Curator — {datetime.date.today()}")
    stored = sum(fetch_and_store(s, args.topic) for s in SOURCES)
    print(f"✅ {TEAM}: {stored}/{len(SOURCES)} sources proposed (pending HITL approval)")
