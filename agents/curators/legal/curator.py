"""Legal domain knowledge curator"""
import os, sys, argparse, json, datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from knowledge.knowledge_base import store_knowledge, PRIORITY_HIGH, PRIORITY_CRITICAL, PRIORITY_MEDIUM, PRIORITY_LOW

SOURCES = [
    {"name": "UK Gambling Commission", "url": "https://www.gamblingcommission.gov.uk/news-action-and-statistics/news", "domain": "uk_gambling_regulation", "priority": PRIORITY_HIGH},
    {"name": "FCA Regulation", "url": "https://www.fca.org.uk/news/news-stories", "domain": "financial_promotion", "priority": PRIORITY_HIGH},
    {"name": "ICO GDPR", "url": "https://ico.org.uk/about-the-ico/media-centre/news-and-blogs/", "domain": "data_protection", "priority": PRIORITY_HIGH},
    {"name": "EU GDPR Updates", "url": "https://edpb.europa.eu/news/news_en", "domain": "data_protection", "priority": PRIORITY_MEDIUM},
    {"name": "ASA Gambling Ads", "url": "https://www.asa.org.uk/news/latest-news.html", "domain": "uk_gambling_regulation", "priority": PRIORITY_HIGH},
    {"name": "AGA US Gambling", "url": "https://www.americangaming.org/resources/", "domain": "us_gambling_regulation", "priority": PRIORITY_MEDIUM},
    {"name": "ACMA Australia", "url": "https://www.acma.gov.au/newsroom", "domain": "au_regulation", "priority": PRIORITY_MEDIUM},
]

def fetch_and_store(source: dict, topic: str = None) -> int:
    """Fetch from source URL and store in knowledge base."""
    try:
        import urllib.request
        from html.parser import HTMLParser

        class TextExtractor(HTMLParser):
            def __init__(self):
                super().__init__()
                self.text = []
                self.in_article = False
            def handle_data(self, data):
                if data.strip():
                    self.text.append(data.strip())
            def get_text(self):
                return " ".join(self.text[:100])

        req = urllib.request.Request(
            source["url"],
            headers={"User-Agent": "Mozilla/5.0 Protean-Pursuits-Training-Bot/1.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        parser = TextExtractor()
        parser.feed(html)
        text = parser.get_text()

        if topic and topic.lower() not in text.lower():
            return 0

        if len(text) < 50:
            return 0

        store_knowledge(
            team="legal",
            domain=source["domain"],
            content=text[:2000],
            source=source["name"],
            title=f"{source['name']} — {datetime.date.today()}",
            priority=source["priority"],
            metadata={"url": source["url"], "fetched_at": datetime.datetime.utcnow().isoformat()}
        )
        print(f"  ✅ {source['name']}: stored {len(text)} chars")
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
    print(f"✅ Legal: {stored}/{len(SOURCES)} sources stored")
