"""Offline tests for infra/netbird: acl.json invariants and apply.py's diff/payload logic. No network."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent / "infra" / "netbird"
spec = importlib.util.spec_from_file_location("netbird_apply", HERE / "apply.py")
nb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nb)

ACL = json.loads((HERE / "acl.json").read_text())


def live_from_acl(acl: dict) -> tuple[list[dict], list[dict]]:
    """Fake API responses that exactly match acl.json."""
    groups = [{"id": f"g-{n}", "name": n, "peers": [{"name": p} for p in s["peers"]]} for n, s in acl["groups"].items()]
    policies = [{"name": p["name"], "enabled": True, "rules": [{
        "sources": [{"name": g} for g in p["sources"]],
        "destinations": [{"name": g} for g in p["destinations"]],
        "protocol": p["protocol"], "ports": p["ports"], "bidirectional": p["bidirectional"],
    }]} for p in acl["policies"]]
    policies.append({"name": "Default", "enabled": acl["default_policy_enabled"], "rules": []})
    return groups, policies


def test_nothing_can_reach_outbound_only_peers():
    for p in ACL["policies"]:
        assert "outbound-only" not in p["destinations"], p["name"]
        if "outbound-only" in p["sources"]:
            assert p["bidirectional"] is False, p["name"]
    assert ACL["default_policy_enabled"] is False


def test_gateway_can_reach_orchestrator():
    rule = next(p for p in ACL["policies"] if p["name"] == "gateway-to-rigs")
    assert "9000" in rule["ports"] and rule["destinations"] == ["ocs-rigs"]


def test_policies_reference_defined_groups():
    for p in ACL["policies"]:
        assert set(p["sources"]) | set(p["destinations"]) <= set(ACL["groups"]), p["name"]


def test_diff_is_empty_when_live_matches():
    assert nb.diff(ACL, *live_from_acl(ACL)) == []


def test_diff_reports_missing_policy_member_change_and_default():
    groups, policies = live_from_acl(ACL)
    policies = [p for p in policies if p["name"] != "gateway-to-rigs"]
    next(p for p in policies if p["name"] == "Default")["enabled"] = True
    next(g for g in groups if g["name"] == "outbound-only")["peers"].append({"name": "new-laptop"})
    problems = nb.diff(ACL, groups, policies)
    assert "policy gateway-to-rigs: missing" in problems
    assert any(s.startswith("group outbound-only: members") for s in problems)
    assert any(s.startswith("policy Default: enabled=True") for s in problems)


def test_diff_reports_changed_rule():
    groups, policies = live_from_acl(ACL)
    next(p for p in policies if p["name"] == "outbound-only-to-infra")["rules"][0]["bidirectional"] = True
    assert any(s.startswith("policy outbound-only-to-infra: rules differ") for s in nb.diff(ACL, groups, policies))


def test_policy_payload_uses_group_ids_and_omits_ports_for_all():
    ids = {n: f"id-{n}" for n in ACL["groups"]}
    allp = nb.policy_payload(next(p for p in ACL["policies"] if p["protocol"] == "all"), ids)
    rule = allp["rules"][0]
    assert rule["sources"] == ["id-outbound-only"] and "ports" not in rule and rule["bidirectional"] is False
    tcp = nb.policy_payload(next(p for p in ACL["policies"] if p["name"] == "gateway-to-rigs"), ids)
    assert tcp["rules"][0]["ports"] == ["9000", "3000"]
