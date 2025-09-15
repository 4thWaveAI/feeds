/* 4thWave AI Feed Widget
 * Works with your GitHub Pages feeds:
 *  - RSS:  https://4thwaveai-feeds.github.io/4thwaveai-feeds/feeds/<area>.xml
 *  - JSON: https://4thwaveai-feeds.github.io/4thwaveai-feeds/feeds/<area>.json
 * Also supports Atom. Handles images/videos via <enclosure> or JSON attachments.
 */

const CACHE_MINUTES = 15;

function $(sel, root=document){ return root.querySelector(sel); }
function $all(sel, root=document){ return Array.from(root.querySelectorAll(sel)); }

function stripTags(html){ const d = document.createElement('div'); d.innerHTML = html||''; return d.textContent||d.innerText||''; }
function truncate(s, n=180){ if(!s) return ""; const t = s.trim(); return t.length>n ? (t.slice(0,n-1)+'…') : t; }
function toISO(d){ const dt = new Date(d); return isNaN(dt) ? null : dt.toISOString(); }
function fromRFC822(s){ const d = new Date(s); return isNaN(d) ? null : d; }

function cacheKey(url){ return 'fwfeed:'+url; }
function saveCache(url, data){
  try{
    localStorage.setItem(cacheKey(url), JSON.stringify({t:Date.now(), data}));
  }catch(e){}
}
function loadCache(url){
  try{
    const raw = localStorage.getItem(cacheKey(url));
    if(!raw) return null;
    const obj = JSON.parse(raw);
    if(Date.now() - obj.t > CACHE_MINUTES*60*1000) return null;
    return obj.data;
  }catch(e){ return null; }
}

async function fetchText(url){
  const c = loadCache(url);
  if(c) return c;
  const res = await fetch(url, {credentials:'omit', mode:'cors'});
  const txt = await res.text();
  saveCache(url, txt);
  return txt;
}

/* Normalize items to a common shape:
 * { title, url, desc, date, area, image, video }
 */
function normalizeFromJSON(feed, areaGuess=''){
  const out = [];
  const items = (feed.items||[]);
  for(const it of items){
    const title = it.title || '';
    const url = it.url || it.external_url || '';
    const desc = it.content_text || it.summary || '';
    const date = it.date_published || null; // may be missing in your generator
    let image=null, video=null;
    if(Array.isArray(it.attachments)){
      for(const a of it.attachments){
        const mt = (a.mime_type||'').toLowerCase();
        if(!image && mt.startsWith('image/')) image = a.url;
        if(!video && mt.startsWith('video/')) video = a.url;
      }
    }
    out.push({title, url, desc, date, area: areaGuess, image, video});
  }
  return out;
}

function normalizeFromRSS(xmlDoc, areaGuess=''){
  const out = [];
  const items = Array.from(xmlDoc.querySelectorAll('item'));
  for(const node of items){
    const title = node.querySelector('title')?.textContent?.trim() || '';
    const url = node.querySelector('link')?.textContent?.trim() || '';
    const desc = stripTags(node.querySelector('description')?.textContent || '');
    const date = node.querySelector('pubDate')?.textContent?.trim() || null;
    const area = node.querySelector('category')?.textContent?.trim() || areaGuess;
    let image=null, video=null;
    const encs = Array.from(node.querySelectorAll('enclosure[url]'));
    for(const e of encs){
      const mt = (e.getAttribute('type')||'').toLowerCase();
      const u  = e.getAttribute('url');
      if(!image && mt.startsWith('image/')) image = u;
      if(!video && mt.startsWith('video/')) video = u;
    }
    out.push({title, url, desc, date, area, image, video});
  }
  return out;
}

function normalizeFromAtom(xmlDoc, areaGuess=''){
  const out = [];
  const ns = 'http://www.w3.org/2005/Atom';
  const entries = Array.from(xmlDoc.getElementsByTagNameNS(ns,'entry'));
  for(const node of entries){
    const title = node.getElementsByTagNameNS(ns,'title')[0]?.textContent?.trim() || '';
    let url = '';
    const links = Array.from(node.getElementsByTagNameNS(ns,'link'));
    const alt = links.find(l => (l.getAttribute('rel')||'alternate')==='alternate' && ((l.getAttribute('type')||'').includes('html') || !l.getAttribute('type')));
    url = (alt?.getAttribute('href') || links[0]?.getAttribute('href') || '').trim();
    const desc = stripTags(node.getElementsByTagNameNS(ns,'summary')[0]?.textContent || node.getElementsByTagNameNS(ns,'content')[0]?.textContent || '');
    const date = node.getElementsByTagNameNS(ns,'updated')[0]?.textContent?.trim() || null;
    // Atom doesn't standardize enclosures; skip for simplicity here.
    out.push({title, url, desc, date, area: areaGuess, image:null, video:null});
  }
  return out;
}

async function loadItems(url, areaLabel=''){
  const text = await fetchText(url);
  const trimmed = text.trim().slice(0, 200).toLowerCase();

  // JSON Feed?
  if (trimmed.startsWith('{') && (text.includes('"version"') && text.includes('jsonfeed'))) {
    try{
      const json = JSON.parse(text);
      return normalizeFromJSON(json, areaLabel);
    }catch(e){ /* fallthrough */ }
  }

  // XML (RSS/Atom)
  const doc = new DOMParser().parseFromString(text, 'application/xml');
  if (doc.querySelector('parsererror')) {
    // Fallback: try HTML (not expected here)
    return [];
  }
  if (doc.querySelector('rss'))  return normalizeFromRSS(doc, areaLabel);
  if (doc.querySelector('feed')) return normalizeFromAtom(doc, areaLabel);
  return [];
}

function renderCard(it){
  const el = document.createElement('article');
  el.className = 'fw-card';

  const media = document.createElement('div');
  media.className = 'fw-media';

  if (it.video) {
    const v = document.createElement('video');
    v.src = it.video; v.controls = true; v.playsInline = true; v.preload = 'none';
    if (it.image) v.poster = it.image;
    media.appendChild(v);
  } else if (it.image) {
    const img = new Image();
    img.loading = 'lazy'; img.decoding = 'async';
    img.src = it.image;
    media.appendChild(img);
  }

  const body = document.createElement('div');
  body.className = 'fw-body';

  const area = document.createElement('div');
  area.className = 'fw-area';
  area.textContent = it.area || '';

  const h = document.createElement('h3');
  h.className = 'fw-h';
  const a = document.createElement('a');
  a.href = it.url; a.target = '_blank'; a.rel = 'noopener';
  a.textContent = it.title || 'Untitled';
  h.appendChild(a);

  const desc = document.createElement('p');
  desc.className = 'fw-desc';
  desc.textContent = truncate(it.desc, 180);

  const meta = document.createElement('div');
  meta.className = 'fw-meta';
  if (it.date) {
    const d = document.createElement('span');
    const dt = fromRFC822(it.date) || new Date(it.date);
    d.textContent = isNaN(dt)? '' : dt.toLocaleDateString(undefined, {month:'short', day:'numeric', year:'numeric'});
    meta.appendChild(d);
  }
  if (it.video) {
    const vd = document.createElement('span');
    vd.className = 'fw-dot';
    vd.textContent = 'Video';
    meta.appendChild(vd);
  }

  if (it.image || it.video) el.appendChild(media);
  body.append(area, h, desc, meta);
  el.appendChild(body);
  return el;
}

async function initWidget(root){
  const feed    = root.dataset.feed || '';
  const merge   = root.dataset.merge || '';      // comma-separated list of feed URLs
  const limit   = parseInt(root.dataset.limit || '9', 10);
  const title   = root.dataset.title || 'Latest';
  const areaLbl = root.dataset.area || '';       // optional label override
  const viewAll = root.dataset.viewall || '';    // optional "view all" URL

  // header
  const header = document.createElement('div');
  header.className = 'fw-header';
  const h = document.createElement('h2');
  h.className = 'fw-title';
  h.textContent = title;
  header.appendChild(h);
  if (viewAll) {
    const a = document.createElement('a');
    a.href = viewAll; a.target = '_blank'; a.rel='noopener';
    a.className = 'fw-viewall'; a.textContent = 'View all ›';
    header.appendChild(a);
  }
  root.appendChild(header);

  const grid = document.createElement('div');
  grid.className = 'fw-grid';
  root.appendChild(grid);

  // skeleton while loading
  for(let i=0;i<Math.min(limit,6);i++){
    const sk = document.createElement('div'); sk.className='fw-card';
    const m  = document.createElement('div'); m.className='fw-media fw-skel';
    const b  = document.createElement('div'); b.className='fw-body';
    b.innerHTML = '<div class="fw-skel" style="height:18px;width:70%"></div><div class="fw-skel" style="height:12px;width:95%;margin-top:10px"></div>';
    sk.append(m,b); grid.appendChild(sk);
  }

  // gather feed URLs
  const urls = [];
  if (merge) merge.split(',').map(s=>s.trim()).filter(Boolean).forEach(u=>urls.push(u));
  if (feed) urls.push(feed);

  // load & normalize
  const batches = await Promise.all(urls.map(u => loadItems(u, areaLbl)));
  let items = batches.flat();

  // sort by date when present; otherwise keep original order
  items = items.map((it, i)=> ({...it, _i:i, _sort: toISO(it.date)||''}));
  items.sort((a,b)=>{
    if (a._sort && b._sort) return (a._sort > b._sort ? -1 : 1);
    if (a._sort && !b._sort) return -1;
    if (!a._sort && b._sort) return 1;
    return a._i - b._i;
  });
  items = items.slice(0, limit);

  // render
  grid.innerHTML = '';
  for(const it of items){
    grid.appendChild(renderCard(it));
  }
}

function boot(){
  $all('[data-feed], .fw-feed').forEach(initWidget);
}
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', boot);
} else {
  boot();
}
