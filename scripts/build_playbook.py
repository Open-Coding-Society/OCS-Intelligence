#!/usr/bin/env python3
"""Render a playbook's Markdown into the standard PDF next to it.

  uv run --group playbook scripts/build_playbook.py evidence/sprint4/2026-10-15-netbird-access-policies.md
  uv run --group playbook scripts/build_playbook.py --all          # every playbook under evidence/
  uv run --group playbook scripts/build_playbook.py --html FILE    # also write FILE.html, for previewing

Needs pandoc on PATH; the `playbook` dependency group brings weasyprint. Format rules: docs/conventions.md#playbooks.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HERE = REPO / "scripts" / "playbook"
EVIDENCE = REPO / "evidence"
REQUIRED = ("date", "title", "sprint", "state")
STATES = {"in progress", "done"}
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def header(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    end = text.find("\n---\n", 4)
    if not text.startswith("---\n") or end == -1:
        return {}
    fields = {}
    for line in text[4:end].splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip()] = value.split(" #", 1)[0].strip()
    return fields


def is_playbook(path: Path) -> bool:
    return header(path).get("type") == "playbook"


def check(path: Path, fields: dict[str, str]) -> list[str]:
    rel = path.relative_to(REPO)
    errors = [f"{rel}: header needs '{key}:'" for key in REQUIRED if not fields.get(key)]
    if fields.get("state") and fields["state"] not in STATES:
        errors.append(f"{rel}: state must be one of {sorted(STATES)}")
    if fields.get("date") and not DATE.match(fields["date"]):
        errors.append(f"{rel}: date must be YYYY-MM-DD")
    if not DATE.match(path.name[:10]):
        errors.append(f"{rel}: name it YYYY-MM-DD-short-title.md")
    return errors


def build(path: Path, html: bool) -> None:
    from weasyprint import CSS, HTML  # imported late so --help works without it

    fields = header(path)
    rel = path.relative_to(REPO)
    page = subprocess.run(
        [
            "pandoc", str(path),
            "--from", "gfm+yaml_metadata_block",
            "--to", "html5",
            "--template", str(HERE / "template.html"),
            "--lua-filter", str(HERE / "filter.lua"),
            "--highlight-style", str(HERE / "illuminati.theme"),
            "--metadata", f"repo-dir={rel.parent.as_posix()}",
            "--metadata", f"source-path={rel.as_posix()}",
            "--metadata", f"state-class={fields['state'].replace(' ', '-')}",
        ],
        check=True, capture_output=True, text=True,
    ).stdout
    page = re.sub(r'<a href="#cb\d+-\d+" aria-hidden="true" tabindex="-1"></a>', "", page)
    if html:
        path.with_suffix(".html").write_text(page, encoding="utf-8")
    out = path.with_suffix(".pdf")
    HTML(string=page, base_url=str(path.parent)).write_pdf(
        out, stylesheets=[CSS(filename=str(HERE / "style.css"))]
    )
    print(f"wrote {out.relative_to(REPO)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("files", nargs="*", type=Path)
    parser.add_argument("--all", action="store_true", help="build every playbook under evidence/")
    parser.add_argument("--html", action="store_true", help="also write the intermediate HTML")
    args = parser.parse_args()

    files = [p.resolve() for p in args.files]
    if args.all:
        files += sorted(p for p in EVIDENCE.rglob("*.md") if is_playbook(p))
    if not files:
        parser.error("give a playbook .md file, or --all")

    errors = [e for p in files for e in check(p, header(p))]
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    for path in files:
        build(path, args.html)
    return 0


if __name__ == "__main__":
    sys.exit(main())
