#!/usr/bin/env python3
"""Check the docs follow docs/conventions.md.

  python3 scripts/check_docs.py

Checks:
  - every doc under docs/ and evidence/ has the right header
  - every relative Markdown link in the repo points at a file that exists
  - every doc is reachable from docs/docs.md by following links

Stdlib only. Exits 1 if anything fails.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DOCS = REPO / "docs"
EVIDENCE = REPO / "evidence"
INDEX = DOCS / "docs.md"
TEMPLATES = DOCS / "_templates"
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__"}

DOC_STATUSES = {"draft", "current", "superseded"}
DECISION_STATUSES = {"proposed", "accepted", "rejected", "superseded"}
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DECISION_FILE = re.compile(r"^\d{4}-.+\.md$")
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
FENCE = re.compile(r"^\s*(```|~~~)")


def markdown_files() -> list[Path]:
    return sorted(
        p
        for p in REPO.rglob("*.md")
        if not SKIP_DIRS.intersection(p.relative_to(REPO).parts)
    )


def header(path: Path) -> dict[str, str] | None:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end == -1:
        return None
    fields = {}
    for line in text[4:end].splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip()] = value.split("#", 1)[0].strip()
    return fields


def links(path: Path) -> list[str]:
    out, in_fence = [], False
    for line in path.read_text(encoding="utf-8").splitlines():
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        line = re.sub(r"`[^`]*`", "", line)  # ignore inline code
        out.extend(LINK.findall(line))
    return out


def local_target(path: Path, link: str) -> Path | None:
    if re.match(r"^[a-z][a-z0-9+.-]*:", link) or link.startswith("#"):
        return None
    target = link.split("#", 1)[0]
    return (path.parent / target).resolve() if target else None


def check_header(path: Path) -> list[str]:
    rel = path.relative_to(REPO)
    fields = header(path)
    if fields is None:
        return [f"{rel}: missing '---' header (see docs/conventions.md)"]
    is_evidence_record = path.is_relative_to(EVIDENCE) and path.parent != EVIDENCE
    is_decision = path.parent.name == "decisions" and DECISION_FILE.match(path.name)
    errors = []
    if is_evidence_record:
        if not DATE.match(fields.get("date", "")):
            errors.append(f"{rel}: evidence needs 'date: YYYY-MM-DD'")
        return errors
    if is_decision:
        if fields.get("status") not in DECISION_STATUSES:
            errors.append(f"{rel}: status must be one of {sorted(DECISION_STATUSES)}")
        if not DATE.match(fields.get("date", "")):
            errors.append(f"{rel}: decision needs 'date: YYYY-MM-DD'")
        return errors
    if fields.get("status") not in DOC_STATUSES:
        errors.append(f"{rel}: status must be one of {sorted(DOC_STATUSES)}")
    if not DATE.match(fields.get("last_verified", "")):
        errors.append(f"{rel}: needs 'last_verified: YYYY-MM-DD'")
    if fields.get("status") == "superseded" and not fields.get("superseded_by"):
        errors.append(f"{rel}: superseded docs need 'superseded_by:'")
    return errors


def main() -> int:
    errors: list[str] = []
    files = markdown_files()

    for path in files:
        if path.is_relative_to(TEMPLATES):
            continue
        if path.is_relative_to(DOCS) or path.is_relative_to(EVIDENCE):
            errors.extend(check_header(path))
        for link in links(path):
            target = local_target(path, link)
            if target is not None and not target.exists():
                errors.append(f"{path.relative_to(REPO)}: broken link -> {link}")

    tracked = {
        p.resolve()
        for p in files
        if (p.is_relative_to(DOCS) or p.is_relative_to(EVIDENCE))
        and not p.is_relative_to(TEMPLATES)
    }
    seen, queue = {INDEX.resolve()}, [INDEX]
    while queue:
        current = queue.pop()
        for link in links(current):
            target = local_target(current, link)
            if target in tracked and target not in seen:
                seen.add(target)
                queue.append(target)
    for orphan in sorted(tracked - seen):
        errors.append(f"{orphan.relative_to(REPO)}: not reachable from docs/docs.md")

    for error in errors:
        print(error)
    print(f"check_docs: {len(files)} files, {len(errors)} problem(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
