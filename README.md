<p align="center">
  <img src="https://builder.hostinger.com/mjEGRKM9zpTV7VJ5" width="240" alt="4th Wave AI Logo"/>
</p>

<h1 align="center">🌌 4th Wave AI Feeds</h1>
<p align="center"><b>Future-Tech Media & Intelligence Platform</b></p>
<p align="center">Tracking AI • Robotics • Quantum • Biotech • Nanotech • Human Effect</p>

<p align="center">
  <a href="./LICENSE.md">
    <img src="assets/badges/license-bsl-apache.svg" alt="License: BSL → Apache 2.0 (3y)">
  </a>
  <a href="./LICENSE.md">
    <img src="https://img.shields.io/badge/Governing%20Law-Nevada-00FFFF?style=flat-square&labelColor=111318" alt="Governing Law: Nevada">
  </a>
  <a href="https://github.com/4thwaveai-feeds/4thwaveai-feeds/actions">
    <img src="https://github.com/4thwaveai-feeds/4thwaveai-feeds/actions/workflows/update-area-feeds.yml/badge.svg" alt="Build Status">
  </a>
</p>

---

> **Future-Tech Media & Intelligence Platform**  
> Auto-updating **RSS, Atom, and JSON feeds** for the five frontiers shaping civilization — AI, Robotics, Quantum, Biotech, Nanotech — plus the **Human Effect** area.  
> Built nightly (and on demand) via GitHub Actions.

> **Note:** These are *unofficial* convenience feeds.  
> All content © their respective publishers.

---

## 🌍 Live Site
- Homepage → [4thwaveai-feeds.github.io/4thwaveai-feeds](https://4thwaveai-feeds.github.io/4thwaveai-feeds/)

---

## 📡 Direct Feed Links

### 🔹 Boston Dynamics (source mirror)
- [RSS](https://4thwaveai-feeds.github.io/4thwaveai-feeds/boston-dynamics-blog.xml)  
- [Atom](https://4thwaveai-feeds.github.io/4thwaveai-feeds/boston-dynamics-blog.atom.xml)  
- [JSON](https://4thwaveai-feeds.github.io/4thwaveai-feeds/boston-dynamics-blog.json)

---

### 🔹 Area Feeds (aggregated)

**AI** → [RSS](feeds/ai.xml) | [Atom](feeds/ai.atom.xml) | [JSON](feeds/ai.json)  
**Robotics** → [RSS](feeds/robotics.xml) | [Atom](feeds/robotics.atom.xml) | [JSON](feeds/robotics.json)  
**Quantum** → [RSS](feeds/quantum.xml) | [Atom](feeds/quantum.atom.xml) | [JSON](feeds/quantum.json)  
**Biotech** → [RSS](feeds/biotech.xml) | [Atom](feeds/biotech.atom.xml) | [JSON](feeds/biotech.json)  
**Nanotech** → [RSS](feeds/nanotech.xml) | [Atom](feeds/nanotech.atom.xml) | [JSON](feeds/nanotech.json)  
**Human Effect** → [RSS](feeds/human_effect.xml) | [Atom](feeds/human_effect.atom.xml) | [JSON](feeds/human_effect.json)  

---

## ⚙️ How It Works

### 🔧 Workflows
- **Update Boston Dynamics RSS** → builds BD RSS/Atom/JSON files in repo root  
- **Update Area Feeds** → builds `/feeds/` for AI, Robotics, Quantum, Biotech, Nanotech, Human Effect

### 🛠 Builders
- `scripts/build_boston_dynamics_feed.py`  
- `scripts/build_area_feeds.py`

### 📑 Config
- `feeds.yaml` defines sources per area  
- Add/edit feeds without touching code  

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
