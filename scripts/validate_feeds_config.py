#!/usr/bin/env python3
"""Validate the 4th Wave AI feed registry without contacting remote sites."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import urlparse

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "feeds.yaml"
AREA_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def is_http_url(value: object) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    parsed = urlparse(value.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    try:
        document = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"ERROR: unable to parse {CONFIG.name}: {exc}")
        return 1

    if not isinstance(document, dict):
        print("ERROR: feeds.yaml must contain a top-level mapping.")
        return 1

    for key in ("site_base", "home_url", "areas"):
        if key not in document:
            errors.append(f"missing top-level key: {key}")

    site_base = document.get("site_base")
    home_url = document.get("home_url")
    max_items = document.get("max_items_per_area", 60)
    areas = document.get("areas")

    if not is_http_url(site_base):
        errors.append("site_base must be a valid HTTP(S) URL")
    elif not str(site_base).endswith("/"):
        errors.append("site_base must end with '/' because feed paths are appended to it")

    if not is_http_url(home_url):
        errors.append("home_url must be a valid HTTP(S) URL")

    if not isinstance(max_items, int) or isinstance(max_items, bool) or not 1 <= max_items <= 500:
        errors.append("max_items_per_area must be an integer from 1 through 500 when present")

    source_count = 0
    if not isinstance(areas, dict) or not areas:
        errors.append("areas must be a non-empty mapping of area slug to source list")
    else:
        for area_name, sources in areas.items():
            if not isinstance(area_name, str) or not AREA_SLUG.fullmatch(area_name):
                errors.append(f"invalid area slug: {area_name!r}")

            if not isinstance(sources, list):
                errors.append(f"[{area_name}] must be a list of source mappings")
                continue

            if not sources:
                warnings.append(f"[{area_name}] contains no sources")

            for position, source in enumerate(sources, start=1):
                context = f"[{area_name}][{position}]"
                if not isinstance(source, dict):
                    errors.append(f"{context} must be a mapping")
                    continue

                source_count += 1

                name = source.get("name")
                index = source.get("index")
                base = source.get("base")
                prefix = source.get("prefix")
                mode = source.get("mode")
                limit = source.get("limit", 10)

                if not isinstance(name, str) or not name.strip():
                    errors.append(f"{context} requires a non-empty name")
                if not is_http_url(index):
                    errors.append(f"{context} index must be a valid HTTP(S) URL")
                if not is_http_url(base):
                    errors.append(f"{context} base must be a valid HTTP(S) URL")

                if prefix is not None and not isinstance(prefix, str):
                    errors.append(f"{context} prefix must be a string when present")

                if mode is not None and not isinstance(mode, str):
                    errors.append(f"{context} mode must be a string when present")

                if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 200:
                    errors.append(f"{context} limit must be an integer from 1 through 200")

                for pattern_key in ("allow_patterns", "deny_patterns"):
                    if pattern_key not in source:
                        continue
                    patterns = source[pattern_key]
                    if not isinstance(patterns, list):
                        errors.append(f"{context} {pattern_key} must be a list")
                        continue
                    for pattern_position, pattern in enumerate(patterns, start=1):
                        if not isinstance(pattern, str):
                            errors.append(
                                f"{context} {pattern_key}[{pattern_position}] must be a string"
                            )
                            continue
                        try:
                            re.compile(pattern)
                        except re.error as exc:
                            errors.append(
                                f"{context} {pattern_key}[{pattern_position}] invalid regex: {exc}"
                            )

    for warning in warnings:
        print(f"WARNING: {warning}")

    if errors:
        print(f"ERROR: {CONFIG.name} validation failed with {len(errors)} problem(s):")
        for error in errors:
            print(f" - {error}")
        return 1

    print(
        f"Configuration valid: {len(areas)} areas, {source_count} sources, "
        f"max {max_items} items per area."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
