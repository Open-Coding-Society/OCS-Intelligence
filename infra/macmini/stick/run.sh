#!/bin/sh
# Runs the Mac mini playbook on this machine (ocs-bootstrap.service, set up by
# bootstrap.sh). Exit 0 = done or rebooting to carry on; anything else = systemd
# retries in a minute, up to 5 tries in all.
B=/root/ocs-bootstrap
LOG=/var/log/ocs-bootstrap.log
ANSIBLE_CORE=ansible-core==2.21.6   # the version the playbook is tested with
N=$(cat "$B/number" 2>/dev/null)
say() { echo "OCS setup #${N:-?}: $*" | tee -a "$LOG"; }

tries=$(( $(cat "$B/tries" 2>/dev/null || echo 0) + 1 ))
echo "$tries" > "$B/tries"
if [ "$tries" -gt 5 ]; then
    say "gave up after 5 tries; see $LOG. Rerun the stick to start over."
    systemctl disable ocs-bootstrap.service
    exit 0
fi

rm -f "$B/reboot-pending"
# At boot the service can start before DHCP finishes (the ports are "optional").
i=0
while [ $i -lt 120 ] && ! ip -4 route | grep -q '^default'; do sleep 2; i=$((i + 2)); done
printf '[macminis]\nthis-macmini ansible_connection=local ansible_python_interpreter=/usr/bin/python3\n' > "$B/local.ini"
set -- -i "$B/local.ini" site.yml -e "ocs_env_file=$B/secrets.env" -e "ocs_bootstrap_dir=$B"
[ -n "$N" ] && set -- "$@" -e "macmini_number=$N"

say "try $tries started $(date '+%F %T')"
cd "$B/ansible" || exit 1
HOME=/root /usr/local/bin/uvx --python /usr/bin/python3 --from "$ANSIBLE_CORE" \
    ansible-playbook "$@" >> "$LOG" 2>&1
rc=$?

if [ -e "$B/reboot-pending" ]; then
    reboots=$(( $(cat "$B/reboots" 2>/dev/null || echo 0) + 1 ))
    echo "$reboots" > "$B/reboots"
    if [ "$reboots" -gt 3 ]; then
        # Something keeps asking for a reboot (e.g. unattended-upgrades): stop looping.
        say "asked to reboot $reboots times; stopping. See $LOG. Rerun the stick to start over."
        systemctl disable ocs-bootstrap.service
        exit 0
    fi
    say "rebooting into the new kernel (reboot $reboots); setup carries on after boot"
    echo 0 > "$B/tries"
    exit 0
fi
if [ "$rc" -eq 0 ]; then
    rm -f "$B/secrets.env"
    systemctl disable ocs-bootstrap.service
    say "DONE as $(hostname) $(date '+%F %T')"
    grep -E 'result 285|NetBird IP' "$LOG" | tail -n 2 | tee -a "$LOG"
    exit 0
fi
say "failed (try $tries, exit $rc); retrying in a minute. Log: $LOG"
tail -n 15 "$LOG"
exit "$rc"
