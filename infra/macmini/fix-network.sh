#!/bin/sh
# First boot of a stick-installed Mac mini: name it after its Post-it number and
# turn on DHCP on the wired port. Nothing else; Ansible does the rest.
#
# Copy this file to a FAT32 stick labeled FIX, named `f`. At the Mac mini's console:
#   sudo mount -L FIX /mnt; sudo sh /mnt/f
#
# Why: the autoinstall ran with no cable, so the installer left the wired port
# disabled ("Network is unreachable"). This replaces its netplan with DHCP.
# Guide: docs/operations/flash-mac-minis.md
set -eu
R="${ROOT:-}"   # test hook: ROOT=/some/dir writes there and skips the live steps

# 1. Name: ocs-intelligence-macmini-N, N from the Post-it note on the box.
N="${N:-}"
while ! printf '%s' "$N" | grep -Eq '^[0-9]{1,3}$'; do
  printf 'Mac mini number (from the Post-it): '
  read -r N
done
NAME="ocs-intelligence-macmini-$N"
OLD=$(cat "$R/etc/hostname" 2>/dev/null || echo localhost)
echo "$NAME" > "$R/etc/hostname"
if grep -q '^127\.0\.1\.1' "$R/etc/hosts" 2>/dev/null; then
  sed -i "s/^127\.0\.1\.1.*/127.0.1.1 $NAME/" "$R/etc/hosts"
else
  echo "127.0.1.1 $NAME" >> "$R/etc/hosts"
fi
[ -n "$R" ] || hostname "$NAME"

# 2. The wired port: an en* interface that isn't Wi-Fi (Macmini7,1: enp3s0f0).
if [ -z "$R" ]; then
  IF=""
  for d in /sys/class/net/en*; do
    [ -e "$d" ] || continue
    [ -d "$d/wireless" ] && continue
    IF=$(basename "$d"); break
  done
  [ -n "$IF" ] || { echo "No wired en* interface found"; ip -br link; exit 1; }
else
  IF="${IF:-enp3s0f0}"
fi

# 3. Keep the installer's netplan files, but out of netplan's way.
mkdir -p "$R/etc/netplan" "$R/etc/netplan.installer" "$R/etc/cloud/cloud.cfg.d"
for f in "$R"/etc/netplan/*.yaml; do
  [ -e "$f" ] || continue
  case "$(basename "$f")" in 01-wired.yaml|01-ocs.yaml) continue ;; esac
  mv "$f" "$R/etc/netplan.installer/"
done
if [ ! -e "$R/etc/netplan/01-ocs.yaml" ]; then   # Ansible's file, once it has run
  cat > "$R/etc/netplan/01-wired.yaml" <<YAML
network:
  version: 2
  renderer: networkd
  ethernets:
    $IF:
      dhcp4: true
      optional: true
YAML
  chmod 600 "$R/etc/netplan/01-wired.yaml"
fi
# Stop cloud-init from rewriting netplan on a later boot.
echo 'network: {config: disabled}' > "$R/etc/cloud/cloud.cfg.d/99-disable-network-config.cfg"

[ -n "$R" ] && { echo "test mode: wrote to $R as $NAME"; exit 0; }

netplan apply
ip link set "$IF" up 2>/dev/null || true
i=0; A=""
while [ $i -lt 30 ]; do
  A=$(ip -4 -br addr show "$IF" | awk '{print $3}')
  [ -n "$A" ] && break
  sleep 1; i=$((i+1))
done
C=$(cat "/sys/class/net/$IF/carrier" 2>/dev/null || echo ?)
echo "$NAME (was $OLD)  $IF  carrier=$C  ip=${A:-NONE}"
[ -n "$A" ] || echo "No address: check the cable and link light (carrier=0 means no link)."
