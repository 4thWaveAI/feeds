#!/usr/bin/env python3
"""
Build RSS, Atom, and JSON feeds for the Boston Dynamics blog.
Outputs (repo root):
  - boston-dynamics-blog.xml
  - boston-dynamics-blog.atom.xml
  - boston-dynamics-blog.json
"""

import html, json, email.utils, requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime, timezone

# ----- Config -----
INDEX_URL = "https://bostondynamics.com/blog/"
BASE      = "https://bostondynamics.com"
HOME_URL  = "https://bostondynamics.com/blog/"
FEED_BASE = "https://4thwaveai-feeds.github.io/4thwaveai-feeds/"  # change if repo/owner changes

RSS_OUT   = "boston-dynamics-blog.xml"
ATOM_OUT  = "boston-dynamics-blog.atom.xml"
JSON_OUT  = "boston-dynamics-blog.json"

USER_AGENT = "4thWaveAI-Feeds/1.2 (+https://github.com/4thwaveai-feeds/4thwaveai-feeds)"

# ----- Helpers -----
def fetch(url: str) -> str:
    r = requests.get(url, timeout=30, headers={"User-Agent": USER_AGENT})
    r.raise_for_status()
    return r.text

def parse_index(html_text: str, limit: int = 20):
    soup = BeautifulSoup(html_text, "lxml")
    urls, seen = [], set()
    for a in soup.select('a[href^="/blog/"], a[href^="https://bostondynamics.com/blog/"]'):
        full = urljoin(BASE, a.get("href", "").strip())
        if not full or full == INDEX_URL:
            continue
        if full not in seen:
            seen.add(full)
            urls.append(full)
        if len(urls) >= limit:
            break
    return urls

def parse_article(url: str):
    try:
        s = BeautifulSoup(fetch(url), "lxml")

        # Title
        ogt = s.find("meta", property="og:title")
        title = ogt.get("content", "").strip() if ogt else (s.title.get_text(strip=True) if s.title else url)

        # Description
        ogd = s.find("meta", property="og:description")
        if ogd and ogd.get("content"):
            description = ogd["content"].strip()
        else:
            p = s.find("article") or s
            p = p.find("p")
            description = (p.get_text(" ", strip=True) if p else "")[:400]

        # Published time (optional)
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
        return None  # skip silently

def build_rss(items):
    now_rfc = email.utils.format_datetime(datetime.now(timezone.utc))
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0">',
        "  <channel>",
        "    <title>Boston Dynamics Blog — Unofficial RSS</title>",
        f"    <link>{HOME_URL}</link>",
        "    <description>Unofficial feed generated for convenience. Source: Boston Dynamics Blog.</description>",
        "    <language>en-us</language>",
        f"    <lastBuildDate>{now_rfc}</lastBuildDate>",
    ]
    for it in items:
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

def build_atom(items):
    now_rfc = email.utils.format_datetime(datetime.now(timezone.utc))
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<feed xmlns="http://www.w3.org/2005/Atom">',
        "  <title>Boston Dynamics Blog — Unofficial Atom</title>",
        f"  <link href=\"{HOME_URL}\"/>",
        f"  <link rel=\"self\" href=\"{FEED_BASE}{ATOM_OUT}\"/>",
        "  <id>urn:4thwaveai-feeds:boston-dynamics-blog</id>",
        f"  <updated>{now_rfc}</updated>",
    ]
    for it in items:
        parts += [
            "  <entry>",
            f"    <title>{html.escape(it['title'])}</title>",
            f"    <link href=\"{html.escape(it['link'])}\"/>",
            f"    <id>{html.escape(it['guid'])}</id>",
            f"    <summary type=\"html\"><![CDATA[{it['description']}]]></summary>",
        ]
        if it.get("pubDate"):
            parts.append(f"    <updated>{it['pubDate']}</updated>")
        parts += ["  </entry>"]
    parts += ["</feed>"]
    return "\n".join(parts)

def bu
::contentReference[oaicite:0]{index=0}
