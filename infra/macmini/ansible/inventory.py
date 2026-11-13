#!/usr/bin/env python3
"""Ansible inventory that finds the Mac minis on the LAN, so no IPs are written down.

Every run: try SSH (port 22) on each address of OCS_LAN (default 192.168.8.0/24),
log in as ocs with your key, and keep the machines that report Macmini7,1.
Each one is named by its hostname, and Ansible connects to its wired address
when it has one (the Wi-Fi address otherwise), as reported by the machine.

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
from concurrent.futures import ThreadPoolExecutor

LAN = os.environ.get("OCS_LAN", "192.168.8.0/24")
USER = "ocs"
MODEL = "Macmini7,1"
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


def probe(ip: str) -> dict | None:
    try:
        out = subprocess.run(
            ["ssh", "-n", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5",
             "-o", "StrictHostKeyChecking=accept-new", "-o", "LogLevel=ERROR",
             f"{USER}@{ip}", PROBE],
            capture_output=True, text=True, timeout=15).stdout.splitlines()
    except subprocess.TimeoutExpired:
        return None
    if len(out) < 2 or out[1].strip() != MODEL:
        return None
    addrs = dict(line.split()[:2] for line in out[2:] if len(line.split()) >= 2)
    wired = [a.split("/")[0] for i, a in addrs.items() if i.startswith("en")]
    wifi = [a.split("/")[0] for i, a in addrs.items() if i.startswith("wl")]
    return {"name": out[0].strip(), "found_at": ip,
            "ansible_host": (wired or wifi or [ip])[0],
            "wired_ip": wired[0] if wired else None,
            "wifi_ip": wifi[0] if wifi else None}


def discover() -> dict[str, dict]:
    ips = [str(h) for h in ipaddress.ip_network(LAN).hosts()]
    with ThreadPoolExecutor(64) as pool:
        open_ips = [ip for ip, ok in zip(ips, pool.map(ssh_open, ips)) if ok]
        found = [h for h in pool.map(probe, open_ips) if h]
    hosts: dict[str, dict] = {}
    for h in found:  # a machine on wired and Wi-Fi answers twice; keep one
        hosts.setdefault(h["name"], h)
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
