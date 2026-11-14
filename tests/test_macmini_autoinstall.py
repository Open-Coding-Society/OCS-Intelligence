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


def test_fix_network_enables_dhcp_and_leaves_the_name(tmp_path):
    """The FIX stick script, in its test mode (ROOT set): no live changes."""
    import subprocess
    (tmp_path / "etc" / "netplan").mkdir(parents=True)
    (tmp_path / "etc" / "hostname").write_text("ocs-intelligence-c07test\n")
    (tmp_path / "etc" / "hosts").write_text("127.0.0.1 localhost\n127.0.1.1 ocs-intelligence-c07test\n")
    installer = tmp_path / "etc" / "netplan" / "00-installer-config.yaml"
    installer.write_text("network:\n  version: 2\n  ethernets:\n    enp3s0f0:\n      dhcp4: false\n")
    subprocess.run(["sh", str(KIT / "fix-network.sh")], input="", text=True, check=True,
                   env={"ROOT": str(tmp_path), "PATH": "/usr/bin:/bin"}, capture_output=True, timeout=10)
    # No prompt, no rename: the playbook names it from the serial table.
    assert (tmp_path / "etc" / "hostname").read_text() == "ocs-intelligence-c07test\n"
    assert not installer.exists() and (tmp_path / "etc" / "netplan.installer" / installer.name).exists()
    wired = yaml.safe_load((tmp_path / "etc" / "netplan" / "01-wired.yaml").read_text())
    assert wired["network"]["ethernets"]["enp3s0f0"]["dhcp4"] is True
    assert wired["network"]["ethernets"]["enp3s0f0"]["dhcp-identifier"] == "mac"


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


def _ansible_module(name):
    import importlib.util
    import sys
    d = Path(__file__).resolve().parent.parent / "infra/macmini/ansible"
    sys.path.insert(0, str(d))
    try:
        spec = importlib.util.spec_from_file_location(name, d / f"{name}.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        sys.path.remove(str(d))


def test_serial_table_numbers_unrenamed_machines(tmp_path):
    inv = _ansible_module("inventory")
    t = tmp_path / "macminis.csv"
    t.write_text("# comment\nnumber,serial\n7,C07ABC123\n")
    inv.TABLE = t
    table = inv.load_table()
    assert inv.number_of("ocs-intelligence-c07abc123", table) == 7
    assert inv.number_of("ocs-intelligence-macmini-3", table) == 3
    assert inv.number_of("ocs-intelligence-c07zzz", table) is None


def test_reservations_layout_and_clash_detection():
    res = _ansible_module("reservations")
    hosts = {"ocs-intelligence-macmini-25": {"wired_mac": "38:c9:86:56:ed:f3", "wifi_mac": "2c:f0:a2:f0:72:64"},
             "ocs-intelligence-c07unknown": {"wired_mac": "aa:bb:cc:dd:ee:ff", "wifi_mac": None}}
    es, skipped = res.entries(hosts, {})
    assert [(e["section"], e["ip"]) for e in es] == [("ocs_mm25_wired", "192.168.8.35"), ("ocs_mm25_wifi", "192.168.8.75")]
    assert len(skipped) == 1
    # every reserved address stays below the router's pool (.100)
    assert res.WIFI_BASE + res.MAX_NUMBER < 100 and res.WIRED_BASE + res.MAX_NUMBER < res.WIFI_BASE
    dump = ("dhcp.cfg01=host\ndhcp.cfg01.mac='18:31:BF:26:3B:47'\ndhcp.cfg01.ip='192.168.8.112'\n"
            "dhcp.ocs_mm25_wifi=host\ndhcp.ocs_mm25_wifi.mac='2C:F0:A2:F0:72:64'\ndhcp.ocs_mm25_wifi.ip='192.168.8.75'\n")
    current = res.existing(dump)
    assert res.conflicts(es, current) == []           # our own section isn't a clash (re-apply is fine)
    clash = res.conflicts([{**es[0], "ip": "192.168.8.112"}], current)
    assert len(clash) == 1 and "192.168.8.112" in clash[0]


def test_stick_bootstrap_copies_kit_finds_number_and_starts_service(tmp_path):
    """bootstrap.sh with its test hooks: no root, no systemd."""
    import subprocess
    kit = tmp_path / "stick" / "ocs"
    (kit / "ansible").mkdir(parents=True)
    (kit / "ansible" / "site.yml").write_text("- hosts: all\n")
    (kit / "secrets.env").write_text("MACMINI_WIFI_PASSWORD=x\n")
    (kit / "macminis.csv").write_text("number,serial\n7,C07RX0ABG1J1\n")
    for name in ("bootstrap.sh", "run.sh"):
        (kit / name).write_text((KIT / "stick" / name).read_text())
    (kit / "uv").write_text("#!/bin/sh\n")
    (tmp_path / "serial").write_text("c07rx0abg1j1\n")
    for d in ("root", "units", "bin"):
        (tmp_path / d).mkdir()
    calls = tmp_path / "systemctl.log"
    fake = tmp_path / "systemctl"
    fake.write_text(f'#!/bin/sh\necho "$@" >> {calls}\n')
    fake.chmod(0o755)
    env = {"PATH": "/usr/bin:/bin", "OCS_BOOTSTRAP_DIR": str(tmp_path / "root" / "ocs-bootstrap"),
           "OCS_DMI_SERIAL": str(tmp_path / "serial"), "OCS_UNIT_DIR": str(tmp_path / "units"),
           "OCS_BIN_DIR": str(tmp_path / "bin"), "OCS_SYSTEMCTL": str(fake)}
    r = subprocess.run(["sh", str(kit / "bootstrap.sh"), str(kit)], env=env, capture_output=True, text=True, timeout=20)
    assert r.returncode == 0, r.stderr
    b = tmp_path / "root" / "ocs-bootstrap"
    assert (b / "number").read_text().strip() == "7" and "#7" in r.stdout
    assert (b / "secrets.env").exists() and (b / "ansible" / "site.yml").exists()
    assert (b.stat().st_mode & 0o077) == 0                       # root-only
    assert "ExecStart=" + str(b / "run.sh") in (tmp_path / "units" / "ocs-bootstrap.service").read_text()
    assert "start --no-block ocs-bootstrap.service" in calls.read_text()
    # unknown serial: still starts, says so
    (tmp_path / "serial").write_text("C07UNKNOWN99\n")
    r = subprocess.run(["sh", str(kit / "bootstrap.sh"), str(kit)], env=env, capture_output=True, text=True, timeout=20)
    assert r.returncode == 0 and "#?" in r.stdout and "not in macminis.csv" in r.stdout


def test_fix_stick_hands_over_to_the_kit_and_playbook_resumes_after_local_reboot():
    f = (KIT / "fix-network.sh").read_text()
    assert 'sh "$KIT/bootstrap.sh" "$KIT"' in f
    base = (KIT / "ansible" / "tasks" / "base.yml").read_text()
    assert "reboot-pending" in base and "meta: end_host" in base
    run = (KIT / "stick" / "run.sh").read_text()
    assert 'rm -f "$B/secrets.env"' in run and "reboot-pending" in run
