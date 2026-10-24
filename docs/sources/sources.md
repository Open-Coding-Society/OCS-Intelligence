---
status: current
last_verified: 2026-10-23
---

# Sources

Original documents the project builds from: the mentor's specs, presentation decks, meeting handouts. **The originals are never edited.** Each one has a `.md` summary next to it, so people and agents can find what's inside without opening a PDF or pptx, and so each part of the source can be traced to the doc that handles it.

| Date | Source | Author | Summary |
|---|---|---|---|
| 2026-09-11 | Build Blueprint, Student Edition v2.2 + tech spec PROMX-OCS-001 Rev 0.1 ([pdf](./2026-09-11-blueprint-v2.2.pdf)) | Eduardo Revollo (Prometheus), mentor | [summary](./2026-09-11-blueprint-v2.2.md) |
| 2026-09-28 | Week 0+1 intro deck presented to the mentor ([pptx](./2026-09-28-week0-1-mentor-deck.pptx)) | OCS Intelligence team | [summary](./2026-09-28-week0-1-mentor-deck.md) |
| 2026-10-14 | Deep audit deck ([pdf](./2026-10-14-mentor-audit-deck.pdf)) and open-issues report with the fix order ([pdf](./2026-10-14-mentor-audit-open-issues.pdf)) | Eddie Revollo (Prometheus), mentor | [summary](./2026-10-14-mentor-audit.md) |
| 2026-10-20 | Mentor meeting notes and report ([issue #28](https://github.com/Open-Coding-Society/OCS-Intelligence/issues/28)) | OCS Intelligence team; follow-up by John Mortensen | [summary](./2026-10-20-mentor-meeting-notes.md) |

## Adding a source

1. Save the original here as `YYYY-MM-DD-short-name.ext`, dated by when it was issued or presented.
2. Copy [`_templates/source-summary.md`](../_templates/source-summary.md) to `YYYY-MM-DD-short-name.md` next to it and fill it in.
3. Add a row to the table above.
4. When a new revision of a source replaces an old one, keep both. Mark the old summary `status: superseded` with `superseded_by:`.
