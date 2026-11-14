#!/bin/sh
# Second half of the FIX stick (the first half, `f`, has just turned on the wired
# port). Copies the setup kit off the stick and starts the playbook on this machine
# as a service, so the stick can be pulled right away and the run survives the
# reboot into a new kernel. Built by infra/macmini/make_stick.py; guide:
# docs/operations/set-up-mac-minis.md
#
#   sh bootstrap.sh <kit dir on the stick>
set -eu
SRC="$1"
# Test hooks (tests/test_macmini_autoinstall.py); unset on a real machine.
B="${OCS_BOOTSTRAP_DIR:-/root/ocs-bootstrap}"
DMI_SERIAL="${OCS_DMI_SERIAL:-/sys/class/dmi/id/product_serial}"
UNIT_DIR="${OCS_UNIT_DIR:-/etc/systemd/system}"
BIN_DIR="${OCS_BIN_DIR:-/usr/local/bin}"
SYSTEMCTL="${OCS_SYSTEMCTL:-systemctl}"
umask 077

# 1. The kit, off the stick (a second run of the stick starts fresh).
rm -rf "$B.new"
mkdir -p "$B.new"
cp -r "$SRC/ansible" "$SRC/secrets.env" "$SRC/macminis.csv" "$SRC/run.sh" "$B.new/"
rm -rf "$B"
mv "$B.new" "$B"
chmod 700 "$B" "$B/run.sh"
install -m 0755 "$SRC/uv" "$BIN_DIR/uv"

# 2. This machine's Post-it number, from its own serial.
SERIAL=$(tr -cd 'A-Za-z0-9' < "$DMI_SERIAL" | tr 'a-z' 'A-Z')
N=$(awk -F, -v s="$SERIAL" 'toupper($2) == s { print $1 }' "$B/macminis.csv" | head -n 1)
echo "$SERIAL" > "$B/serial"
echo "$N" > "$B/number"

# 3. The playbook as a service: retries on failure, resumes after a reboot.
cat > "$UNIT_DIR/ocs-bootstrap.service" <<EOF
[Unit]
Description=OCS Mac mini setup (started from the FIX stick)
Wants=network-online.target
After=network-online.target

[Service]
Type=oneshot
ExecStart=$B/run.sh
Restart=on-failure
RestartSec=60
TimeoutStartSec=3h
StandardOutput=journal+console
StandardError=journal+console

[Install]
WantedBy=multi-user.target
EOF
$SYSTEMCTL daemon-reload
$SYSTEMCTL enable ocs-bootstrap.service >/dev/null 2>&1
$SYSTEMCTL start --no-block ocs-bootstrap.service

echo "#${N:-?} (serial $SERIAL): setup started. You can pull the stick."
[ -n "$N" ] || echo "  Serial not in macminis.csv: it'll be set up, but keeps its serial name. Fix the table."
echo "  Progress: journalctl -fu ocs-bootstrap   (about 20-30 min; it reboots once)"
