#!/usr/bin/env python3
"""
Pharma news fetcher — runs in GitHub Actions every 6 hours.
Saves results to data/news.json (served as static file from GitHub Pages).
No CORS issues since the frontend fetches from the same domain.
"""
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ShMoPharmaBot/1.0)"}
MAX_PER_SOURCE = 20

# ── News sources ──────────────────────────────────────────────────────────────
# English: direct RSS feeds
# Korean: Google News RSS (site: 검색) — 직접 RSS URL이 없는 경우
SOURCES = [
    {
        "name": "Biopharma Dive",
        "url":  "https://www.biopharmadive.com/feeds/news",
        "lang": "en",
    },
    {
        "name": "Fierce Pharma",
        "url":  "https://www.fiercepharma.com/rss/news",
        "lang": "en",
    },
    {
        "name": "Endpoints News",
        "url":  "https://endpts.com/feed/",
        "lang": "en",
    },
    {
        "name": "STAT News",
        "url":  "https://www.statnews.com/feed/",
        "lang": "en",
    },
    # 한국어 소스 — Google News 한국어 RSS (index.html fallback 과 동일한 URL)
    {
        "name": "데일리팜",
        "url":  "https://news.google.com/rss/search?q=site:dailypharm.com+제약&hl=ko&gl=KR&ceid=KR:ko",
        "lang": "ko",
    },
    {
        "name": "약업신문",
        "url":  "https://news.google.com/rss/search?q=site:yakup.com+제약&hl=ko&gl=KR&ceid=KR:ko",
        "lang": "ko",
    },
    {
        "name": "의학신문",
        "url":  "https://news.google.com/rss/search?q=site:mdtoday.co.kr+의약&hl=ko&gl=KR&ceid=KR:ko",
        "lang": "ko",
    },
]


def strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()


def fetch_rss(source: dict) -> list[dict]:
    url  = source["url"]
    name = source["name"]
    try:
        req = Request(url, headers=HEADERS)
        with urlopen(req, timeout=15) as resp:
            raw = resp.read()
    except (URLError, OSError) as e:
        print(f"  ✗ {name}: {e}")
        return []

    # Feedparser handles RSS 1.0/2.0 and Atom
    try:
        import feedparser
        feed = feedparser.parse(raw)
        articles = []
        for entry in feed.entries[:MAX_PER_SOURCE]:
            title   = strip_html(entry.get("title", "")).strip()
            link    = entry.get("link", "").strip()
            summary = strip_html(entry.get("summary", entry.get("description", "")))[:250]
            pub     = entry.get("published", entry.get("updated", ""))[:16]
            if title and link:
                articles.append({
                    "title":          title,
                    "link":           link,
                    "source":         name,
                    "published_date": pub or "Recent",
                    "snippet":        summary,
                })
        print(f"  ✓ {name}: {len(articles)} articles")
        return articles
    except Exception as e:
        print(f"  ✗ {name} parse error: {e}")
        return []


def main():
    print(f"[{datetime.now(timezone.utc).isoformat()}] Fetching pharma news...")
    all_articles = []

    for src in SOURCES:
        articles = fetch_rss(src)
        all_articles.extend(articles)
        time.sleep(1)   # polite delay between requests

    output = {
        "updated":  datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count":    len(all_articles),
        "articles": all_articles,
    }

    out_path = Path(__file__).parent.parent / "data" / "news.json"
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Saved {len(all_articles)} articles → {out_path}")


if __name__ == "__main__":
    main()
