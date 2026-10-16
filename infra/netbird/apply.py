#!/usr/bin/env python3
"""Compare or apply the NetBird access policies in acl.json.

  python3 infra/netbird/apply.py check        # report differences from acl.json (read-only)
  python3 infra/netbird/apply.py apply        # create missing groups and policies
  python3 infra/netbird/apply.py default off  # disable the built-in All<->All policy ("on" to roll back)

Needs NETBIRD_API_TOKEN (environment or repo-root .env) from an admin service user.
`apply` only creates. It never deletes, never edits existing policies, and never
changes group membership: people are added to groups in the dashboard.
Standard library only.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

API = "https://api.netbird.io/api"
HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent


def load_token() -> str:
    token = os.environ.get("NETBIRD_API_TOKEN")
    env = REPO / ".env"
    if not token and env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("NETBIRD_API_TOKEN="):
                token = line.split("=", 1)[1].strip()
    if not token or "CHANGE_ME" in token:
        sys.exit("NETBIRD_API_TOKEN is not set (see .env.example)")
    return token


def api(method: str, path: str, body: object = None) -> object:
    req = urllib.request.Request(
        API + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": "Token " + load_token(), "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read() or "null")
    except urllib.error.HTTPError as e:
        sys.exit(f"{method} {path} -> {e.code} {e.read().decode()}")


def rule_summary(rule: dict) -> dict:
    """The parts of a live policy rule that acl.json describes, with group names instead of IDs."""
    return {
        "sources": sorted(g["name"] for g in rule.get("sources") or []),
        "destinations": sorted(g["name"] for g in rule.get("destinations") or []),
        "protocol": rule["protocol"],
        "ports": sorted(rule.get("ports") or []) or None,
        "bidirectional": rule["bidirectional"],
    }


def spec_summary(spec: dict) -> dict:
    return {
        "sources": sorted(spec["sources"]),
        "destinations": sorted(spec["destinations"]),
        "protocol": spec["protocol"],
        "ports": sorted(spec["ports"] or []) or None,
        "bidirectional": spec["bidirectional"],
    }


def diff(acl: dict, groups: list[dict], policies: list[dict]) -> list[str]:
    """Human-readable differences between acl.json and the live account."""
    out = []
    live_groups = {g["name"]: sorted(p["name"] for p in g.get("peers") or []) for g in groups}
    for name, spec in acl["groups"].items():
        if name not in live_groups:
            out.append(f"group {name}: missing")
        elif live_groups[name] != sorted(spec["peers"]):
            out.append(f"group {name}: members are {live_groups[name]}, acl.json lists {sorted(spec['peers'])}")
    live_policies = {p["name"]: p for p in policies}
    for spec in acl["policies"]:
        live = live_policies.get(spec["name"])
        if live is None:
            out.append(f"policy {spec['name']}: missing")
        elif not live["enabled"]:
            out.append(f"policy {spec['name']}: disabled")
        elif [rule_summary(r) for r in live["rules"]] != [spec_summary(spec)]:
            out.append(f"policy {spec['name']}: rules differ: {[rule_summary(r) for r in live['rules']]}")
    default = live_policies.get("Default")
    if default and default["enabled"] != acl["default_policy_enabled"]:
        out.append(f"policy Default: enabled={default['enabled']}, acl.json wants {acl['default_policy_enabled']}")
    return out


def policy_payload(spec: dict, group_ids: dict[str, str]) -> dict:
    rule = {
        "name": spec["name"], "enabled": True, "action": "accept",
        "bidirectional": spec["bidirectional"], "protocol": spec["protocol"],
        "sources": [group_ids[g] for g in spec["sources"]],
        "destinations": [group_ids[g] for g in spec["destinations"]],
    }
    if spec["ports"]:
        rule["ports"] = spec["ports"]
    return {"name": spec["name"], "description": spec["description"], "enabled": True, "rules": [rule]}


def apply(acl: dict) -> None:
    peers = {p["name"]: p["id"] for p in api("GET", "/peers")}
    group_ids = {g["name"]: g["id"] for g in api("GET", "/groups")}
    for name, spec in acl["groups"].items():
        if name not in group_ids:
            group_ids[name] = api("POST", "/groups", {"name": name, "peers": [peers[p] for p in spec["peers"]]})["id"]
            print("created group", name)
    existing = {p["name"] for p in api("GET", "/policies")}
    for spec in acl["policies"]:
        if spec["name"] not in existing:
            api("POST", "/policies", policy_payload(spec, group_ids))
            print("created policy", spec["name"])


def set_default(enabled: bool) -> None:
    p = next(p for p in api("GET", "/policies") if p["name"] == "Default")
    rules = [{k: v for k, v in r.items() if k not in ("sources", "destinations")}
             | {"sources": [g["id"] for g in r["sources"]], "destinations": [g["id"] for g in r["destinations"]]}
             for r in p["rules"]]
    api("PUT", "/policies/" + p["id"],
        {"name": p["name"], "description": p.get("description", ""), "enabled": enabled, "rules": rules})
    print("Default policy enabled =", enabled)


def main(argv: list[str]) -> None:
    acl = json.loads((HERE / "acl.json").read_text())
    cmd = argv[0] if argv else "check"
    if cmd == "check":
        problems = diff(acl, api("GET", "/groups"), api("GET", "/policies"))
        print("\n".join(problems) or "live NetBird config matches acl.json")
        sys.exit(1 if problems else 0)
    elif cmd == "apply":
        apply(acl)
    elif cmd == "default" and argv[1:] in (["on"], ["off"]):
        set_default(argv[1] == "on")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
