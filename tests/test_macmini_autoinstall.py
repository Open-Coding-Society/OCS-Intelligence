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
    # Installs run with no cable; an explicit DHCP config keeps the wired port enabled.
    wired = cfg["network"]["ethernets"]["wired"]
    assert wired == {"match": {"name": "en*"}, "dhcp4": True, "optional": True}
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


def test_fix_network_names_the_machine_and_enables_dhcp(tmp_path):
    """The FIX stick script, in its test mode (ROOT set): no live changes."""
    import subprocess
    (tmp_path / "etc" / "netplan").mkdir(parents=True)
    (tmp_path / "etc" / "hostname").write_text("ocs-intelligence-c07test\n")
    (tmp_path / "etc" / "hosts").write_text("127.0.0.1 localhost\n127.0.1.1 ocs-intelligence-c07test\n")
    installer = tmp_path / "etc" / "netplan" / "00-installer-config.yaml"
    installer.write_text("network:\n  version: 2\n  ethernets:\n    enp3s0f0:\n      dhcp4: false\n")
    subprocess.run(["sh", str(KIT / "fix-network.sh")], input="abc\n7\n", text=True, check=True,
                   env={"ROOT": str(tmp_path), "PATH": "/usr/bin:/bin"}, capture_output=True)
    assert (tmp_path / "etc" / "hostname").read_text() == "ocs-intelligence-macmini-7\n"
    assert "127.0.1.1 ocs-intelligence-macmini-7" in (tmp_path / "etc" / "hosts").read_text()
    assert not installer.exists() and (tmp_path / "etc" / "netplan.installer" / installer.name).exists()
    wired = yaml.safe_load((tmp_path / "etc" / "netplan" / "01-wired.yaml").read_text())
    assert wired["network"]["ethernets"]["enp3s0f0"]["dhcp4"] is True


def test_ansible_files_parse_and_ray_is_pinned():
    ans = KIT / "ansible"
    for f in [ans / "site.yml", ans / "group_vars" / "macminis.yml", *sorted((ans / "tasks").glob("*.yml"))]:
        assert yaml.safe_load(f.read_text()) is not None, f
    gv = yaml.safe_load((ans / "group_vars" / "macminis.yml").read_text())
    assert "password" not in str({k: v for k, v in gv.items() if "lookup" not in str(v)}).lower()
    locked = (ans / "files" / "cluster-requirements.txt").read_text()
    assert "\nray==2.60.0" in locked
    assert "ray[default,data,train,tune,serve]==2.60.0" in (ans / "files" / "cluster-requirements.in").read_text()


def test_inventory_names_hosts_and_reads_number_from_name():
    import importlib.util
    path = Path(__file__).resolve().parent.parent / "infra/macmini/ansible/inventory.py"
    spec = importlib.util.spec_from_file_location("macmini_inventory", path)
    inv = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(inv)
    out = inv.inventory({
        "ocs-intelligence-macmini-25": {"ansible_host": "192.168.8.10", "wired_ip": "192.168.8.10", "wifi_ip": "192.168.8.11"},
        "ocs-intelligence-c07abc": {"ansible_host": "192.168.8.12", "wired_ip": None, "wifi_ip": "192.168.8.12"},
    })
    assert out["macminis"]["hosts"] == ["ocs-intelligence-c07abc", "ocs-intelligence-macmini-25"]
    hv = out["_meta"]["hostvars"]
    assert hv["ocs-intelligence-macmini-25"]["macmini_number"] == 25
    assert "macmini_number" not in hv["ocs-intelligence-c07abc"]


def test_netbird_setup_key_never_on_the_command_line():
    text = (Path(__file__).resolve().parent.parent / "infra/macmini/ansible/tasks/netbird.yml").read_text()
    assert "--setup-key {{" not in text and "--setup-key-file" in text
