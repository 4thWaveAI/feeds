#!/usr/bin/env python3
"""
Builds aggregated feeds per area from feeds.yaml

Outputs:
  /feeds/<area>.xml
  /feeds/<area>.atom.xml
  /feeds/<area>.json
Also writes:
  /index.html  (auto-lists all areas)

Safe XML, no raw CDATA; validates before finish.
"""

import os, re, html, json, yaml, requests, email.utils
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from datetime import datetime, timezone
from pathlib import Path

# ---------- Paths & config ----------
ROOT    = Path(__file__).resolve().parents[1]
CONFIG  = ROOT / "feeds.yaml"
OUTDIR  = ROOT / "feeds"
OUTDIR.mkdir(parents=True, exist_ok=True)

# ---------- HTTP ----------
HEADERS = {
    "User-Agent": "4thWaveAI Feeds Bot/1.0 (+https://4thwave.ai)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.7",
    "Connection": "keep-alive",
    "Cache-Control": "no-cache",
}
def fetch(url: str, timeout: int = 30) -> str:
    r = requests.get(url, timeout=timeout, headers=HEADERS)
    r.raise_for_status()
    # Force sensible decode (prevents garbled bytes like I�Z�…)
    r.encoding = r.apparent_encoding or "utf-8"
    return r.text

# ---------- Text & XML safety ----------
_CONTROL = re.compile(r'[\x00-\x08\x0B\x0C\x0E-\x1F]')
def _clean(s):
    if s is None:
        return ""
    if isinstance(s, bytes):
        s = s.decode("utf-8", "replace")
    s = s.replace("\ufeff", "")           # strip BOM
    return _CONTROL.sub("", s)

def xml_text(s: str) -> str:
    return html.escape(_clean(s), quote=True)

# Only use if you *must* keep HTML in <description>
def cdata_safe(s: str) -> str:
    s = _clean(s).replace("]]>", "]]]]><![CDATA[>")
    return f"<![CDATA[{s}]]>"

TAG = re.compile(r"<[^>]+>")
def strip_tags(html_str: str) -> str:
    return TAG.sub("", html_str or "")

# ---------- Link picking ----------
def pick_links(index_html: str, base: str, preferred_prefix: str | None, limit: int = 20) -> list[str]:
    soup = BeautifulSoup(index_html, "lxml")
    host = urlparse(base).netloc
    seen, out = set(), []

    def add(href: str | None):
        if not href: return
        full = urljoin(base, href.strip())
        if urlparse(full).netloc != host: return
        if full in seen: return
        seen.add(full); out.append(full)

    # 1) Preferred prefix (can be abs or rel)
    if preferred_prefix:
        # try absolute first, then relative
        for a in soup.select(f'a[href^="{preferred_prefix}"]'):
            add(a.get("href"));  0
            if len(out) >= limit: return out
        if preferred_prefix.startswith("/"):
            for a in soup.select(f'a[href^="{preferred_prefix}"]'):
                add(a.get("href"))
                if len(out) >= limit: return out

    # 2) Domain fallbacks
    patterns = []
    if "nanowerk.com" in host: patterns += ["/news2/"]
    if "phys.org" in host:     patterns += ["/news/"]
    if "sciencedaily.com" in host: patterns += ["/releases/"]
    if "news.mit.edu" in host or "berkeley.edu" in host: patterns += ["/20"]  # /2025/...

    for p in patterns:
        for a in soup.select(f'a[href^="{p}"]'):
            add(a.get("href"))
            if len(out) >= limit: return out

    # 3) Generic fallback
    for a in soup.select("a[href]"):
        href = a.get("href", "")
        if any(k in href for k in ("/news/", "/story/", "/releases/", "/202", "/20", "/blog/")):
            add(href)
            if len(out) >= limit: break

    return out[:limit]

# ---------- Article parsing ----------
def parse_article(url: str) -> dict | None:
    try:
        s  = BeautifulSoup(fetch(url), "lxml")
        # Title
        ogt = s.find("meta", property="og:title")
        title = (ogt.get("content") or "").strip() if ogt else (s.title.get_text(strip=True) if s.title else url)
        title = _clean(title)

        # Description (prefer og:description, else first paragraph)
        ogd = s.find("meta", property="og:description")
        if ogd and ogd.get("content"):
            descr = ogd["content"].strip()
        else:
            p = (s.find("article") or s).find("p")
            descr = p.get_text(" ", strip=True) if p else ""
        descr = _clean(descr)
        if not descr:
            descr = title
        descr = descr[:800]

        # Pub date (optional)
        pubDate = None
        pub = s.find("meta", property="article:published_time")
        if pub and pub.get("content"):
            try:
                dt = datetime.fromisoformat(pub["content"].replace("Z", "+00:00"))
                pubDate = email.utils.format_datetime(dt)
            except Exception:
                pubDate = None

        return {"title": title, "link": url, "guid": url, "description": descr, "pubDate": pubDate}
    except Exception as e:
        print(f"Skip {url}: {e}")
        return None

# ---------- Writers ----------
def build_rss(items: list[dict], title: str, home_url: str) -> str:
    now_rfc = email.utils.format_datetime(datetime.now(timezone.utc))
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0">',
        "  <channel>",
        f"    <title>{xml_text(title)}</title>",
        f"    <link>{xml_text(home_url)}</link>",
        f"    <description>{xml_text('Aggregated feed generated by 4thWave AI.')}</description>",
        "    <language>en-us</language>",
        f"    <lastBuildDate>{now_rfc}</lastBuildDate>",
    ]
    for it in items:
        parts += [
            "    <item>",
            f"      <title>{xml_text(it['title'])}</title>",
            f"      <link>{xml_text(it['link'])}</link>",
            f"      <guid isPermaLink=\"true\">{xml_text(it['guid'])}</guid>",
            # safest: plain text (no CDATA)
            f"      <description>{xml_text(it['description'])}</description>",
        ]
        if it.get("pubDate"):
            parts.append(f"      <pubDate>{xml_text(it['pubDate'])}</pubDate>")
        parts += ["    </item>"]
    parts += ["  </channel>", "</rss>"]
    return "\n".join(parts)

def build_atom(items: list[dict], title: str, self_url: str, home_url: str, feed_id: str) -> str:
    now_rfc = email.utils.format_datetime(datetime.now(timezone.utc))
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<feed xmlns="http://www.w3.org/2005/Atom">',
        f"  <title>{xml_text(title)}</title>",
        f"  <link href=\"{xml_text(home_url)}\"/>",
        f"  <link rel=\"self\" href=\"{xml_text(self_url)}\"/>",
        f"  <id>{xml_text(feed_id)}</id>",
        f"  <updated>{now_rfc}</updated>",
    ]
    for it in items:
        parts += [
            "  <entry>",
            f"    <title>{xml_text(it['title'])}</title>",
            f"    <link href=\"{xml_text(it['link'])}\"/>",
            f"    <id>{xml_text(it['guid'])}</id>",
            # safest: text summary
            f"    <summary type=\"text\">{xml_text(it['description'])}</summary>",
        ]
        if it.get("pubDate"):
            parts.append(f"    <updated>{xml_text(it['pubDate'])}</updated>")
        parts += ["  </entry>"]
    parts += ["</feed>"]
    return "\n".join(parts)

def build_json(items: list[dict], title: str, self_url: str, home_url: str) -> str:
    feed = {
        "version": "https://jsonfeed.org/version/1",
        "title": title,
        "home_page_url": home_url,
        "feed_url": self_url,
        "items": []
    }
    for it in items:
        feed["items"].append({
            "id": it["guid"],
            "url": it["link"],
            "title": it["title"],
            "content_text": _clean(it["description"])
        })
    return json.dumps(feed, ensure_ascii=False, indent=2)

def validate_xml(path: Path):
    ET.parse(path)  # raises if invalid

# ---------- Homepage generator ----------
def build_index_html(areas: list[str], site_base: str):
    def row(slug: str) -> str:
        return (f'  <li>{slug.replace("-", " ").title()} — '
                f'<a href="feeds/{slug}.xml">RSS</a> <span class="sep">·</span> '
                f'<a href="feeds/{slug}.atom.xml">Atom</a> <span class="sep">·</span> '
                f'<a href="feeds/{slug}.json">JSON</a></li>')
    html_doc = f"""<!doctype html>
<meta charset="utf-8">
<title>4thWave AI Feeds</title>
<style>
  body {{ max-width: 860px; margin: 3rem auto; font: 16px/1.5 system-ui,-apple-system,Segoe UI,Roboto,Helvetica Neue,Arial,Noto Sans,Apple Color Emoji,Segoe UI Emoji; }}
  h1{{font-size:2.2rem;margin-bottom:.5rem}} h2{{margin-top:2.0rem}} ul{{margin:.5rem 0 1.25rem 1rem}}
  li{{margin:.25rem 0}} .sep{{opacity:.6}}
</style>
<h1>4thWave AI Feeds</h1>
<ul>
  <li><a href="feeds/all.xml">RSS 2.0 (all)</a> <span class="sep">·</span> <a href="feeds/all.atom.xml">Atom</a> <span class="sep">·</span> <a href="feeds/all.json">JSON</a></li>
</ul>
<h2>Area Feeds</h2>
<ul>
{chr(10).join(row(a) for a in sorted(areas))}
</ul>
"""
    (ROOT / "index.html").write_text(html_doc, encoding="utf-8", newline="\n")

# ---------- Main ----------
def main():
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    site_base = cfg.get("site_base", "https://4thwaveai-feeds.github.io/4thwaveai-feeds/")
    home_url  = cfg.get("home_url", "https://4thwave.ai")
    max_items = cfg.get("max_items_per_area", 60)

    all_items_for_all = []  # for optional global "all" feed
    areas_cfg = cfg.get("areas", {})
    written_areas = []

    for area_slug, sources in areas_cfg.items():
        collected = []
        for src in sources:
            try:
                idx_html = fetch(src["index"])
                links = pick_links(idx_html, src["base"], src.get("prefix"), limit=src.get("limit", 10))
                for u in links:
                    it = parse_article(u)
                    if it: collected.append(it)
            except Exception as e:
                print(f"[{area_slug}] source failed: {src.get('name', src.get('base', ''))} -> {e}")

        # de-dup by guid/link
        seen, unique = set(), []
        for it in collected:
            gid = it["guid"]
            if gid in seen: continue
            seen.add(gid)
            unique.append(it)

        if not unique:
            print(f"[{area_slug}] no items, skipping write (preserve previous files)")
            continue

        unique = unique[:max_items]
        written_areas.append(area_slug)
        all_items_for_all.extend(unique)

        title = f"4thWave AI — {area_slug.replace('-', ' ').title()} (Aggregated)"

        rss_path  = OUTDIR / f"{area_slug}.xml"
        atom_path = OUTDIR / f"{area_slug}.atom.xml"
        json_path = OUTDIR / f"{area_slug}.json"

        rss_xml  = build_rss(unique, title, home_url)
        atom_xml = build_atom(unique, title, site_base + f"feeds/{area_slug}.atom.xml", home_url, f"urn:4thwaveai-feeds:{area_slug}")
        json_txt = build_json(unique, title, site_base + f"feeds/{area_slug}.json", home_url)

        rss_path.write_text(rss_xml,  encoding="utf-8", newline="\n")
        atom_path.write_text(atom_xml, encoding="utf-8", newline="\n")
        json_path.write_text(json_txt, encoding="utf-8", newline="\n")

        # validate
        validate_xml(rss_path)
        validate_xml(atom_path)

        print(f"[{area_slug}] wrote {len(unique)} items")

    # Optional global "all" feeds (concat all areas)
    if all_items_for_all:
        # de-dup again globally by guid
        seen, global_items = set(), []
        for it in all_items_for_all:
            gid = it["guid"]
            if gid in seen: continue
            seen.add(gid)
            global_items.append(it)
        global_items = global_items[: max_items]

        title_all = "4thWave AI — All Areas (Aggregated)"
        (OUTDIR / "all.xml").write_text(build_rss(global_items, title_all, home_url), encoding="utf-8", newline="\n")
        (OUTDIR / "all.atom.xml").write_text(
            build_atom(global_items, title_all, site_base + "feeds/all.atom.xml", home_url, "urn:4thwaveai-feeds:all"),
            encoding="utf-8", newline="\n")
        (OUTDIR / "all.json").write_text(
            build_json(global_items, title_all, site_base + "feeds/all.json", home_url),
            encoding="utf-8", newline="\n")
        validate_xml(OUTDIR / "all.xml"); validate_xml(OUTDIR / "all.atom.xml")
        print(f"[all] wrote {len(global_items)} items")

    # Homepage
    build_index_html(written_areas, site_base)
    print(f"Homepage index.html updated with {len(written_areas)} areas")

if __name__ == "__main__":
    main()
