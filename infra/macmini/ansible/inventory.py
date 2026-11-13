#!/usr/bin/env python3
"""Ansible inventory that finds the Mac minis on the LAN, so no IPs are written down.

Every run: try SSH (port 22) on each address of OCS_LAN (default 192.168.8.0/24),
log in as ocs with your key, and keep the machines that report Macmini7,1.
Each one is named by its hostname, and Ansible connects to its wired address
when it has one (the Wi-Fi address otherwise), as reported by the machine.

Host keys are remembered by machine name, not IP, in ~/.ssh/known_hosts_ocs_macminis
(DHCP moves addresses between machines, so an IP-keyed entry would go stale).
A machine's key is trusted on first sight; after that, a machine claiming a
known name with a different key (reflashed, or not ours) is left out and
reported. To accept a reflashed one, delete its line from that file.

  ./inventory.py --list            # what Ansible sees (JSON)
  ./inventory.py --table           # the same, readable

Per-machine settings (e.g. macmini_number for one that hasn't been renamed yet)
go in host_vars/<hostname>.yml. Standard library only.
"""

from __future__ import annotations

import ipaddress
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

LAN = os.environ.get("OCS_LAN", "192.168.8.0/24")
USER = "ocs"
MODEL = "Macmini7,1"
KNOWN = Path(os.environ.get("OCS_KNOWN_HOSTS", Path.home() / ".ssh/known_hosts_ocs_macminis"))
# hostname, model, then "iface addr/prefix" for each IPv4 address
PROBE = (
    "hostname; cat /sys/class/dmi/id/product_name; "
    "ip -o -4 addr show scope global | awk '{print $2, $4}'"
)


def ssh_open(ip: str) -> bool:
    try:
        with socket.create_connection((ip, 22), timeout=1.0):
            return True
    except OSError:
        return False


def load_known() -> dict[str, tuple[str, str]]:
    """name -> (key type, key) from KNOWN."""
    known = {}
    if KNOWN.exists():
        for line in KNOWN.read_text().splitlines():
            parts = line.split()
            if len(parts) == 3 and not line.startswith("#"):
                known[parts[0]] = (parts[1], parts[2])
    return known


def keyscan(ip: str) -> tuple[str, str] | None:
    try:
        out = subprocess.run(["ssh-keyscan", "-T", "3", "-t", "ed25519", ip],
                             capture_output=True, text=True, timeout=10).stdout
    except subprocess.TimeoutExpired:
        return None
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 3 and not line.startswith("#"):
            return parts[1], parts[2]
    return None


def probe(ip: str, name_of_key: dict[str, str]) -> dict | None:
    """The Mac mini at ip, or None (not a Mac mini, our key refused, or no answer).

    Connects pinned to the key ssh-keyscan just saw, so what it reports came
    from the machine holding that key. Whether the key is trusted for that name
    is decided afterwards, in discover().
    """
    key = keyscan(ip)
    if not key:
        return None
    alias = name_of_key.get(key[1], f"unverified-{ip}")
    with tempfile.NamedTemporaryFile("w", suffix=".known_hosts") as kh:
        kh.write(f"{alias} {key[0]} {key[1]}\n")
        kh.flush()
        try:
            out = subprocess.run(
                ["ssh", "-n", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5",
                 "-o", "StrictHostKeyChecking=yes", "-o", f"UserKnownHostsFile={kh.name}",
                 "-o", "GlobalKnownHostsFile=/dev/null", "-o", f"HostKeyAlias={alias}",
                 "-o", "LogLevel=ERROR", f"{USER}@{ip}", PROBE],
                capture_output=True, text=True, timeout=15).stdout.splitlines()
        except subprocess.TimeoutExpired:
            return None
    if len(out) < 2 or out[1].strip() != MODEL:
        return None
    addrs = dict(line.split()[:2] for line in out[2:] if len(line.split()) >= 2)
    wired = [a.split("/")[0] for i, a in addrs.items() if i.startswith("en")]
    wifi = [a.split("/")[0] for i, a in addrs.items() if i.startswith("wl")]
    return {"name": out[0].strip(), "found_at": ip, "key": key,
            "ansible_host": (wired or wifi or [ip])[0],
            "wired_ip": wired[0] if wired else None,
            "wifi_ip": wifi[0] if wifi else None}


def discover() -> dict[str, dict]:
    known = load_known()
    name_of_key = {k: n for n, (_, k) in known.items()}
    ips = [str(h) for h in ipaddress.ip_network(LAN).hosts()]
    with ThreadPoolExecutor(64) as pool:
        open_ips = [ip for ip, ok in zip(ips, pool.map(ssh_open, ips)) if ok]
        found = [h for h in pool.map(lambda ip: probe(ip, name_of_key), open_ips) if h]
    hosts: dict[str, dict] = {}
    refused = []
    for h in found:  # a machine on wired and Wi-Fi answers twice; keep one
        name, key = h["name"], h["key"]
        if name in known and known[name] != key:
            refused.append(f"{name} at {h['found_at']}")
            continue
        old = name_of_key.get(key[1])
        if old and old != name:  # renamed (e.g. by the FIX stick or --tags hostname)
            known.pop(old, None)
        known[name] = key
        hosts.setdefault(name, h)
    KNOWN.parent.mkdir(mode=0o700, exist_ok=True)
    KNOWN.write_text("".join(f"{n} {t} {k}\n" for n, (t, k) in sorted(known.items())))
    if refused:
        print(f"LEFT OUT, host key differs from the one remembered for that name: {', '.join(refused)}. "
              f"If it was reflashed, delete its line from {KNOWN}.", file=sys.stderr)
    if "--table" in sys.argv:
        seen = {h["found_at"] for h in found}
        others = [ip for ip in open_ips if ip not in seen]
        print(f"SSH open but not a Mac mini of ours (other device, or our key refused): "
              f"{' '.join(others) or '-'}", file=sys.stderr)
    return hosts


def inventory(hosts: dict[str, dict]) -> dict:
    hostvars = {}
    for name, h in hosts.items():
        v = {k: h[k] for k in ("ansible_host", "wired_ip", "wifi_ip")}
        m = re.fullmatch(r"ocs-intelligence-macmini-(\d+)", name)
        if m:
            v["macmini_number"] = int(m.group(1))
        hostvars[name] = v
    return {"macminis": {"hosts": sorted(hosts)}, "_meta": {"hostvars": hostvars}}


def main() -> None:
    arg = sys.argv[1] if len(sys.argv) > 1 else "--list"
    if arg == "--host":
        print("{}")  # everything is in _meta
        return
    hosts = discover()
    if arg == "--table":
        for name in sorted(hosts):
            h = hosts[name]
            print(f"{name:40} wired={h['wired_ip'] or '-':16} wifi={h['wifi_ip'] or '-'}")
        print(f"{len(hosts)} Mac mini(s) on {LAN}", file=sys.stderr)
        return
    print(json.dumps(inventory(hosts), indent=2))


if __name__ == "__main__":
    main()
