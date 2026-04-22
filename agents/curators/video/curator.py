"""video domain knowledge curator"""
import os, sys, argparse, datetime, urllib.request
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from knowledge.knowledge_base import propose_knowledge, PRIORITY_HIGH, PRIORITY_MEDIUM, PRIORITY_LOW

TEAM = "video"

SOURCES = [
    {"name": "YouTube Creator Insider", "url": "https://www.youtube.com/@YouTubeCreatorInsider/videos", "domain": "platform_policies_video", "priority": PRIORITY_HIGH},
    {"name": "TikTok Newsroom", "url": "https://newsroom.tiktok.com/en-us/", "domain": "platform_policies_video", "priority": PRIORITY_HIGH},
    {"name": "Meta Transparency — Advertising", "url": "https://transparency.meta.com/policies/ad-standards/", "domain": "advertising_standards_video", "priority": PRIORITY_HIGH},
    {"name": "YouTube Community Guidelines", "url": "https://support.google.com/youtube/answer/9288567", "domain": "content_guidelines", "priority": PRIORITY_HIGH},
    {"name": "TikTok Community Guidelines", "url": "https://www.tiktok.com/community-guidelines/en/", "domain": "content_guidelines", "priority": PRIORITY_HIGH},
    {"name": "Runway News", "url": "https://runwayml.com/blog", "domain": "ai_video_tools", "priority": PRIORITY_MEDIUM},
    {"name": "Pika Labs News", "url": "https://pika.art/blog", "domain": "ai_video_tools", "priority": PRIORITY_MEDIUM},
    {"name": "OpenAI Sora Updates", "url": "https://openai.com/sora/", "domain": "ai_video_tools", "priority": PRIORITY_MEDIUM},
    {"name": "VidIQ YouTube SEO", "url": "https://vidiq.com/blog/", "domain": "video_seo", "priority": PRIORITY_LOW},
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
