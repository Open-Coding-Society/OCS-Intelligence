---
type: playbook
date: YYYY-MM-DD           # when the work happened (the first day, if it spanned several)
title: Short title
subtitle: One line on what this playbook gets the reader.
sprint: N
state: in progress         # in progress | done. Editable until done, frozen after.
---

# Short title

One paragraph: what was done, why it mattered, and where things stand now. Someone who reads only this paragraph should know the outcome.

## At a glance

| | |
|---|---|
| Goal | What this sprint item set out to do |
| Outcome | What is true now. For `in progress`, what works so far |
| Where | Machines, services, or files touched |
| Why | Link to the decision record, if there is one |

## Before

What was wrong or missing, with the symptoms someone would actually see.

## What we did

Numbered steps, in the order they were done. Commands go in fenced code blocks with a language. Keep secrets out: write `<redacted>` or `CHANGE_ME`.

1. First step.

   ```bash
   command --flag
   ```

2. Second step.

> [!NOTE]
> Callouts use GitHub's alert syntax: `[!NOTE]`, `[!TIP]`, `[!IMPORTANT]`, `[!WARNING]`, `[!CAUTION]`. They render on GitHub and in the PDF.

## How to check it

| Check | Pass looks like | If it fails |
|---|---|---|
| `command` | Expected output | Where to look next |

## Pitfalls

Real failures from this work, so nobody has to rediscover them.

| Symptom | Cause | Fix |
|---|---|---|
| What you see | Why | What to do |

## Open items

What isn't done or wasn't checked. Name what would close each one.

- Item.

## Sources

Captures, decisions, and commits this playbook is built from. Facts the team reported but nobody recorded at the time are marked as reported, with the date.

- [Some capture](../../evidence/evidence.md)
