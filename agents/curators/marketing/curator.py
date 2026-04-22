"""marketing domain knowledge curator"""
import os, sys, argparse, datetime, urllib.request
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from knowledge.knowledge_base import propose_knowledge, PRIORITY_HIGH, PRIORITY_MEDIUM, PRIORITY_LOW

TEAM = "marketing"

SOURCES_MAP = {
    "marketing": [
        {"name": "Meta Ad Policies", "url": "https://www.facebook.com/policies/ads/", "domain": "platform_policies", "priority": PRIORITY_HIGH},
        # FIXME: 404 — Google restructured /adspolicy/answer/ paths. See TODO_URLS.md.
        {"name": "Google Ads Gambling Policy", "url": "https://support.google.com/adspolicy/answer/6023246", "domain": "gambling_ad_regulation", "priority": PRIORITY_HIGH},
        {"name": "ASA CAP Gambling", "url": "https://www.asa.org.uk/type/non_broadcast/code_section/16.html", "domain": "gambling_ad_regulation", "priority": PRIORITY_HIGH},
        {"name": "Marketing Week", "url": "https://www.marketingweek.com/", "domain": "industry_news", "priority": PRIORITY_LOW},
    ],
    "strategy": [
        {"name": "Sports Betting Market", "url": "https://www.gamblinginsider.com/", "domain": "market_intelligence", "priority": PRIORITY_MEDIUM},
        {"name": "Sports Analytics World", "url": "https://www.sportsanalyticsworld.com/", "domain": "industry_trends", "priority": PRIORITY_MEDIUM},
        {"name": "Crunchbase Sports Tech", "url": "https://www.crunchbase.com/hub/sports-technology-companies", "domain": "competitor_analysis", "priority": PRIORITY_MEDIUM},
    ],
    "design": [
        {"name": "WCAG Updates", "url": "https://www.w3.org/WAI/news/", "domain": "wcag_updates", "priority": PRIORITY_HIGH},
        {"name": "WebAIM Blog", "url": "https://webaim.org/blog/", "domain": "accessibility_law", "priority": PRIORITY_MEDIUM},
        {"name": "Smashing Magazine", "url": "https://www.smashingmagazine.com/articles/", "domain": "ux_research", "priority": PRIORITY_LOW},
    ],
    "qa": [
        {"name": "OWASP News", "url": "https://owasp.org/news/", "domain": "owasp_updates", "priority": PRIORITY_HIGH},
        {"name": "NIST CVE Feed", "url": "https://nvd.nist.gov/vuln/full-listing", "domain": "security_advisories", "priority": PRIORITY_HIGH},
        {"name": "W3C Accessibility", "url": "https://www.w3.org/WAI/news/", "domain": "compliance_standards", "priority": PRIORITY_MEDIUM},
        {"name": "Pytest Releases", "url": "https://github.com/pytest-dev/pytest/releases.atom", "domain": "testing_frameworks", "priority": PRIORITY_LOW},
    ],
}

SOURCES = SOURCES_MAP.get(TEAM, [])

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
