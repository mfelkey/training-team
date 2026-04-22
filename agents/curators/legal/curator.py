"""Legal domain knowledge curator"""
import os, sys, argparse, datetime, urllib.request
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from knowledge.knowledge_base import propose_knowledge, PRIORITY_HIGH, PRIORITY_CRITICAL, PRIORITY_MEDIUM, PRIORITY_LOW

SOURCES = [
    {"name": "UK Gambling Commission News", "url": "https://www.gamblingcommission.gov.uk/news-action-and-statistics/news", "domain": "uk_gambling_regulation", "priority": PRIORITY_HIGH},
    {"name": "FCA Press Releases", "url": "https://www.fca.org.uk/news/press-releases", "domain": "financial_promotion", "priority": PRIORITY_HIGH},
    {"name": "ICO News", "url": "https://ico.org.uk/about-the-ico/media-centre/news-and-blogs/", "domain": "data_protection", "priority": PRIORITY_HIGH},
    {"name": "EDPB News", "url": "https://edpb.europa.eu/news/news_en", "domain": "data_protection", "priority": PRIORITY_MEDIUM},
    {"name": "CAP Code Gambling", "url": "https://www.asa.org.uk/codes-and-rulings/advertising-codes/non-broadcast-code.html", "domain": "uk_gambling_regulation", "priority": PRIORITY_HIGH},
    {"name": "IAGR Global Gambling", "url": "https://iagr.org/news/", "domain": "us_gambling_regulation", "priority": PRIORITY_MEDIUM},
    {"name": "ACMA Gambling", "url": "https://www.acma.gov.au/gambling", "domain": "au_regulation", "priority": PRIORITY_MEDIUM},
    {"name": "GamblingCompliance", "url": "https://www.gamblingcommission.gov.uk/licensees-and-businesses/guide/page/licence-conditions-and-codes-of-practice", "domain": "uk_gambling_regulation", "priority": PRIORITY_HIGH},
]

def fetch_and_store(source: dict, topic: str = None) -> int:
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
        propose_knowledge(team="legal", domain=source["domain"],
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
    print(f"\n🎓 Legal Curator — {datetime.date.today()}")
    stored = sum(fetch_and_store(s, args.topic) for s in SOURCES)
    print(f"✅ Legal: {stored}/{len(SOURCES)} sources proposed (pending HITL approval)")
