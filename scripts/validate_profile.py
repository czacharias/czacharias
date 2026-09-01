#!/usr/bin/env python3
"""Local and CI checks for the generated profile repository."""

from __future__ import annotations

import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def run(*arguments: str) -> None:
    subprocess.run([sys.executable, *arguments], cwd=ROOT, check=True)


def main() -> int:
    required = [
        ROOT / "README.md",
        ROOT / "assets" / "header.svg",
        ROOT / "assets" / "status.svg",
        ROOT / ".github" / "workflows" / "profile.yml",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
    if missing:
        raise ValueError(f"missing required files: {', '.join(missing)}")

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for fragment in ("/selected-work", "/system-status", "/reading", "/research-interests", "/off-hours"):
        if fragment not in readme:
            raise ValueError(f"README is missing {fragment}")
    for forbidden in ("osu",):
        if forbidden.lower() in readme.lower():
            raise ValueError(f"README contains intentionally excluded text: {forbidden}")

    status = json.loads((ROOT / "data" / "status.json").read_text(encoding="utf-8"))
    keys = [project["key"] for project in status["projects"]]
    if len(keys) != len(set(keys)):
        raise ValueError("project keys must be unique")

    ET.parse(ROOT / "assets" / "header.svg")
    ET.parse(ROOT / "assets" / "status.svg")
    run("scripts/generate_status.py", "--check")
    run("scripts/update_reading.py", "--offline", "--check")
    print("profile validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
