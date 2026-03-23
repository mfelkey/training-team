"""Dev domain knowledge curator"""
import os, sys, argparse, json, datetime, urllib.request
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from knowledge.knowledge_base import store_knowledge, PRIORITY_HIGH, PRIORITY_CRITICAL, PRIORITY_MEDIUM, PRIORITY_LOW

SOURCES = [
    {"name": "FastAPI Releases", "url": "https://github.com/tiangolo/fastapi/releases.atom", "domain": "framework_releases", "priority": PRIORITY_HIGH},
    {"name": "React Releases", "url": "https://github.com/facebook/react/releases.atom", "domain": "framework_releases", "priority": PRIORITY_MEDIUM},
    {"name": "PostgreSQL News", "url": "https://www.postgresql.org/about/newsarchive/", "domain": "framework_releases", "priority": PRIORITY_MEDIUM},
    {"name": "OWASP Top 10", "url": "https://owasp.org/www-project-top-ten/", "domain": "security_vulnerabilities", "priority": PRIORITY_HIGH},
    {"name": "CVE Critical Python", "url": "https://cve.mitre.org/cgi-bin/cvekey.cgi?keyword=python", "domain": "security_vulnerabilities", "priority": PRIORITY_CRITICAL},
    {"name": "Node Security", "url": "https://nodejs.org/en/blog/vulnerability/", "domain": "security_vulnerabilities", "priority": PRIORITY_HIGH},
    {"name": "CrewAI Releases", "url": "https://github.com/crewAIInc/crewAI/releases.atom", "domain": "framework_releases", "priority": PRIORITY_HIGH},
]

def fetch_and_store(source: dict, topic: str = None) -> int:
    try:
        from html.parser import HTMLParser
        class TextExtractor(HTMLParser):
            def __init__(self):
                super().__init__()
                self.text = []
            def handle_data(self, data):
                if data.strip():
                    self.text.append(data.strip())
            def get_text(self):
                return " ".join(self.text[:150])

        req = urllib.request.Request(
            source["url"],
            headers={"User-Agent": "Mozilla/5.0 Protean-Pursuits-Training-Bot/1.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        parser = TextExtractor()
        parser.feed(html)
        text = parser.get_text()
        if len(text) < 50:
            return 0
        store_knowledge(
            team="dev", domain=source["domain"],
            content=text[:2000], source=source["name"],
            title=f"{source['name']} — {datetime.date.today()}",
            priority=source["priority"],
            metadata={"url": source["url"], "fetched_at": datetime.datetime.utcnow().isoformat()}
        )
        print(f"  ✅ {source['name']}: stored")
        return 1
    except Exception as e:
        print(f"  ⚠️  {source['name']}: {e}")
        return 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", type=str, default=None)
    args = parser.parse_args()
    print(f"\n🎓 Dev Curator — {datetime.date.today()}")
    stored = sum(fetch_and_store(s, args.topic) for s in SOURCES)
    print(f"✅ Dev: {stored}/{len(SOURCES)} sources stored")
