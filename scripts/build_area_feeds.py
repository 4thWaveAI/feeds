#!/usr/bin/env python3
"""
Build aggregated feeds per area from feeds.yaml

Outputs:
  /feeds/<area>.xml
  /feeds/<area>.atom.xml
  /feeds/<area>.json
  /feeds/all.(xml|atom.xml|json)            # all areas combined (optional if items exist)
  /feeds/videos.(xml|atom.xml|json)         # videos-only (optional if items exist)

Also writes:
  /index.html  (auto-lists all areas + 'All' + 'Videos' when present)

Safe XML (no raw CDATA). Adds <enclosure> for image/video. Validates XML before finish.
"""

import re, os, html, json, yaml, requests, email.utils, xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlunparse, parse_qsl, urlencode
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, List

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

# ---------- URL helpers ----------
STRIP_QS = {"utm_source","utm_medium","utm_campaign","utm_term","utm_content","utm_id",
            "fbclid","gclid","mc_cid","mc_eid","igshid","si","ref","ref_src"}
def canon_url(u: str) -> str:
    """Absolute, no fragment, trimmed tracking query params."""
    try:
        p = urlparse(u)
        # make absolute if somehow relative slipped through (rare)
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

TAG = re.compile(r"<[^>]+>")
def strip_tags(html_str: str) -> str:
    return TAG.sub("", html_str or "")

# ---------- Link picking ----------
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

    # 1) Preferred prefix (abs or rel)
    if preferred_prefix:
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
        html_text = fetch(url)
        s  = BeautifulSoup(html_text, "lxml")

        # Title
        ogt = s.find("meta", property="og:title")
        tit
