# 🌌 4th Wave AI Feeds

[![License: BSL → Apache 2.0 (3y)](assets/badges/license-bsl-apache.svg)](./LICENSE.md)
[![Governing Law: Nevada](https://img.shields.io/badge/Governing%20Law-Nevada-00FFFF?style=flat-square&labelColor=111318)](./LICENSE.md)

**Future-Tech Media & Intelligence Platform**  
Tracking the five frontiers shaping civilization: **AI, Quantum, Biotech, Nanotech, Robotics**

Auto-updating RSS, Atom, and JSON feeds for the five frontiers shaping civilization—plus select vendor/news sources and the new **Human Effect** area.  
Built nightly (and on demand) via GitHub Actions.

> **Note:** These are *unofficial* convenience feeds. All content © their respective publishers.

---

## 🌍 Live Site

- Homepage: [https://4thwaveai-feeds.github.io/4thwaveai-feeds/](https://4thwaveai-feeds.github.io/4thwaveai-feeds/)

---

## 📡 Direct Feed Links

### Boston Dynamics (source mirror)
- RSS:  [boston-dynamics-blog.xml](https://4thwaveai-feeds.github.io/4thwaveai-feeds/boston-dynamics-blog.xml)  
- Atom: [boston-dynamics-blog.atom.xml](https://4thwaveai-feeds.github.io/4thwaveai-feeds/boston-dynamics-blog.atom.xml)  
- JSON: [boston-dynamics-blog.json](https://4thwaveai-feeds.github.io/4thwaveai-feeds/boston-dynamics-blog.json)

---

### Area Feeds (aggregated)

**AI**  
- RSS:  [ai.xml](https://4thwaveai-feeds.github.io/4thwaveai-feeds/feeds/ai.xml)  
- Atom: [ai.atom.xml](https://4thwaveai-feeds.github.io/4thwaveai-feeds/feeds/ai.atom.xml)  
- JSON: [ai.json](https://4thwaveai-feeds.github.io/4thwaveai-feeds/feeds/ai.json)

**Robotics**  
- RSS:  [robotics.xml](https://4thwaveai-feeds.github.io/4thwaveai-feeds/feeds/robotics.xml)  
- Atom: [robotics.atom.xml](https://4thwaveai-feeds.github.io/4thwaveai-feeds/feeds/robotics.atom.xml)  
- JSON: [robotics.json](https://4thwaveai-feeds.github.io/4thwaveai-feeds/feeds/robotics.json)

**Quantum**  
- RSS:  [quantum.xml](https://4thwaveai-feeds.github.io/4thwaveai-feeds/feeds/quantum.xml)  
- Atom: [quantum.atom.xml](https://4thwaveai-feeds.github.io/4thwaveai-feeds/feeds/quantum.atom.xml)  
- JSON: [quantum.json](https://4thwaveai-feeds.github.io/4thwaveai-feeds/feeds/quantum.json)

**Biotech**  
- RSS:  [biotech.xml](https://4thwaveai-feeds.github.io/4thwaveai-feeds/feeds/biotech.xml)  
- Atom: [biotech.atom.xml](https://4thwaveai-feeds.github.io/4thwaveai-feeds/feeds/biotech.atom.xml)  
- JSON: [biotech.json](https://4thwaveai-feeds.github.io/4thwaveai-feeds/feeds/biotech.json)

**Nanotech**  
- RSS:  [nanotech.xml](https://4thwaveai-feeds.github.io/4thwaveai-feeds/feeds/nanotech.xml)  
- Atom: [nanotech.atom.xml](https://4thwaveai-feeds.github.io/4thwaveai-feeds/feeds/nanotech.atom.xml)  
- JSON: [nanotech.json](https://4thwaveai-feeds.github.io/4thwaveai-feeds/feeds/nanotech.json)

**Human Effect**  
- RSS:  [human_effect.xml](https://4thwaveai-feeds.github.io/4thwaveai-feeds/feeds/human_effect.xml)  
- Atom: [human_effect.atom.xml](https://4thwaveai-feeds.github.io/4thwaveai-feeds/feeds/human_effect.atom.xml)  
- JSON: [human_effect.json](https://4thwaveai-feeds.github.io/4thwaveai-feeds/feeds/human_effect.json)

---

## ⚙️ How It Works

### Workflows
- **Update Boston Dynamics RSS** → builds the BD RSS/Atom/JSON files in the repo root.  
- **Update Area Feeds** → builds aggregated feeds under `/feeds/` for AI, Robotics, Quantum, Biotech, Nanotech, Human Effect.

### Builders
- `scripts/build_boston_dynamics_feed.py`  
- `scripts/build_area_feeds.py`

### Config
- `feeds.yaml` lists sources per area.  
- Add/edit sources without touching code.

---

## ✍️ Add or Edit a Source

To add a new feed:

```yaml
areas:
  robotics:
    - name: Example Robotics Site
      index: "https://example.com/news/"
      base:  "https://example.com"
      prefix: "/news/"
      limit: 10
