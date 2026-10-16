---
date: 2026-10-15
---

# Open WebUI connected to Rig 2 (2026-10-15)

Changed live over NetBird SSH on Rig 1 (`ocs-intelligence-rig`) and Rig 2 (`ocs-intelligence-rig2`) from the `Yash WSL` peer, about 19:15 PDT. This is a record: don't edit it. Why: [decision 0009](../../docs/decisions/0009-rig2-moe-behind-open-webui.md). The earlier read-only look at Open WebUI is in [the Rig 2 record](./2026-10-15-rig2-inference-fix.md#also-checked-open-webui-on-rig-1-read-only).

## What was changed

1. **A dedicated key for Open WebUI → Rig 2**, generated on the operator machine (`sk-ocs-owui-rig2-` + 48 hex characters). It was appended to `PUBLIC_API_KEYS` in Rig 2's `/etc/ocs-orchestrator/orchestrator.env`, alongside the temporary key, and `ocs-orchestrator` was restarted. The key isn't recorded anywhere in this repo.
2. **A backup of Open WebUI's database**, made with SQLite's online backup: `/app/backend/data/webui.db.bak-20261015` inside the `open-webui` volume (on the host: `/var/lib/docker/volumes/open-webui/_data/`).
3. **A second OpenAI connection** written to Open WebUI's `config` table (`openai.api_base_urls`, `openai.api_keys`, `openai.api_configs`): index 1, `http://100.75.127.192:9000/v1`, enabled, no prefix, no model filter. Connection 0 (`https://ai.opencodingsociety.com/v1`) was left as it was.
4. `docker restart open-webui`. Healthy again within the wait loop.

## Checked

From inside the `open-webui` container, using the URLs and keys Open WebUI has saved:

```text
0 https://ai.opencodingsociety.com/v1 enabled=True ['qwen3.8:27b', 'qwen2.5:0.5b']
1 http://100.75.127.192:9000/v1 enabled=True ['qwen3.6:35b-a3b']
chat via saved rig2 connection: qwen3.6:35b-a3b 'ok' gen tok/s 27.8
```

Not checked: the model dropdown in a browser, as admin or as a regular user. Open WebUI fetches model lists when the page asks for them, and no session was used here.

## How to undo

In Open WebUI: Admin Settings → Connections → OpenAI → delete the `100.75.127.192` connection. Or stop the container, copy `webui.db.bak-20261015` back over `webui.db`, and start it again. That also reverts any other settings changed since this backup.
