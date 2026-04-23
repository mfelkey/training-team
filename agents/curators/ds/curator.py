"""DS domain knowledge curator"""
import os, sys, argparse, datetime, urllib.request
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from knowledge.knowledge_base import propose_knowledge, PRIORITY_HIGH, PRIORITY_MEDIUM, PRIORITY_LOW

SOURCES = [
    {"name": "arXiv Soccer Analytics RSS", "url": "https://arxiv.org/search/?searchtype=all&query=soccer+xG+expected+goals&start=0&order=-announced_date_first", "domain": "xg_modeling", "priority": PRIORITY_HIGH},
    {"name": "StatsBomb Articles", "url": "https://statsbomb.com/articles/", "domain": "xg_modeling", "priority": PRIORITY_HIGH},
    {"name": "Open-Meteo Docs", "url": "https://open-meteo.com/en/docs", "domain": "data_providers", "priority": PRIORITY_HIGH},
    {"name": "Football Data API", "url": "https://www.football-data.org/documentation/quickstart", "domain": "data_providers", "priority": PRIORITY_MEDIUM},
    {"name": "Scikit-learn Releases", "url": "https://scikit-learn.org/stable/whats_new.html", "domain": "ml_techniques", "priority": PRIORITY_LOW},
    {"name": "WC2026 FIFA Updates", "url": "https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/news", "domain": "xg_modeling", "priority": PRIORITY_HIGH},
    {"name": "Scikit-learn Calibration Docs", "url": "https://scikit-learn.org/stable/modules/calibration.html", "domain": "ml_techniques", "priority": PRIORITY_HIGH},
    {"name": "NannyML Docs", "url": "https://www.nannyml.com/", "domain": "ml_techniques", "priority": PRIORITY_MEDIUM},
    {"name": "Evidently AI Docs", "url": "https://www.evidentlyai.com/", "domain": "ml_techniques", "priority": PRIORITY_MEDIUM},
    # FIXME: 403 — fbref.com bot-blocks our User-Agent. See TODO_URLS.md.
    {"name": "Sports Reference Soccer", "url": "https://fbref.com/en/", "domain": "soccer_analytics", "priority": PRIORITY_MEDIUM},
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
            headers={"User-Agent": "Mozilla/5.0 (compatible; research-bot/1.0)"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        parser = TextExtractor()
        parser.feed(html)
        text = parser.get_text()
        if len(text) < 50: return 0
        propose_knowledge(team="ds", domain=source["domain"],
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
    print(f"\n🎓 DS Curator — {datetime.date.today()}")
    stored = sum(fetch_and_store(s, args.topic) for s in SOURCES)
    print(f"✅ DS: {stored}/{len(SOURCES)} sources proposed (pending HITL approval)")
