---
date: 2026-10-15
---

# Open WebUI admin password reset (2026-10-15)

Done over NetBird SSH on Rig 1 from the `Yash WSL` peer, about 19:40 PDT, at Yash Parikh's request. The previous password wasn't known to the operator. This is a record: don't edit it. The new password is deliberately **not** recorded here, because this repo is public. Ask a team lead.

- Open WebUI has one admin account (`ocsintelligence@gmail.com`, "OCS Intelligence") and six regular users. Only the admin was changed.
- A new bcrypt hash was written to the admin's row in the `auth` table of `/app/backend/data/webui.db`, inside the `open-webui` container. No restart. The password was set twice: the second value replaced the first a few minutes later.
- Checked: `POST http://localhost:3000/api/v1/auths/signin` with the new password returned a token with `role: admin`.
- The new password is short and easy to guess ([threat model](../../docs/security/threat-model.md)). Change it to a strong one.
