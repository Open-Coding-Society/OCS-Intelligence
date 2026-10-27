#!/usr/bin/env python3
"""Build the Mac mini autoinstall ISO from the stock Ubuntu Server ISO. Stdlib only.

Fills in autoinstall.yaml.template (password hash, SSH keys),
adds it to the ISO root as /autoinstall.yaml, and adds the `autoinstall`
kernel argument to GRUB so the installer starts without asking. Boot records
are replayed unchanged, so the result boots like the stock ISO ("EFI Boot" in
the Mac's Option-key menu). Needs xorriso and openssl.

    python3 infra/macmini/build_iso.py \\
        --iso /mnt/c/Users/<you>/Downloads/ubuntu-26.04.1-live-server-amd64.iso \\
        --out-dir /mnt/c/Users/<you>/Downloads/ocs-macmini

Prompts for the `ocs` password. Writes to infra/macmini/build/ by default
(gitignored, because the output holds the password hash). Guide: docs/operations/flash-mac-minis.md
"""

from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "autoinstall.yaml.template"
KEY_RE = re.compile(r"^(ssh-ed25519|ssh-rsa|ecdsa-sha2-nistp\d+|sk-ssh-ed25519@openssh\.com) [A-Za-z0-9+/=]+( .*)?$")


def render(template: str, password_hash: str, keys: list[str]) -> str:
    if not password_hash.startswith("$6$"):
        raise ValueError("password hash must be SHA-512 crypt ($6$...)")
    if not keys:
        raise ValueError("need at least one SSH public key")
    for key in keys:
        if not KEY_RE.match(key):
            raise ValueError(f"not an SSH public key: {key[:40]!r}")
    key_lines = "\n".join(f"      - {json.dumps(k)}" for k in keys)
    out = template.replace("@PASSWORD_HASH@", password_hash).replace("@SSH_KEYS@", key_lines)
    left = re.findall(r"@[A-Z_]+@", out)
    if left:
        raise ValueError(f"unfilled placeholders: {sorted(set(left))}")
    return out


def patch_grub(cfg: str) -> str:
    """Add `autoinstall` to every casper kernel line and shorten the menu timeout."""
    lines, found = [], 0
    for line in cfg.splitlines():
        if re.match(r"\s*linux\s+/casper/", line):
            found += 1
            if "autoinstall" not in line.split():
                if " ---" in line:
                    line = line.replace(" ---", " autoinstall ---", 1)
                else:
                    line = line + " autoinstall"
        line = re.sub(r"^(\s*set timeout=)\d+", r"\g<1>5", line)
        lines.append(line)
    if not found:
        raise ValueError("no `linux /casper/...` line found in grub.cfg")
    return "\n".join(lines) + "\n"


def update_md5sums(md5sums: str, iso_path: str, data: bytes) -> str:
    """Point md5sum.txt's entry for iso_path (e.g. ./boot/grub/grub.cfg) at data's new hash,
    so casper's boot-time media check doesn't report the ISO as corrupt."""
    new = hashlib.md5(data).hexdigest()
    out, found = [], False
    for line in md5sums.splitlines():
        if line.endswith("  " + iso_path):
            line, found = f"{new}  {iso_path}", True
        out.append(line)
    if not found:
        raise ValueError(f"{iso_path} not in md5sum.txt")
    return "\n".join(out) + "\n"


def password_hash() -> str:
    pw = getpass.getpass("Password for user ocs: ")
    if pw != getpass.getpass("Again: "):
        sys.exit("Passwords don't match.")
    out = subprocess.run(["openssl", "passwd", "-6", "-stdin"], input=pw, text=True,
                         capture_output=True, check=True)
    return out.stdout.strip()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--iso", type=Path, required=True, help="stock ubuntu-*-live-server-amd64.iso")
    p.add_argument("--ssh-key", type=Path, action="append",
                   help="public key file, repeatable (default ~/.ssh/id_ed25519.pub)")
    p.add_argument("--password-hash-file", type=Path,
                   help="file holding an `openssl passwd -6` hash, instead of prompting")
    p.add_argument("--out-dir", type=Path, default=HERE / "build")
    p.add_argument("--xorriso", default=os.environ.get("XORRISO", "xorriso"))
    args = p.parse_args()

    key_files = args.ssh_key or [Path.home() / ".ssh" / "id_ed25519.pub"]
    keys = [f.expanduser().read_text().strip() for f in key_files]
    pw_hash = args.password_hash_file.read_text().strip() if args.password_hash_file else password_hash()
    rendered = render(TEMPLATE.read_text(), pw_hash, keys)

    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True)
    (out / "autoinstall.yaml").write_text(rendered)
    for name in ("grub.cfg", "md5sum.txt"):
        (out / f"{name}.stock").unlink(missing_ok=True)
    subprocess.run([args.xorriso, "-osirrox", "on", "-indev", str(args.iso),
                    "-extract", "/boot/grub/grub.cfg", str(out / "grub.cfg.stock"),
                    "-extract", "/md5sum.txt", str(out / "md5sum.txt.stock")], check=True)
    grub = patch_grub((out / "grub.cfg.stock").read_text())
    (out / "grub.cfg").write_text(grub)
    (out / "md5sum.txt").write_text(
        update_md5sums((out / "md5sum.txt.stock").read_text(), "./boot/grub/grub.cfg", grub.encode()))

    iso_out = out / args.iso.name.replace("live-server", "ocs-macmini")
    iso_out.unlink(missing_ok=True)
    subprocess.run([args.xorriso, "-indev", str(args.iso), "-outdev", str(iso_out),
                    "-map", str(out / "autoinstall.yaml"), "/autoinstall.yaml",
                    "-map", str(out / "grub.cfg"), "/boot/grub/grub.cfg",
                    "-map", str(out / "md5sum.txt"), "/md5sum.txt",
                    "-boot_image", "any", "replay"], check=True)
    print(f"\nWrote {iso_out}\nWrite it to each stick, e.g. sudo dd if={iso_out} of=/dev/sdX bs=4M status=progress conv=fsync")


if __name__ == "__main__":
    main()
