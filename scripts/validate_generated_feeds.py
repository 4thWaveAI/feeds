#!/usr/bin/env python3
"""Validate generated feed files and the public directory index."""

from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
FEEDS_DIR = ROOT / "feeds"
CONFIG = ROOT / "feeds.yaml"
INDEX = ROOT / "index.html"


def main() -> int:
    errors: list[str] = []

    try:
        config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
        areas = config["areas"]
    except Exception as exc:
        print(f"ERROR: unable to load feed registry: {exc}")
        return 1

    if not INDEX.exists():
        errors.append("index.html was not generated")
        index_text = ""
    else:
        index_text = INDEX.read_text(encoding="utf-8")

    for area in areas:
        expected = {
            "rss": FEEDS_DIR / f"{area}.xml",
            "atom": FEEDS_DIR / f"{area}.atom.xml",
            "json": FEEDS_DIR / f"{area}.json",
        }

        for kind, path in expected.items():
            if not path.exists():
                errors.append(f"missing {kind} output: {path.relative_to(ROOT)}")
                continue

            try:
                if kind == "json":
                    payload = json.loads(path.read_text(encoding="utf-8"))
                    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
                        errors.append(f"invalid JSON Feed structure: {path.relative_to(ROOT)}")
                else:
                    ET.parse(path)
            except Exception as exc:
                errors.append(f"invalid {kind} output {path.relative_to(ROOT)}: {exc}")

        for suffix in ("xml", "atom.xml", "json"):
            link = f'feeds/{area}.{suffix}'
            if link not in index_text:
                errors.append(f"index.html does not list {link}")

    for path in FEEDS_DIR.glob("*.xml"):
        try:
            ET.parse(path)
        except Exception as exc:
            errors.append(f"invalid XML file {path.relative_to(ROOT)}: {exc}")

    for path in FEEDS_DIR.glob("*.json"):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"invalid JSON file {path.relative_to(ROOT)}: {exc}")

    if errors:
        print(f"ERROR: generated feed validation failed with {len(errors)} problem(s):")
        for error in errors:
            print(f" - {error}")
        return 1

    print(f"Generated output valid for {len(areas)} configured areas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
