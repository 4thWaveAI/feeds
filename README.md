# 4thWave AI Feeds

Auto-updating RSS, Atom, and JSON feeds for the five frontiers shaping civilization—AI, Robotics, Quantum, Biotech, and Nanotech—plus select vendor/news sources. Built nightly (and on demand) via GitHub Actions.

> **Note**: These are *unofficial* convenience feeds. All content © their respective publishers.

---

## Live site

- Homepage: https://4thwaveai-feeds.github.io/4thwaveai-feeds/

---

## Direct feed links

### Boston Dynamics (source mirror)
- RSS:  https://4thwaveai-feeds.github.io/4thwaveai-feeds/boston-dynamics-blog.xml
- Atom: https://4thwaveai-feeds.github.io/4thwaveai-feeds/boston-dynamics-blog.atom.xml
- JSON: https://4thwaveai-feeds.github.io/4thwaveai-feeds/boston-dynamics-blog.json

### Area feeds (aggregated)
- **AI**  
  RSS:  https://4thwaveai-feeds.github.io/4thwaveai-feeds/feeds/ai.xml  
  Atom: https://4thwaveai-feeds.github.io/4thwaveai-feeds/feeds/ai.atom.xml  
  JSON: https://4thwaveai-feeds.github.io/4thwaveai-feeds/feeds/ai.json

- **Robotics**  
  RSS:  https://4thwaveai-feeds.github.io/4thwaveai-feeds/feeds/robotics.xml  
  Atom: https://4thwaveai-feeds.github.io/4thwaveai-feeds/feeds/robotics.atom.xml  
  JSON: https://4thwaveai-feeds.github.io/4thwaveai-feeds/feeds/robotics.json

- **Quantum**  
  RSS:  https://4thwaveai-feeds.github.io/4thwaveai-feeds/feeds/quantum.xml  
  Atom: https://4thwaveai-feeds.github.io/4thwaveai-feeds/feeds/quantum.atom.xml  
  JSON: https://4thwaveai-feeds.github.io/4thwaveai-feeds/feeds/quantum.json

- **Biotech**  
  RSS:  https://4thwaveai-feeds.github.io/4thwaveai-feeds/feeds/biotech.xml  
  Atom: https://4thwaveai-feeds.github.io/4thwaveai-feeds/feeds/biotech.atom.xml  
  JSON: https://4thwaveai-feeds.github.io/4thwaveai-feeds/feeds/biotech.json

- **Nanotech**  
  RSS:  https://4thwaveai-feeds.github.io/4thwaveai-feeds/feeds/nanotech.xml  
  Atom: https://4thwaveai-feeds.github.io/4thwaveai-feeds/feeds/nanotech.atom.xml  
  JSON: https://4thwaveai-feeds.github.io/4thwaveai-feeds/feeds/nanotech.json

---

## How it works

- **Workflows**
  - `Update Boston Dynamics RSS` → builds the BD RSS/Atom/JSON files in the repo root.
  - `Update Area Feeds` → builds aggregated feeds under `/feeds/` for AI, Robotics, Quantum, Biotech, Nanotech.
- **Builders**
  - `scripts/build_boston_dynamics_feed.py`
  - `scripts/build_area_feeds.py`
- **Config**
  - `feeds.yaml` lists sources per area. You can add/edit sources without touching code.

---

## Add or edit a source

Edit `feeds.yaml` → find the area → append a block:

```yaml
areas:
  robotics:
    - name: Example Robotics Site
      index: "https://example.com/news/"
      base:  "https://example.com"
      prefix: "/news/"
      limit: 10
