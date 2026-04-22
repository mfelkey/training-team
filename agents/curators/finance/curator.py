"""finance domain knowledge curator"""
import os, sys, argparse, datetime, urllib.request
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from knowledge.knowledge_base import propose_knowledge, PRIORITY_HIGH, PRIORITY_MEDIUM, PRIORITY_LOW

TEAM = "finance"

SOURCES = [
    {"name": "SEC EDGAR Filings", "url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent", "domain": "sec_filings", "priority": PRIORITY_HIGH},
    {"name": "SEC Press Releases", "url": "https://www.sec.gov/news/pressreleases", "domain": "sec_filings", "priority": PRIORITY_MEDIUM},
    # FIXME: 403 — FASB bot-blocks our User-Agent. See TODO_URLS.md.
    {"name": "FASB News", "url": "https://www.fasb.org/page/pagecontent?pageId=/news/current.html", "domain": "fasb_standards", "priority": PRIORITY_MEDIUM},
    {"name": "IRS Newsroom", "url": "https://www.irs.gov/newsroom", "domain": "tax_updates", "priority": PRIORITY_MEDIUM},
    {"name": "Bloomberg Tax", "url": "https://news.bloombergtax.com/daily-tax-report/feed", "domain": "tax_updates", "priority": PRIORITY_LOW},
    # FIXME: 401 — Reuters requires paid subscription auth. See TODO_URLS.md.
    {"name": "Reuters Finance", "url": "https://www.reuters.com/business/finance/", "domain": "financial_news", "priority": PRIORITY_LOW},
    {"name": "SaaStr Blog", "url": "https://www.saastr.com/blog/", "domain": "saas_metrics", "priority": PRIORITY_LOW},
    {"name": "OpenView SaaS Metrics", "url": "https://openviewpartners.com/blog/", "domain": "saas_metrics", "priority": PRIORITY_LOW},
    {"name": "Stripe Blog", "url": "https://stripe.com/blog", "domain": "payment_processing", "priority": PRIORITY_MEDIUM},
    # FIXME: 403 — Payments Dive bot-blocks our User-Agent. See TODO_URLS.md.
    {"name": "Payments Dive", "url": "https://www.paymentsdive.com/", "domain": "payment_processing", "priority": PRIORITY_LOW},
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
