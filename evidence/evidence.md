---
status: current
last_verified: 2026-09-29
---

# Evidence

Proof that something was measured, tested, or decided. The blueprint's rule: "If someone else can't reproduce what you did from what's in the folder, it doesn't count."

**Rules**

- Files are **append-only**. Once committed, an evidence file isn't edited. Record a new run in a new file.
- Name files `YYYY-MM-DD-short-title.md`, dated by when the thing happened. Put `date:` in the header.
- Record enough to reproduce the result: the command, the model, the llama.cpp commit, the config, and the raw output. Remove secrets.
- Docs cite evidence. Evidence doesn't cite itself as current.

## Folders

| Folder | What goes in it | Template |
|---|---|---|
| `captures/` | Verbatim API responses, test runs, drill results | — |
| `week1/` | Week 1 playbooks (PDF) | — |
| `benchmarks/` | Committed benchmark runs (`benchmark/results/` is gitignored; copy a run here to keep it) | — |
| `weekly/` | The one-page Friday report, `YYYY-Www.md` | [`weekly-report.md`](../docs/_templates/weekly-report.md) |

Create `benchmarks/` and `weekly/` when you add their first file.

## Log

| Date | Record |
|---|---|
| 2026-09-17 | [Public API end-to-end test](./captures/2026-09-17-public-api-e2e.md): 9/9 pass, verbatim responses for both models |
| 2026-09-18 | [Rig 1 deployment log](./captures/2026-09-18-rig1-deployment-log.md): what was installed and fixed, llama.cpp build details, first worker-direct speeds |
| 2026-09-18 | [Admission gateway concurrency check](./captures/2026-09-18-gateway-concurrency.md): 6×200 + 1×429 (B), 5×200 + 1×429 (A) |
| 2026-09-30 | [Multi-service llama.cpp API playbook](./week1/Multi-Service%20llama.cpp%20API%20Playbook.pdf): live gateway, orchestrator, and both llama-server workers, including the 262,144-token Worker A window measured 2026-09-23 |

Add a row for each new record, newest last.
