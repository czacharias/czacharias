#!/usr/bin/env python3
"""Generate the profile status SVG and Shields endpoint JSON files."""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
STATUS_PATH = ROOT / "data" / "status.json"
SVG_PATH = ROOT / "assets" / "status.svg"
BADGES_DIR = ROOT / "badges"


def load_projects() -> list[dict[str, str]]:
    payload = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
    projects = payload.get("projects")
    if not isinstance(projects, list) or not projects:
        raise ValueError("data/status.json must contain a non-empty projects list")

    required = {"key", "name", "area", "status", "detail", "color"}
    for project in projects:
        missing = required.difference(project)
        if missing:
            raise ValueError(f"status entry is missing: {', '.join(sorted(missing))}")
    return projects


def render_svg(projects: list[dict[str, str]]) -> str:
    width = 900
    row_height = 78
    height = 74 + row_height * len(projects) + 22
    rows: list[str] = []

    for index, project in enumerate(projects):
        y = 68 + index * row_height
        name = html.escape(project["name"])
        area = html.escape(project["area"])
        status = html.escape(project["status"])
        detail = html.escape(project["detail"])
        color = html.escape(project["color"].lstrip("#"))
        rows.append(
            f'''  <g transform="translate(34 {y})">
    <rect width="832" height="62" rx="6" fill="#111715" stroke="#263732"/>
    <rect width="4" height="62" rx="2" fill="#{color}"/>
    <circle cx="24" cy="22" r="5" fill="#{color}"/>
    <text x="40" y="27" class="name">{name}</text>
    <text x="230" y="27" class="area">{area}</text>
    <text x="812" y="27" class="status" text-anchor="end" fill="#{color}">{status}</text>
    <text x="40" y="48" class="detail">{detail}</text>
  </g>'''
        )

    body = "\n".join(rows)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">
  <title>Current project status</title>
  <style>
    text {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
    .eyebrow {{ fill: #66f0c8; font-size: 12px; letter-spacing: 1.5px; }}
    .hint {{ fill: #71817c; font-size: 11px; }}
    .name {{ fill: #f0eee6; font-size: 15px; font-weight: 700; }}
    .area {{ fill: #8fa29c; font-size: 12px; }}
    .status {{ font-size: 12px; font-weight: 700; }}
    .detail {{ fill: #a9b8b3; font-size: 12px; }}
  </style>
  <rect width="{width}" height="{height}" rx="10" fill="#0b0f0e"/>
  <rect x="1" y="1" width="898" height="{height - 2}" rx="9" fill="none" stroke="#2d3d39"/>
  <text x="34" y="36" class="eyebrow">PROJECT TELEMETRY</text>
  <text x="866" y="36" class="hint" text-anchor="end">source: data/status.json</text>
{body}
</svg>
'''


def render_badge(project: dict[str, str]) -> str:
    payload = {
        "schemaVersion": 1,
        "label": project["name"].lower(),
        "message": project["status"],
        "color": project["color"].lstrip("#"),
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def sync(path: Path, expected: str, check: bool) -> bool:
    current = path.read_text(encoding="utf-8") if path.exists() else None
    if current == expected:
        return True
    if check:
        print(f"stale generated file: {path.relative_to(ROOT)}", file=sys.stderr)
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(expected, encoding="utf-8")
    print(f"updated {path.relative_to(ROOT)}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if generated files are stale")
    args = parser.parse_args()

    projects = load_projects()
    outputs = [(SVG_PATH, render_svg(projects))]
    outputs.extend((BADGES_DIR / f"{project['key']}.json", render_badge(project)) for project in projects)
    return 0 if all(sync(path, content, args.check) for path, content in outputs) else 1


if __name__ == "__main__":
    raise SystemExit(main())

