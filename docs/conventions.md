---
status: current
last_verified: 2026-09-29
---

# Documentation conventions

How docs in this repo are organized, and how to add or change one. Read this before writing a new doc. The same rules apply to people and to coding agents.

## Where we took the ideas from

We borrow from these sources but don't follow any of them exactly. Where we differ, it says so below.

| Idea | Source | What we took |
|---|---|---|
| Four kinds of docs | [Diátaxis](https://diataxis.fr/) | The rule for which folder a doc goes in (see [Where a new doc goes](#where-a-new-doc-goes)). |
| Decision records | [MADR](https://adr.github.io/madr/) | `docs/decisions/NNNN-title.md`, a status per decision, and considered options with pros and cons. We use a trimmed template. |
| Agent instructions | [AGENTS.md](https://agents.md/) | One `AGENTS.md` at the repo root. `CLAUDE.md` only imports it, so there's one copy. |
| Docs as code | [Google documentation guide](https://google.github.io/styleguide/docguide/best_practices.html) | Update the docs in the same commit as the code change. Minimal, current docs beat thorough, stale ones. Delete dead docs (here: move them to the archive). |
| Evidence folder | [Blueprint v2.2](./sources/2026-09-11-blueprint-v2.2.md), "How to use this document" and §6 | Evidence is committed next to the code, dated, and never edited after the fact. |

## The rules

1. **Each fact lives in one place.** Other docs link to that place instead of copying it. The canonical homes:

   | Fact | Only lives in |
   |---|---|
   | What is running right now | [`status.md`](./status.md) |
   | Hosts, IPs, ports, on-disk paths | [`reference/hosts.md`](./reference/hosts.md) |
   | GPU inventory and PCIe topology | [`architecture/hardware.md`](./architecture/hardware.md) |
   | Wait-line capacity (in flight and waiting, per model) | [`architecture/gateway.md`](./architecture/gateway.md) |
   | API endpoints, models, error codes | [`reference/api.md`](./reference/api.md) |
   | Environment variables | [`reference/configuration.md`](./reference/configuration.md) |
   | Why we chose X over Y | [`decisions/`](./decisions/decisions.md) |
   | Measured numbers and verbatim captures | [`evidence/`](../evidence/evidence.md) |
   | Terms | [`project/glossary.md`](./project/glossary.md) |

2. **Every doc starts with a header.**

   ```yaml
   ---
   status: current        # draft | current | superseded
   last_verified: 2026-09-29
   ---
   ```

   - `draft`: incomplete, or not yet checked against reality. Useful but don't rely on it blindly.
   - `current`: believed accurate as of `last_verified`.
   - `superseded`: kept for history. Add `superseded_by: <path>` and move it to [`archive/`](./archive/archive.md).
   - `last_verified`: the last date someone **checked the content against the thing it describes**: the code, the live machines, or the source document. Fixing typos doesn't count. **Never set it to today unless you checked today.** Agents trust this field.

   Decision records use `status: proposed | accepted | rejected | superseded` and `date:` in place of `last_verified` (see the [template](./_templates/decision.md)). Evidence files use only `date:`, because they are records of one moment and are never updated. [Playbooks](#playbooks) add a few fields and stay editable until they're `done`.

3. **Sort by how often something changes.** Design docs (`architecture/`, `decisions/`) never say "right now" or "tonight". Anything time-sensitive goes in `status.md` or `evidence/`.

4. **Folder index files are named after their folder** (`decisions/decisions.md`, `sources/sources.md`), not `README.md`. The one exception is the repo-root `README.md`, which GitHub shows on the project page. (Trade-off: GitHub only auto-renders `README.md` when you browse a folder, so open the index file yourself.)

5. **Every doc must be reachable from [`docs.md`](./docs.md)**, either directly or through a folder index. Unlinked docs get lost.

6. **Any change from the blueprint needs a decision record.** If what we build differs from [Blueprint v2.2](./sources/2026-09-11-blueprint-v2.2.md), write a decision record explaining why. Our mentor reviews these.

7. **No secrets, ever.** Write `<redacted>` or `CHANGE_ME`. This repo is public.

## Where a new doc goes

Ask what the reader is trying to do:

| The reader wants to… | Kind (Diátaxis) | Folder | Template |
|---|---|---|---|
| learn the project from zero, step by step | tutorial | `guides/` (`getting-started.md`) | [`guide.md`](./_templates/guide.md) |
| get a specific task done ("set up Copilot", "deploy the gateway") | how-to | `guides/` for users, `operations/` for operators | [`guide.md`](./_templates/guide.md) |
| look up a fact (a port, an env var, an error code) | reference | `reference/` | none, use a table |
| understand how something works or why | explanation | `architecture/` | [`doc.md`](./_templates/doc.md) |
| know why we picked X over Y | explanation | `decisions/` | [`decision.md`](./_templates/decision.md) |
| know the project's scope, plan, or people | — | `project/` | [`doc.md`](./_templates/doc.md) |
| see proof that something was measured or tested | — | `../evidence/` | [`weekly-report.md`](./_templates/weekly-report.md), or a dated capture |
| read an outside document (mentor spec, slides) | — | `sources/` | [`source-summary.md`](./_templates/source-summary.md) |

Security (`security/`) and testing (`testing/`) get their own folders because the blueprint treats them as their own review areas. They hold explanation and reference docs about those topics.

## Adding a doc

1. Pick the folder with the table above, copy the template, and name the file in `kebab-case.md`.
2. Fill in the header. Start with `status: draft` if you haven't checked the content against reality.
3. Link it from [`docs.md`](./docs.md) or from its folder index.
4. Run `python3 scripts/check_docs.py`. It checks headers, broken links, and that every doc is reachable from the index.
5. Commit the doc together with the code change it describes.

## Playbooks

A playbook is the write-up of one sprint item: what was wrong, what we did, how to check it, and what's still open. Every playbook uses the same format, so they read the same and render to the same PDF.

- **Where:** `evidence/sprintN/YYYY-MM-DD-short-title.md`, dated by the first day of the work, with the rendered `.pdf` next to it. Images go next to the playbook or in `assets/`.
- **Start from** [`_templates/playbook.md`](./_templates/playbook.md). It has the header and the section order: summary paragraph, At a glance, Before, What we did, How to check it, Pitfalls, Open items, Sources. Leave out a section only if it would be empty.
- **Header:** `type: playbook`, `date`, `title`, `subtitle`, `sprint`, `state`. `state` is `in progress` or `done`. Playbooks carry no author names: the work is the project's, and every PDF is tagged **PROMX-OCS**.
- **Editable until done.** An `in progress` playbook may be updated as the work moves. Once it's `done`, it's frozen like any other evidence. Changes after that go in a new dated file.
- **Facts the team reported** but nobody captured at the time are marked as reported, with the date. They aren't presented as measured.
- **Render** with `python3 scripts/build_playbook.py <file.md>` (or `--all`). It needs `pandoc` and `pip install weasyprint`. Commit the `.md` and the `.pdf` together. The style is the Illuminati palette from Yash's VS Code theme, in [`scripts/playbook/style.css`](../scripts/playbook/style.css). Relative links become GitHub links in the PDF. GitHub alerts (`> [!NOTE]`, `[!WARNING]`, …) become callouts.
- **Link it** from the log in [`evidence/evidence.md`](../evidence/evidence.md) and from the sprint's row in the [roadmap](./project/roadmap.md#sprints).

## File naming

- Docs: `kebab-case.md`.
- Decisions: `NNNN-short-title.md`, numbered in order and never reused.
- Sources and evidence: `YYYY-MM-DD-short-title.ext`, dated by when the thing happened.
- Weekly reports: `evidence/weekly/YYYY-Www.md` (ISO week, e.g. `2026-W40`).
