---
status: current
last_verified: 2026-09-29
---

# Evidence

Proof that something was measured, tested, or decided. The blueprint's rule: "If someone else can't reproduce what you did from what's in the folder, it doesn't count."

**Rules**

- Files are **append-only**. Once committed, an evidence file isn't edited. Record a new run in a new file. The one exception: a [playbook](../docs/conventions.md#playbooks) with `state: in progress` may be updated until it's `done`.
- Name files `YYYY-MM-DD-short-title.md`, dated by when the thing happened. Put `date:` in the header.
- Record enough to reproduce the result: the command, the model, the llama.cpp commit, the config, and the raw output. Remove secrets.
- Docs cite evidence. Evidence doesn't cite itself as current.

## Folders

| Folder | What goes in it | Template |
|---|---|---|
| `captures/` | Verbatim API responses, test runs, drill results | — |
| `sprintN/` | Playbooks (`.md` source + rendered `.pdf`) and other material for sprint N (see the [roadmap](../docs/project/roadmap.md#sprints)) | [`playbook.md`](../docs/_templates/playbook.md) |
| `benchmarks/` | Committed benchmark runs (`benchmark/results/` is gitignored; copy a run here to keep it) | — |
| `weekly/` | The one-page Friday report, `YYYY-Www.md` | [`weekly-report.md`](../docs/_templates/weekly-report.md) |

Create `benchmarks/` and `weekly/` when you add their first file.

## Log

| Date | Record |
|---|---|
| 2026-09-17 | [Public API end-to-end test](./captures/2026-09-17-public-api-e2e.md): 9/9 pass, verbatim responses for both models |
| 2026-09-18 | [Rig 1 deployment log](./captures/2026-09-18-rig1-deployment-log.md): what was installed and fixed, llama.cpp build details, first worker-direct speeds |
| 2026-09-18 | [Admission gateway concurrency check](./captures/2026-09-18-gateway-concurrency.md): 6×200 + 1×429 (B), 5×200 + 1×429 (A) |
| 2026-09-30 | [Multi-service llama.cpp API playbook](./sprint1/2026-09-30-multi-service-llama-cpp-api.md) ([PDF](./sprint1/2026-09-30-multi-service-llama-cpp-api.pdf)), re-rendered 2026-10-16 in the standard format: live gateway, orchestrator, and both llama-server workers, including the 262,144-token Worker A window measured 2026-09-23 |
| 2026-09-30 | [Public gateway playbook](./sprint1/2026-09-30-public-gateway.md) ([PDF](./sprint1/2026-09-30-public-gateway.pdf)), re-rendered 2026-10-16 in the standard format: exposing a GPU rig behind a locked-down network |
| 2026-10-15 | [NetBird access policies](./captures/2026-10-15-netbird-access-policies.md): `Default` disabled, one-way group policies; public API and operator access checked before and after |
| 2026-10-15 | [Rig 2 inference fix](./captures/2026-10-15-rig2-inference-fix.md): a test `http.server` on port 8081 had the worker crash-looping; worker back up at 8.8 tok/s, orchestrator deployed with Worker B off, then switched to Qwen3.6-35B-A3B at 27 tok/s; Open WebUI connections inspected |
| 2026-10-15 | [Open WebUI connected to Rig 2](./captures/2026-10-15-open-webui-rig2-connection.md): second OpenAI connection with its own key; both connections' model lists and a Rig 2 chat checked from inside the container |
| 2026-10-15 | [Open WebUI admin password reset](./captures/2026-10-15-open-webui-admin-password-reset.md): admin password replaced in the `auth` table; sign-in checked. Password not recorded |
| 2026-10-15 | [Playbook: locking down NetBird with one-way group policies](./sprint4/2026-10-15-netbird-one-way-access.md) ([PDF](./sprint4/2026-10-15-netbird-one-way-access.pdf)), Sprint 4, done |
| 2026-10-15 | [Playbook: inference on both rigs, behind one chat](./sprint4/2026-10-15-inference-on-both-rigs.md) ([PDF](./sprint4/2026-10-15-inference-on-both-rigs.pdf)), Sprint 4, in progress. Includes the 2026-10-16 [model picker screenshot](./sprint4/2026-10-16-open-webui-model-picker.png) |
| 2026-10-16 | [Playbook: the VR experience of the OCS LLM path](./sprint2/2026-09-16-vr-experience.md) ([PDF](./sprint2/2026-09-16-vr-experience.pdf)), Sprint 2, in progress. Headless run of the full arc on 2026-10-14: 100/100 tests, 144 s arc. Not yet run on a headset |

Add a row for each new record, newest last.
