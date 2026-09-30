---
status: current
last_verified: 2026-09-29
---

# Getting started

For a new team member. In about 30 minutes you'll understand what we're building, make your first request to our own GPUs, and know where everything lives.

## 1. Understand the mission (5 min)

Read the first two sections of the [charter](../project/charter.md). In one line: **free coding help for every student, served from donated GPUs, built and run by students, with evidence for every claim.**

## 2. See the system (10 min)

Read the [architecture overview](../architecture/overview.md). Keep this picture in mind:

```text
You ─HTTPS─▶ EC2 (Nginx → wait line) ─NetBird─▶ GPU rig (router → llama.cpp on GTX 1070s)
```

## 3. Make your first request (10 min)

```bash
git clone https://github.com/Open-Coding-Society/OCS-Intelligence
cd OCS-Intelligence
cp .env.example .env          # ask an operator for OCS_API_KEY and put it here
python3 scripts/demo.py --pause
```

`demo.py` walks through health, auth, a fast completion, and seven requests at once, so you can watch the wait line send back a 429. Then try the [API guide](./using-the-api.md) yourself.

## 4. Run the tests (5 min)

```bash
python3 -m pip install pytest fastapi httpx -r benchmark/requirements.txt
python3 -m pytest -q
python3 scripts/check_docs.py
```

Everything should pass without network or GPU access.

## 5. Know where things live

| I want to… | Go to |
|---|---|
| find any doc | [docs index](../docs.md) |
| know what's running now | [status](../status.md) |
| know why something is built this way | [decisions](../decisions/decisions.md) |
| know what we're doing this week | [roadmap](../project/roadmap.md) |
| get a shell on the machines (operators) | [NetBird access](./netbird-access.md) |
| write or change a doc | [conventions](../conventions.md) |

## 6. How we work

- **Evidence or it didn't happen.** Every task ends with a file, a number, a log, or a screenshot in [`evidence/`](../../evidence/evidence.md).
- **Open an issue before asking for help:** include what you expected, what happened, how to reproduce it, and what you tried.
- **Update docs in the same commit as the code.**
- **Never commit secrets.** The repo is public.
