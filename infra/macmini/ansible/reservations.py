#!/usr/bin/env python3
"""Fixed DHCP addresses for the Mac minis on the Flint 2, generated, not typed.

Mac mini N gets 192.168.8.(10+N) on its wired card and 192.168.8.(50+N) on Wi-Fi,
outside the router's pool (.100-.249), so the router never hands them to anything
else. Numbers come from the hostname (ocs-intelligence-macmini-N) or, for one still
named by serial, from ../macminis.csv. MACs come from inventory.py's LAN scan.

  ./reservations.py             # show the entries and the router commands (changes nothing)
  ./reservations.py --apply     # back up the router's DHCP config, add the entries, reload

--apply only adds or updates its own sections (ocs_mmN_wired, ocs_mmN_wifi). It
refuses if a MAC or address is already reserved by something else (the rigs are
at .112 and .213). Reload keeps current leases; a Mac mini moves to its new address
when it next renews (within 12 h, or `sudo networkctl renew <iface>`).
Needs FLINT_ADMIN_PASSWORD in the repo-root .env and sshpass. Guide:
docs/architecture/network.md#dhcp-on-the-flint
"""

from __future__ import annotations

import datetime
import os
import subprocess
import sys
from pathlib import Path

import inventory

ROUTER = "root@192.168.8.1"
PREFIX = "192.168.8."
WIRED_BASE, WIFI_BASE = 10, 50
MAX_NUMBER = 39          # .10-.49 wired, .50-.89 Wi-Fi: both stay below the pool at .100
ENV = Path(__file__).resolve().parents[3] / ".env"


def entries(hosts: dict[str, dict], table: dict[str, int]) -> tuple[list[dict], list[str]]:
    out, skipped = [], []
    for name in sorted(hosts):
        h = hosts[name]
        n = inventory.number_of(name, table)
        if n is None or not 0 <= n <= MAX_NUMBER:
            skipped.append(f"{name}: no Post-it number (rename it, or add its serial to macminis.csv)")
            continue
        label = f"ocs-intelligence-macmini-{n}"
        for kind, base, mac in (("wired", WIRED_BASE, h.get("wired_mac")), ("wifi", WIFI_BASE, h.get("wifi_mac"))):
            if mac:
                out.append({"section": f"ocs_mm{n}_{kind}", "name": label if kind == "wifi" else f"{label}-wired",
                            "mac": mac.upper(), "ip": f"{PREFIX}{base + n}", "host": name})
    return out, skipped


def uci_script(es: list[dict]) -> str:
    lines = []
    for e in es:
        s = e["section"]
        lines += [f"uci set dhcp.{s}=host", f"uci set dhcp.{s}.name='{e['name']}'",
                  f"uci set dhcp.{s}.mac='{e['mac']}'", f"uci set dhcp.{s}.ip='{e['ip']}'"]
    return "\n".join(lines)


def router(cmd: str) -> str:
    pw = next((l.split("=", 1)[1] for l in ENV.read_text().splitlines()
               if l.startswith("FLINT_ADMIN_PASSWORD=")), "")
    if not pw or "CHANGE_ME" in pw:
        sys.exit(f"FLINT_ADMIN_PASSWORD is not set in {ENV}")
    r = subprocess.run(["sshpass", "-e", "ssh", "-o", "PubkeyAuthentication=no", "-o", "ConnectTimeout=5",
                        ROUTER, cmd], capture_output=True, text=True, env={**os.environ, "SSHPASS": pw})
    if r.returncode:
        sys.exit(f"router command failed ({r.returncode}): {r.stderr.strip()}")
    return r.stdout


def existing(dump: str) -> list[dict]:
    """Host sections from `uci show dhcp` output: [{section, mac, ip}]."""
    hosts: dict[str, dict] = {}
    for line in dump.splitlines():
        key, _, val = line.partition("=")
        parts = key.split(".")
        if len(parts) == 2 and val == "host":
            hosts.setdefault(parts[1], {"section": parts[1]})
        elif len(parts) == 3 and parts[2] in ("mac", "ip"):
            hosts.setdefault(parts[1], {"section": parts[1]})[parts[2]] = val.strip("'").upper()
    return list(hosts.values())


def conflicts(es: list[dict], current: list[dict]) -> list[str]:
    ours = {e["section"] for e in es}
    found = []
    for c in current:
        if c["section"] in ours:
            continue
        for e in es:
            if c.get("mac") == e["mac"] or c.get("ip") == e["ip"].upper():
                found.append(f"{e['section']} ({e['mac']} -> {e['ip']}) clashes with existing {c}")
    return found


def main() -> None:
    hosts = inventory.discover()
    table = inventory.load_table()
    es, skipped = entries(hosts, table)
    print(f"{'section':18} {'name':36} {'MAC':18} IP")
    for e in es:
        print(f"{e['section']:18} {e['name']:36} {e['mac']:18} {e['ip']}")
    for s in skipped:
        print("skipped:", s)
    if not es:
        return
    print("\nRouter commands:\n" + uci_script(es) + "\nuci commit dhcp\n/etc/init.d/dnsmasq reload")
    clash = conflicts(es, existing(router("uci show dhcp")))   # read-only
    if clash:
        sys.exit("\nClashes with the router's existing reservations, not applied:\n" + "\n".join(clash))
    print("\nNo clashes with the router's existing reservations.")
    if "--apply" not in sys.argv:
        print("Nothing changed. Run with --apply to back up and apply.")
        return
    stamp = datetime.datetime.now().strftime("%Y-%m-%d-%H%M%S")
    print(router(f"uci export dhcp > /root/dhcp.backup-{stamp} && echo backup /root/dhcp.backup-{stamp}").strip())
    router(uci_script(es) + "\nuci commit dhcp\n/etc/init.d/dnsmasq reload")
    after = existing(router("uci show dhcp"))
    applied = {c["section"]: c for c in after}
    for e in es:
        c = applied.get(e["section"], {})
        ok = c.get("mac") == e["mac"] and c.get("ip") == e["ip"]
        print(("ok      " if ok else "MISSING ") + f"{e['section']} {e['mac']} -> {e['ip']}")
    print(f"Undo: ssh {ROUTER} 'uci import dhcp < /root/dhcp.backup-{stamp} && uci commit dhcp && /etc/init.d/dnsmasq reload'")


if __name__ == "__main__":
    main()
