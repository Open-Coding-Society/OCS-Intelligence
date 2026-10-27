"""Offline tests for the Mac mini autoinstall ISO builder (infra/macmini/). No network, no ISO."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parent.parent
KIT = REPO / "infra" / "macmini"


spec = importlib.util.spec_from_file_location("build_iso", KIT / "build_iso.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)

KEY = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIExampleExampleExampleExampleExample user@laptop"
HASH = "$6$salt$abcdefghijklmnopqrstuvwxyz0123456789./ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuv"


def test_rendered_autoinstall_is_valid_yaml():
    out = build.render(build.TEMPLATE.read_text(), HASH, [KEY])
    cfg = yaml.safe_load(out)["autoinstall"]
    assert cfg["identity"]["username"] == "ocs"
    assert cfg["identity"]["password"] == HASH
    assert cfg["identity"]["hostname"] == "ocs-intelligence-unassigned"
    assert cfg["ssh"] == {"install-server": True, "allow-pw": False, "authorized-keys": [KEY]}
    assert cfg["apt"]["fallback"] == "offline-install"
    assert cfg["storage"]["layout"] == {"name": "direct", "match": {"size": "largest"}}
    assert cfg["shutdown"] == "poweroff"
    assert "/sys/class/dmi/id/product_serial" in cfg["late-commands"][0]
    # The heredoc terminator must land at column 0 once YAML strips the indent.
    assert "\nEOF\n" in cfg["late-commands"][1]


@pytest.mark.parametrize("hash_,keys", [("plaintext", [KEY]), (HASH, []), (HASH, ["not a key"])])
def test_render_rejects_bad_input(hash_, keys):
    with pytest.raises(ValueError):
        build.render(build.TEMPLATE.read_text(), hash_, keys)


def test_patch_grub_adds_autoinstall_once():
    stock = (
        "set timeout=30\n"
        "menuentry \"Try or Install Ubuntu Server\" {\n"
        "\tlinux\t/casper/vmlinuz  ---\n"
        "\tinitrd\t/casper/initrd\n"
        "}\n"
    )
    patched = build.patch_grub(stock)
    assert "\tlinux\t/casper/vmlinuz  autoinstall ---" in patched
    assert "set timeout=5" in patched
    assert build.patch_grub(patched) == patched


def test_patch_grub_fails_without_kernel_line():
    with pytest.raises(ValueError):
        build.patch_grub("set timeout=30\n")


def test_update_md5sums_replaces_only_that_entry():
    stock = "aaa  ./md5sum.txt\nbbb  ./boot/grub/grub.cfg\nccc  ./boot/grub/grub.cfg.bak\n"
    out = build.update_md5sums(stock, "./boot/grub/grub.cfg", b"new")
    assert out.splitlines() == ["aaa  ./md5sum.txt", "22af645d1859cb5ca6da0c484f1f37ea  ./boot/grub/grub.cfg",
                                "ccc  ./boot/grub/grub.cfg.bak"]
    with pytest.raises(ValueError):
        build.update_md5sums(stock, "./nope", b"")
