#!/usr/bin/env python3
"""Build the FIX stick's contents: plug it into a freshly flashed Mac mini, run one
command, and it sets itself up (network, name, packages, Wi-Fi, Python, Ray, NetBird).

  python3 infra/macmini/make_stick.py --out /mnt/c/Users/<you>/Downloads/ocs-macmini-stick

Then copy everything in --out onto a FAT32 stick labeled FIX. At each Mac mini
(Ethernet plugged in), log in as ocs and run:

  sudo mount -L FIX /mnt; sudo sh /mnt/f

The stick holds secrets (ocs/secrets.env): the Wi-Fi password and a NetBird setup
key limited to 33 uses and 14 days (NETBIRD_MACMINI_STICK_KEY in .env). Keep the
stick with the Mac minis and wipe it when the batch is done. The default --out is
gitignored. Standard library only. Guide: docs/operations/set-up-mac-minis.md
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
SECRETS = {  # name in secrets.env on the stick <- name in the repo .env
    "MACMINI_WIFI_SSID": "MACMINI_WIFI_SSID",
    "MACMINI_WIFI_PASSWORD": "MACMINI_WIFI_PASSWORD",
    "NETBIRD_MACMINI_SETUP_KEY": "NETBIRD_MACMINI_STICK_KEY",
}


def read_env(path: Path) -> dict[str, str]:
    env = {}
    for line in path.read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=HERE / "build" / "stick")
    out = ap.parse_args().out

    env = read_env(REPO / ".env")
    missing = [src for src in SECRETS.values() if not env.get(src) or "CHANGE_ME" in env[src]]
    if missing:
        sys.exit(f"missing from .env: {', '.join(missing)}")
    table = HERE / "macminis.csv"
    if not table.exists():
        sys.exit(f"{table} is missing (number,serial per Mac mini; see macminis.example.csv)")
    rows = [l for l in table.read_text().splitlines() if re.match(r"^\d+,\w+", l)]

    want_uv = re.search(r'ocs_uv_version:\s*"([^"]+)"',
                        (HERE / "ansible/group_vars/macminis.yml").read_text()).group(1)
    uv = shutil.which("uv")
    have_uv = subprocess.run([uv, "--version"], capture_output=True, text=True).stdout.split()[1] if uv else ""
    if have_uv != want_uv:
        sys.exit(f"local uv is {have_uv or 'missing'}, the playbook pins {want_uv}: install that version first")

    if out.exists():
        shutil.rmtree(out)
    kit = out / "ocs"
    kit.mkdir(parents=True)
    shutil.copy(HERE / "fix-network.sh", out / "f")
    for name in ("bootstrap.sh", "run.sh"):
        shutil.copy(HERE / "stick" / name, kit / name)
    shutil.copy(uv, kit / "uv")
    shutil.copy(table, kit / "macminis.csv")
    shutil.copytree(HERE / "ansible", kit / "ansible",
                    ignore=shutil.ignore_patterns("__pycache__", "*.retry", "*.pyc"))
    (kit / "secrets.env").write_text("".join(f"{dst}={env[src]}\n" for dst, src in SECRETS.items()))
    (out / "README.txt").write_text(
        "OCS Mac mini FIX stick. Copy everything here onto a FAT32 stick labeled FIX.\n"
        "At a freshly flashed Mac mini, Ethernet plugged in, log in as ocs and run:\n\n"
        "    sudo mount -L FIX /mnt; sudo sh /mnt/f\n\n"
        "It prints the machine's number and 'setup started'; pull the stick and move on.\n"
        "Setup takes about 20-30 min and reboots once. Progress on that machine:\n"
        "    journalctl -fu ocs-bootstrap\n"
        "ocs/secrets.env holds the Wi-Fi password and a NetBird key: keep this stick safe\n"
        "and wipe it when the batch is done.\n")
    print(f"stick contents in {out}: {len(rows)} Mac minis in the table, uv {have_uv}")


if __name__ == "__main__":
    main()
