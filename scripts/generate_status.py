#!/usr/bin/env python3
"""Generate standardized Shields endpoint JSON files."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
STATUS_PATH = ROOT / "data" / "status.json"
BADGES_DIR = ROOT / "badges"


def load_projects() -> list[dict[str, str]]:
    payload = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
    projects = payload.get("projects")
    if not isinstance(projects, list) or not projects:
        raise ValueError("data/status.json must contain a non-empty projects list")

    required = {"key", "name", "status", "color"}
    for project in projects:
        missing = required.difference(project)
        if missing:
            raise ValueError(f"status entry is missing: {', '.join(sorted(missing))}")
    return projects


def render_badge(project: dict[str, str]) -> str:
    payload = {
        "schemaVersion": 1,
        "label": "status",
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
    outputs = [(BADGES_DIR / f"{project['key']}.json", render_badge(project)) for project in projects]
    return 0 if all(sync(path, content, args.check) for path, content in outputs) else 1


if __name__ == "__main__":
    raise SystemExit(main())
