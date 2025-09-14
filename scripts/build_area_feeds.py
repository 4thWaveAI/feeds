#!/usr/bin/env python3
"""
Build aggregated feeds per area from feeds.yaml

Outputs:
  feeds/<area>.xml
  feeds/<area>.atom.xml
  feeds/<area>.json
  feeds/all.(xml|atom.xml|json)            # optional if items exist
  feeds/videos.(xml|atom.xml|json)         # optional if items exist
  feeds/tech-leaders.(xml|atom.xml|json)   # optional if items exist

Also writes:
  index.html (auto lists all areas + All + Videos + Tech Leaders when present)

Notes:
- Safe XML (escaped). No brittle CDATA.
- Media: adds <enclosure> for image/video when available.
- Robust HTTP with retries/backoff. Canonicalizes URLs (strips UTM/fbclid).
- NEW: Can ingest sources that are RSS/Atom feeds (set mode: "rss" in feeds.yaml,
       or use an index URL ending in .xml, or if content looks like <rss>/<feed>).
"""

import re, html, json, yaml, requests, email.utils, xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlunparse, parse_qsl, urlencode
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, List
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ---------- Paths & config ----------
ROOT    = Path(__file__).resolve().parents[1]
CONFIG  = ROOT / "feeds.yaml"
OUTDIR  = ROOT / "feeds"
OUTDIR.mkdir(parents=True, exist_ok=True)

# ---------- HTTP (session with retries) ----------
HEADERS = {
    "User-Agent": "4thWaveAI Feeds Bot/1.0 (+https://4thwave.ai)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.7",
    "Connection": "keep-alive",
    "Cache-Control": "no-cache",
}

_session = requests.Session()
_retry = Retry(
    total=3,
    backoff_factor=1.0,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=frozenset(["GET"]),
    raise_on_status=False,
)
_session.mount("http://", HTTPAdapter(max_retries=_retry))
_session.mount("https://", HTTPAdapter(max_retries=_retry))

def fetch(url: str, timeout: int = 30) -> str:
    r = _session.get(url, timeout=timeout, headers=HEADERS)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    return r.text

# ---------- URL helpers ----------
STRIP_QS = {"utm_source","utm_medium","utm_campaign","utm_term","utm_content","utm_id",
            "fbclid","gclid","mc_cid","mc_eid","igshid","si","ref","ref_src"}

def canon_url(u: str) -> str:
    try:
        p = urlparse(u)
        if not p.scheme:
            return u
        q = [(k,v) for k,v in parse_qsl(p.query, keep_blank_values=True) if k.lower() not in STRIP_QS]
        p = p._replace(query=urlencode(q), fragment="")
        return urlunparse(p)
    except Exception:
        return u

def abs_url(base: str, maybe_rel: Optional[str]) -> Optional[str]:
    if not maybe_rel:
        return None
    full = urljoin(base, maybe_rel.strip())
    return canon_url(full)
  
def write_empty_feeds(area_slug: str, title: str, site_base: str, home_url: str):
    """Create empty-but-valid RSS/Atom/JSON for new areas that currently have 0 items."""
    rss_path  = OUTDIR / f"{area_slug}.xml"
    atom_path = OUTDIR / f"{area_slug}.atom.xml"
    json_path = OUTDIR / f"{area_slug}.json"

    rss_xml  = build_rss([], title, home_url)
    atom_xml = build_atom([], title, site_base + f"feeds/{area_slug}.atom.xml", home_url, f"urn:4thwaveai-feeds:{area_slug}")
    json_txt = build_json([], title, site_base + f"feeds/{area_slug}.json", home_url)

    rss_path.write_text(rss_xml,  encoding="utf-8", newline="\n")
    atom_path.write_text(atom_xml, encoding="utf-8", newline="\n")
    json_path.write_text(json_txt, encoding="utf-8", newline="\n")

    # Validate XML files so we fail fast if something’s off
    validate_xml(rss_path); validate_xml(atom_path)

# ---------- Text & XML safety ----------
_CONTROL = re.compile(r'[\x00-\x08\x0B\x0C\x0E-\x1F]')
def _clean(s):
    if s is None:
        return ""
    if isinstance(s, bytes):
        s = s.decode("utf-8", "replace")
    s = s.replace("\ufeff", "")
    return _CONTROL.sub("", s)

def xml_text(s: str) -> str:
    return html.escape(_clean(s), quote=True)

# ---------- Link picking from HTML ----------
def pick_links(index_html: str, base: str, preferred_prefix: Optional[str], limit: int = 20) -> List[str]:
    soup = BeautifulSoup(index_html, "lxml")
    host = urlparse(base).netloc
    seen, out = set(), []

    def add(href: Optional[str]):
        if not href: return
        full = abs_url(base, href)
        if not full: return
        if urlparse(full).netloc != host: return
        full = canon_url(full)
        if full in seen: return
        seen.add(full); out.append(full)

    # Preferred prefix (abs or rel)
    if preferred_prefix:
        for a in soup.select(f'a[href^="{preferred_prefix}"]'):
            add(a.get("href"))
            if len(out) >= limit: return out

    # Domain fallbacks
    patterns = []
    if "nanowerk.com" in host: patterns += ["/news2/"]
    if "phys.org" in host:     patterns += ["/news/"]
    if "sciencedaily.com" in host: patterns += ["/releases/"]
    if "news.mit.edu" in host or "berkeley.edu" in host: patterns += ["/20"]  # /2025/...

    for p in patterns:
        for a in soup.select(f'a[href^="{p}"]'):
            add(a.get("href"))
            if len(out) >= limit: return out

    # Generic fallback
    for a in soup.select("a[href]"):
        href = a.get("href", "")
        if any(k in href for k in ("/news/", "/story/", "/releases/", "/202", "/20", "/blog/")):
            add(href)
            if len(out) >= limit: break

    return out[:limit]

# ---------- Links from RSS/Atom ----------
def links_from_feed(feed_xml: str, base: str, limit: int = 20) -> List[str]:
    out, seen = [], set()
    try:
        root = ET.fromstring(feed_xml)
    except ET.ParseError:
        return out

    # RSS 2.0
    for item in root.findall(".//item"):
        link_el = item.find("link")
        link = (link_el.text or "").strip() if link_el is not None else ""
        if link:
            u = canon_url(urljoin(base, link))
            if u not in seen:
                seen.add(u); out.append(u)
                if len(out) >= limit: return out

    # Atom
    ns = "{http://www.w3.org/2005/Atom}"
    for entry in root.findall(f".//{ns}entry"):
        # Prefer rel="alternate" HTML link
        href = None
        for l in entry.findall(f"{ns}link"):
            rel = (l.get("rel") or "alternate").lower()
            typ = (l.get("type") or "").lower()
            if rel == "alternate" and (not typ or "html" in typ):
                href = l.get("href"); break
        if not href:
            l = entry.find(f"{ns}link")
            href = l.get("href") if l is not None else None
        if href:
            u = canon_url(urljoin(base, href.strip()))
            if u not in seen:
                seen.add(u); out.append(u)
                if len(out) >= limit: return out

    return out[:limit]

# ---------- MIME sniff ----------
def guess_mime(u: str, default: str) -> str:
    u = u.lower()
    for ext, mt in (
        (".jpg","image/jpeg"),(".jpeg","image/jpeg"),(".png","image/png"),(".gif","image/gif"),(".webp","image/webp"),
        (".mp4","video/mp4"),(".webm","video/webm"),(".mov","video/quicktime"),(".m4v","video/x-m4v"),
        (".avi","video/x-msvideo"),(".mkv","video/x-matroska")
    ):
        if ext in u:
            return mt
    return default

# ---------- Article parsing (with media) ----------
def parse_article(url: str) -> Optional[Dict]:
    try:
        s  = BeautifulSoup(fetch(url), "lxml")

        ogt = s.find("meta", property="og:title")
        title = (ogt.get("content") or "").strip() if ogt else (s.title.get_text(strip=True) if s.title else url)
        title = _clean(title)

        ogd = s.find("meta", property="og:description")
        if ogd and ogd.get("content"):
            descr = ogd["content"].strip()
        else:
            p = (s.find("article") or s).find("p")
            descr = p.get_text(" ", strip=True) if p else ""
        descr = _clean(descr) or title
        descr = descr[:800]

        # Image
        img = None
        ogimg = s.find("meta", property="og:image") or s.find("meta", attrs={"name":"twitter:image"})
        if ogimg and ogimg.get("content"):
            img = abs_url(url, ogimg["content"].strip())
        if not img:
            link_img = s.find("link", rel=lambda v: v and "image_src" in v)
            if link_img and link_img.get("href"):
                img = abs_url(url, link_img["href"].strip())

        # Video
        vid = None
        for key in ("og:video:secure_url", "og:video:url", "og:video"):
            tag = s.find("meta", property=key)
            if tag and tag.get("content"):
                vid = abs_url(url, tag["content"].strip()); break
        if not vid:
            video_tag = s.find("video")
            if video_tag:
                src = video_tag.get("src")
                if not src:
                    source = video_tag.find("source", src=True)
                    src = source["src"] if source else None
                if src:
                    vid = abs_url(url, src)
        if not vid:
            iframe = s.find("iframe", src=True)
            if iframe:
                src = iframe["src"]
                if any(k in src for k in ("youtube.com","youtu.be","vimeo.com")):
                    vid = abs_url(url, src)

        # Pub date (optional)
        pubDate = None
        pub = s.find("meta", property="article:published_time") or s.find("meta", attrs={"name":"pubdate"})
        if pub and pub.get("content"):
            try:
                dt = datetime.fromisoformat(pub["content"].replace("Z", "+00:00"))
                pubDate = email.utils.format_datetime(dt)
            except Exception:
                pubDate = None

        return {
            "title": title,
            "link": canon_url(url),
            "guid": canon_url(url),
            "description": descr,
            "pubDate": pubDate,
            "image": img,
            "video": vid,
        }
    except Exception as e:
        print(f"Skip {url}: {e}")
        return None

# ---------- Writers ----------
def build_rss(items: List[Dict], title: str, home_url: str) -> str:
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
            f"      <description>{xml_text(it['description'])}</description>",
        ]
        if it.get("pubDate"):
            parts.append(f"      <pubDate>{xml_text(it['pubDate'])}</pubDate>")
        if it.get("image"):
            parts.append(f'      <enclosure url="{xml_text(it["image"])}" type="{xml_text(guess_mime(it["image"], "image/jpeg"))}" />')
        if it.get("video"):
            parts.append(f'      <enclosure url="{xml_text(it["video"])}" type="{xml_text(guess_mime(it["video"], "video/mp4"))}" />')
        if it.get("category"):
            parts.append(f"      <category>{xml_text(it['category'])}</category>")
        parts += ["    </item>"]
    parts += ["  </channel>", "</rss>"]
    return "\n".join(parts)

def build_atom(items: List[Dict], title: str, self_url: str, home_url: str, feed_id: str) -> str:
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
            f"    <summary type=\"text\">{xml_text(it['description'])}</summary>",
        ]
        if it.get("pubDate"):
            parts.append(f"    <updated>{xml_text(it['pubDate'])}</updated>")
        parts += ["  </entry>"]
    parts += ["</feed>"]
    return "\n".join(parts)

def build_json(items: List[Dict], title: str, self_url: str, home_url: str) -> str:
    feed = {
        "version": "https://jsonfeed.org/version/1",
        "title": title,
        "home_page_url": home_url,
        "feed_url": self_url,
        "items": []
    }
    for it in items:
        item = {
            "id": it["guid"],
            "url": it["link"],
            "title": it["title"],
            "content_text": _clean(it["description"])
        }
        attachments = []
        if it.get("image"):
            attachments.append({"url": it["image"], "mime_type": guess_mime(it["image"], "image/jpeg")})
        if it.get("video"):
            attachments.append({"url": it["video"], "mime_type": guess_mime(it["video"], "video/mp4")})
        if attachments:
            item["attachments"] = attachments
        if it.get("category"):
            item["tags"] = [it["category"]]
        feed["items"].append(item)
    return json.dumps(feed, ensure_ascii=False, indent=2)

def validate_xml(path: Path):
    ET.parse(path)

# ---------- Homepage ----------
def build_index_html(areas: List[str], have_all: bool, have_videos: bool, have_leaders: bool):
    def row(slug: str) -> str:
        return (f'  <li>{slug.replace("-", " ").title()} — '
                f'<a href="feeds/{slug}.xml">RSS</a> <span class="sep">·</span> '
                f'<a href="feeds/{slug}.atom.xml">Atom</a> <span class="sep">·</span> '
                f'<a href="feeds/{slug}.json">JSON</a></li>')
    blocks = []
    if have_all:
        blocks.append('<li><a href="feeds/all.xml">RSS 2.0 (all)</a> <span class="sep">·</span> '
                      '<a href="feeds/all.atom.xml">Atom</a> <span class="sep">·</span> '
                      '<a href="feeds/all.json">JSON</a></li>')
    if have_videos:
        blocks.append('<li><a href="feeds/videos.xml">RSS 2.0 (videos)</a> <span class="sep">·</span> '
                      '<a href="feeds/videos.atom.xml">Atom</a> <span class="sep">·</span> '
                      '<a href="feeds/videos.json">JSON</a></li>')
    if have_leaders:
        blocks.append('<li><a href="feeds/tech-leaders.xml">RSS 2.0 (tech leaders)</a> <span class="sep">·</span> '
                      '<a href="feeds/tech-leaders.atom.xml">Atom</a> <span class="sep">·</span> '
                      '<a href="feeds/tech-leaders.json">JSON</a></li>')
    html_doc = f"""<!doctype html>
<meta charset="utf-8">
<title>4thWave AI Feeds</title>
<style>
  body {{ max-width: 860px; margin: 3rem auto; font: 16px/1.5 system-ui,-apple-system,Segoe UI,Roboto,"Helvetica Neue",Arial,"Noto Sans","Apple Color Emoji","Segoe UI Emoji"; }}
  h1{{font-size:2.2rem;margin-bottom:.5rem}} h2{{margin-top:2.0rem}} ul{{margin:.5rem 0 1.25rem 1rem}}
  li{{margin:.25rem 0}} .sep{{opacity:.6}}
</style>
<h1>4thWave AI Feeds</h1>
<ul>
{chr(10).join(blocks)}
</ul>
<h2>Area Feeds</h2>
<ul>
{chr(10).join(row(a) for a in sorted(areas))}
</ul>
"""
    (ROOT / "index.html").write_text(html_doc, encoding="utf-8", newline="\n")

# ---------- Main ----------
def main():
    cfg = yaml.safe_load((ROOT / "feeds.yaml").read_text(encoding="utf-8"))
    site_base = cfg.get("site_base", "https://4thwaveai-feeds.github.io/4thwaveai-feeds/")
    home_url  = cfg.get("home_url", "https://4thwave.ai")
    max_items = cfg.get("max_items_per_area", 60)

    areas_cfg: Dict[str, list] = cfg.get("areas", {})
    written_areas: List[str] = []
    all_items_for_all: List[Dict] = []

    for area_slug, sources in areas_cfg.items():
        collected: List[Dict] = []
        for src in sources:
            try:
                idx_text = fetch(src["index"])
                # Detect RSS/Atom either by explicit mode, file extension, or content sniff
                looks_xml = idx_text.lstrip()[:200].lower()
                is_rss = (src.get("mode") == "rss" or
                          src["index"].lower().endswith(".xml") or
                          "<rss" in looks_xml or "<feed" in looks_xml)
                if is_rss:
                    links = links_from_feed(idx_text, src["base"], limit=src.get("limit", 10))
                else:
                    links = pick_links(idx_text, src["base"], src.get("prefix"), limit=src.get("limit", 10))
                for u in links:
                    it = parse_article(u)
                    if it:
                        it["category"] = area_slug  # tag for routing/filters
                        collected.append(it)
            except Exception as e:
                print(f"[{area_slug}] source failed: {src.get('name', src.get('base', ''))} -> {e}")

        # de-dup by guid
        seen, unique = set(), []
        for it in collected:
            gid = it["guid"]
            if gid in seen: continue
            seen.add(gid)
            unique.append(it)

        # newest-first (undated sink to bottom)
        def s_key(x):
            try:
                return datetime.strptime(x.get("pubDate",""), "%a, %d %b %Y %H:%M:%S %z")
            except Exception:
                return datetime.min.replace(tzinfo=timezone.utc)
        unique.sort(key=s_key, reverse=True)

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

        validate_xml(rss_path); validate_xml(atom_path)
        print(f"[{area_slug}] wrote {len(unique)} items")

    # ----- All -----
    have_all = False
    if all_items_for_all:
        seen, global_items = set(), []
        for it in all_items_for_all:
            gid = it["guid"]
            if gid in seen: continue
            seen.add(gid)
            global_items.append(it)
        def s_key2(x):
            try:
                return datetime.strptime(x.get("pubDate",""), "%a, %d %b %Y %H:%M:%S %z")
            except Exception:
                return datetime.min.replace(tzinfo=timezone.utc)
        global_items.sort(key=s_key2, reverse=True)
        global_items = global_items[:max_items]

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
        have_all = True

    # ----- Videos -----
    have_videos = False
    vid_items = [it for it in all_items_for_all if it.get("video")]
    if vid_items:
        seen, vids = set(), []
        for it in vid_items:
            gid = it["guid"]
            if gid in seen: continue
            seen.add(gid)
            vids.append(it)
        def s_key3(x):
            try:
                return datetime.strptime(x.get("pubDate",""), "%a, %d %b %Y %H:%M:%S %z")
            except Exception:
                return datetime.min.replace(tzinfo=timezone.utc)
        vids.sort(key=s_key3, reverse=True)
        vids = vids[:max_items]

        title_v = "4thWave AI — Videos (Aggregated)"
        (OUTDIR / "videos.xml").write_text(build_rss(vids, title_v, home_url), encoding="utf-8", newline="\n")
        (OUTDIR / "videos.atom.xml").write_text(
            build_atom(vids, title_v, site_base + "feeds/videos.atom.xml", home_url, "urn:4thwaveai-feeds:videos"),
            encoding="utf-8", newline="\n")
        (OUTDIR / "videos.json").write_text(
            build_json(vids, title_v, site_base + "feeds/videos.json", home_url),
            encoding="utf-8", newline="\n")
        validate_xml(OUTDIR / "videos.xml"); validate_xml(OUTDIR / "videos.atom.xml")
        print(f"[videos] wrote {len(vids)} items")
        have_videos = True

    # ----- Tech Leaders combined (requires leader slugs to exist in feeds.yaml) -----
    have_leaders = False
    leader_slugs = {
        "elon-musk", "jeff-bezos", "jensen-huang", "sam-altman",
        "sundar-pichai", "satya-nadella", "demis-hassabis",
        "tim-cook", "mark-zuckerberg"
    }
    leader_items = [it for it in all_items_for_all if it.get("category") in leader_slugs]
    if leader_items:
        seen, uniq = set(), []
        for it in leader_items:
            gid = it["guid"]
            if gid in seen: continue
            seen.add(gid)
            uniq.append(it)
        def s_key4(x):
            try:
                return datetime.strptime(x.get("pubDate",""), "%a, %d %b %Y %H:%M:%S %z")
            except Exception:
                return datetime.min.replace(tzinfo=timezone.utc)
        uniq.sort(key=s_key4, reverse=True)
        uniq = uniq[:max_items]

        title_leaders = "4thWave AI — Tech Leaders (Spotlights)"
        (OUTDIR / "tech-leaders.xml").write_text(build_rss(uniq, title_leaders, home_url), encoding="utf-8", newline="\n")
        (OUTDIR / "tech-leaders.atom.xml").write_text(
            build_atom(uniq, title_leaders, site_base + "feeds/tech-leaders.atom.xml", home_url, "urn:4thwaveai-feeds:tech-leaders"),
            encoding="utf-8", newline="\n")
        (OUTDIR / "tech-leaders.json").write_text(
            build_json(uniq, title_leaders, site_base + "feeds/tech-leaders.json", home_url),
            encoding="utf-8", newline="\n")
        validate_xml(OUTDIR / "tech-leaders.xml"); validate_xml(OUTDIR / "tech-leaders.atom.xml")
        print(f"[tech-leaders] wrote {len(uniq)} items")
        have_leaders = True

    # Homepage
    build_index_html(written_areas, have_all, have_videos, have_leaders)
    print(f"Homepage index.html updated with {len(written_areas)} areas")

if __name__ == "__main__":
    main()
