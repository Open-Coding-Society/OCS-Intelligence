"""Offline tests for scripts/build_playbook.py header checks. No pandoc or WeasyPrint needed."""

from __future__ import annotations

import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("build_playbook", REPO / "scripts" / "build_playbook.py")
bp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bp)

GOOD = """---
type: playbook
date: 2026-10-15
title: A title
sprint: 4
state: in progress   # comment
---

# A title
"""


def write(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text)
    return path


def test_header_strips_comments(tmp_path):
    fields = bp.header(write(tmp_path, "2026-10-15-x.md", GOOD))
    assert fields["state"] == "in progress"
    assert fields["type"] == "playbook"


def test_good_playbook_passes(tmp_path, monkeypatch):
    monkeypatch.setattr(bp, "REPO", tmp_path)
    path = write(tmp_path, "2026-10-15-x.md", GOOD)
    assert bp.check(path, bp.header(path)) == []


def test_bad_state_and_name_fail(tmp_path, monkeypatch):
    monkeypatch.setattr(bp, "REPO", tmp_path)
    path = write(tmp_path, "notes.md", GOOD.replace("in progress", "wip"))
    errors = " ".join(bp.check(path, bp.header(path)))
    assert "state must be one of" in errors
    assert "YYYY-MM-DD-short-title.md" in errors


def test_template_names_no_authors():
    assert "authors" not in bp.header(REPO / "docs" / "_templates" / "playbook.md")


def test_template_has_every_required_field():
    fields = bp.header(REPO / "docs" / "_templates" / "playbook.md")
    for key in bp.REQUIRED + ("type", "subtitle"):
        assert key in fields
