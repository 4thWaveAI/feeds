#!/usr/bin/env python3
import os, html, email.utils, requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime, timezone

INDEX_URL = "https://bostondynamics.com/blog/"
BASE = "https://bostondynamics.com"
OUTFILE = "boston_dynamics_blog_unofficial.rss.xml"
USER_AGENT = "4thWaveAI-RSS/1.0 (+https://github.com/4thwaveai-feeds/4thwaveai-feeds)"

def fetch(url):
    r = requests.get(url, timeout=30, headers={"User-Agent": USER_AGENT})
    r.raise_for_status()
    return r.text

def parse_index(html_text, limit=20):
    soup = BeautifulSoup(html_text, "lxml")
    urls = []
    for a in soup.select("a[href]"):
        href = a["href"]
        if href.startswith("/blog/") or href.startswith("https://bostondynamics.com/blog/"):
            full = urljoin(BASE, href)
            if full not in urls:
                urls.append(full)
        if len(urls) >= limit:
            break
    return urls

def parse_article(url):
    try:
        html_text = fetch(url)
        s = BeautifulSoup(html_text, "lxml")
        title = s.find("meta", property="og:title")
        title = (title["content"].strip() if title and title.get("content")
                 else (s.title.get_text(strip=True) if s.title else url))
        desc = s.find("meta", property="og:description")
        if desc and desc.get("content"):
            description = desc["content"].strip()
        else:
            p = s.find("p")
            description = (p.get_text(" ", strip=True) if p else "")[:400]
        pub = s.find("meta", property="article:published_time")
        pubDate = None
        if pub and pub.get("content"):
            try:
                dt = datetime.fromisoformat(pub["content"].replace("Z", "+00:00"))
                pubDate = email.utils.format_datetime(dt)
            except Exception:
                pubDate = None
        return {"title": title, "link": url, "guid": url, "description": description, "pubDate": pubDate}
    except Exception:
        return None  # skip article on error

def build_rss(items):
    now_rfc = email.utils.format_datetime(datetime.now(timezone.utc))
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0">',
        "  <channel>",
        "    <title>Boston Dynamics Blog — Unofficial RSS</title>",
        "    <link>https://bostondynamics.com/blog/</link>",
        "    <description>Unofficial feed generated for convenience. Source: Boston Dynamics Blog.</description>",
        "    <language>en-us</language>",
        f"    <lastBuildDate>{now_rfc}</lastBuildDate>",
    ]
    for it in items:
        if not it:
            continue
        parts += [
            "    <item>",
            f"      <title>{html.escape(it['title'])}</title>",
            f"      <link>{html.escape(it['link'])}</link>",
            f"      <guid isPermaLink=\"true\">{html.escape(it['guid'])}</guid>",
            f"      <description><![CDATA[{it['description']}]]></description>",
        ]
        if it.get("pubDate"):
            parts.append(f"      <pubDate>{it['pubDate']}</pubDate>")
        parts += ["    </item>"]
    parts += ["  </channel>", "</rss>"]
    return "\n".join(parts)

def main():
    try:
        idx = fetch(INDEX_URL)
        urls = parse_index(idx, limit=20)
        articles = [parse_article(u) for u in urls]
        items = [a for a in articles if a]
        if not items:
            print("No items parsed; leaving previous file untouched.")
            return
        rss_xml = build_rss(items)
        with open(OUTFILE, "w", encoding="utf-8") as f:
            f.write(rss_xml)
        print(f"Wrote {OUTFILE} with {len(items)} items.")
    except Exception as e:
        print(f"Build failed: {e}")

if __name__ == "__main__":
    main()
