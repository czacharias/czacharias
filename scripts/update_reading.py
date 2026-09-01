#!/usr/bin/env python3
"""Resolve configured DOIs through Crossref and update the README reading block."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
README_PATH = ROOT / "README.md"
READING_PATH = ROOT / "data" / "reading.json"
CACHE_PATH = ROOT / "data" / "crossref_cache.json"
START = "<!-- READING:START -->"
END = "<!-- READING:END -->"


def first(value: object, fallback: str) -> str:
    return str(value[0]) if isinstance(value, list) and value else fallback


def publication_year(message: dict[str, object]) -> str:
    for field in ("published-print", "published-online", "published", "issued"):
        value = message.get(field)
        if isinstance(value, dict):
            parts = value.get("date-parts")
            if isinstance(parts, list) and parts and isinstance(parts[0], list) and parts[0]:
                return str(parts[0][0])
    return "year unavailable"


def compact_metadata(doi: str, message: dict[str, object]) -> dict[str, str]:
    return {
        "doi": doi,
        "title": first(message.get("title"), doi),
        "venue": first(message.get("container-title"), "venue unavailable"),
        "year": publication_year(message),
        "url": f"https://doi.org/{doi}",
    }


def fetch_crossref(doi: str) -> dict[str, str]:
    endpoint = f"https://api.crossref.org/works/{urllib.parse.quote(doi, safe='')}"
    mailto = os.environ.get("CROSSREF_MAILTO", "").strip()
    if mailto:
        endpoint += "?" + urllib.parse.urlencode({"mailto": mailto})
    request = urllib.request.Request(
        endpoint,
        headers={"User-Agent": "czacharias-profile/1.0 (GitHub profile metadata updater)"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.load(response)
    return compact_metadata(doi, payload["message"])


def markdown_escape(text: str) -> str:
    for character in ("\\", "[", "]", "*", "_"):
        text = text.replace(character, "\\" + character)
    return text


def render(items: list[dict[str, str]], cache: dict[str, dict[str, str]]) -> str:
    lines: list[str] = []
    for item in items:
        doi = item["doi"].lower()
        metadata = cache.get(doi, {"title": doi, "venue": "Crossref", "year": "metadata pending", "url": f"https://doi.org/{doi}"})
        title = markdown_escape(metadata["title"])
        venue = markdown_escape(metadata["venue"])
        note = markdown_escape(item.get("note", ""))
        lines.append(f"- [{title}]({metadata['url']}) — *{venue}* ({metadata['year']})")
        if note:
            lines.append(f"  {note}")
    return "\n".join(lines)


def replace_block(readme: str, content: str) -> str:
    if readme.count(START) != 1 or readme.count(END) != 1:
        raise ValueError("README must contain exactly one reading marker pair")
    before, remainder = readme.split(START, 1)
    _, after = remainder.split(END, 1)
    return f"{before}{START}\n{content}\n{END}{after}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true", help="use cached Crossref metadata only")
    parser.add_argument("--check", action="store_true", help="fail rather than write if output is stale")
    args = parser.parse_args()

    config = json.loads(READING_PATH.read_text(encoding="utf-8"))
    items = config.get("items", [])
    if not isinstance(items, list):
        raise ValueError("data/reading.json items must be a list")
    cache = json.loads(CACHE_PATH.read_text(encoding="utf-8")) if CACHE_PATH.exists() else {}

    if not args.offline:
        for item in items:
            doi = item["doi"].lower()
            try:
                cache[doi] = fetch_crossref(doi)
                print(f"resolved {doi}")
            except Exception as error:  # A stale profile is better than a broken scheduled run.
                print(f"warning: Crossref lookup failed for {doi}: {error}", file=sys.stderr)

    old_readme = README_PATH.read_text(encoding="utf-8")
    new_readme = replace_block(old_readme, render(items, cache))
    expected_cache = json.dumps(cache, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    old_cache = CACHE_PATH.read_text(encoding="utf-8") if CACHE_PATH.exists() else ""
    stale = old_readme != new_readme or old_cache != expected_cache

    if args.check and stale:
        print("reading block or Crossref cache is stale", file=sys.stderr)
        return 1
    if not args.check:
        if old_readme != new_readme:
            README_PATH.write_text(new_readme, encoding="utf-8")
            print("updated README.md reading block")
        if old_cache != expected_cache:
            CACHE_PATH.write_text(expected_cache, encoding="utf-8")
            print("updated data/crossref_cache.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

