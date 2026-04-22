"""hr domain knowledge curator"""
import os, sys, argparse, datetime, urllib.request
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from knowledge.knowledge_base import propose_knowledge, PRIORITY_HIGH, PRIORITY_MEDIUM, PRIORITY_LOW

TEAM = "hr"

SOURCES = [
    {"name": "DOL Newsroom", "url": "https://www.dol.gov/newsroom", "domain": "employment_law_us", "priority": PRIORITY_HIGH},
    {"name": "EEOC Newsroom", "url": "https://www.eeoc.gov/newsroom", "domain": "employment_law_us", "priority": PRIORITY_HIGH},
    {"name": "SHRM HR News", "url": "https://www.shrm.org/topics-tools/news", "domain": "employment_law_us", "priority": PRIORITY_MEDIUM},
    {"name": "EU-OSHA News", "url": "https://osha.europa.eu/en/highlights", "domain": "employment_law_intl", "priority": PRIORITY_MEDIUM},
    # FIXME: returns 403 to our User-Agent — paywall/bot-block. See TODO_URLS.md.
    {"name": "ILO Newsroom", "url": "https://www.ilo.org/global/about-the-ilo/newsroom/news/lang--en/index.htm", "domain": "employment_law_intl", "priority": PRIORITY_MEDIUM},
    {"name": "Radford / Aon Benchmarks", "url": "https://radford.aon.com/insights", "domain": "compensation_benchmarks", "priority": PRIORITY_LOW},
    # Removed 2026-04-22: Payscale Compensation Today URL returns 404 (site restructured).
    # FIXME: URL 404s — search for new SHRM Benefits index. See TODO_URLS.md.
    {"name": "SHRM Benefits", "url": "https://www.shrm.org/topics-tools/tools/benefits", "domain": "benefits_updates", "priority": PRIORITY_MEDIUM},
    {"name": "HR Executive", "url": "https://hrexecutive.com/", "domain": "hr_tech", "priority": PRIORITY_LOW},
    {"name": "Gallup Workplace", "url": "https://www.gallup.com/workplace/", "domain": "culture_research", "priority": PRIORITY_LOW},
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
