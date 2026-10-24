---
type: playbook
date: 2026-10-22
title: Rig routing
subtitle: Putting the OCS Intelligence rigs on a private network of our own, behind the filtered school Wi-Fi.
sprint: 4
state: done
---

# Rig routing

The room's wall Ethernet jacks don't work, so the only way out is the school Wi-Fi, which filters traffic and blocks unusual ports. We gave the rigs their own private network. A Mac mini joins the school Wi-Fi and shares that connection over Ethernet to a GL.iNet Flint 2 router. The router runs the OCS LAN: both rigs are wired into it, and it broadcasts the 5 GHz `OCS_Intel` Wi-Fi. The network was fully in place on 2026-10-22, when Rig 1's link was fixed to 1 Gb/s to match Rig 2's. Measured since: each rig links at 1 Gb/s, rig to rig carries 934 Mb/s, and the internet gets ~84 Mb/s shared. The next step, a WireGuard tunnel from the Flint to the EC2 relay so all OCS traffic leaves from EC2, is Sprint 5 networking work ([pending playbook](../pending-playbook.md), [plan](../../docs/project/roadmap.md#task-2-networking-router-and-vpn)).

The team first wrote this up as a PDF on 2026-10-16, while Rig 2 was still on a USB Wi-Fi dongle. It was converted to the standard format on 2026-10-23, corrected where the setup changed (the Wi-Fi is `OCS_Intel`, it was `OCS-IoT`; Rig 2 is wired), and dated by when the network was finished. The planned tunnel steps moved to the pending playbook.

## At a glance

| | |
|---|---|
| Goal | The rigs on a private LAN we control, reaching the internet through the school Wi-Fi |
| Outcome | Done 2026-10-22: Mac mini uplink, Flint 2 router, both rigs wired at 1 Gb/s, `OCS_Intel` Wi-Fi. The WireGuard tunnel to EC2 is Sprint 5 |
| Where | Mac mini (Ubuntu), GL.iNet Flint 2 (GL-MT6000), both rigs, the EC2 relay |
| Why | No decision record yet. Defining the "closed-loop" network is a Sprint 5 item |

| Piece | Status |
|---|---|
| Mac mini joins the school Wi-Fi on its built-in card | Live. Proprietary `wl` driver, profile `PUSD open test` |
| Mac mini shares its connection over Ethernet | Live. NetworkManager shared mode on `enp3s0f0`, `10.42.0.1/24` |
| Flint 2 gets its WAN address from the Mac mini | Live. Tested first with a Brume 2 (got `10.42.0.185`), then the Flint 2 |
| Flint 2 runs the OCS LAN and `OCS_Intel` Wi-Fi | Live. 5 GHz only; 2.4 GHz is off (2026-10-23) |
| Rig 2 wired to Flint LAN port 2, Rig 1 to port 3 | Live (ports reported 2026-10-23). Port 4 is for orchestrator testing; ports 5 and 6 belong to other groups in the class |
| Reboot test of the Mac mini with its USB dongle unplugged | Pending. Must pass before anything depends on it |
| WireGuard tunnel to EC2 | Sprint 5 ([pending playbook](../pending-playbook.md)) |

```text
                     INTERNET
                       ▲
   School Wi-Fi (PUSD-Onboard, district filter)
                       ▲   Wi-Fi
             ┌─────────┴──────────┐
             │  Mac mini (Ubuntu) │  wlp2s0 = school Wi-Fi · enp3s0f0 = 10.42.0.1/24
             │  NAT + DHCP        │
             └─────────┬──────────┘
                       │   Ethernet into the router's WAN port (gets 10.42.0.x)
             ┌─────────┴──────────┐
             │  GL.iNet Flint 2   │  OCS LAN 192.168.8.0/24 · admin 192.168.8.1
             └─┬──────┬──────┬────┘
          port 2   port 3   Wi-Fi OCS_Intel (5 GHz)
             │        │
          Rig 2    Rig 1
```

## Before

- The room's wall Ethernet jacks don't work. The only uplink is the school Wi-Fi, `PUSD-Onboard`.
- The district filters outbound traffic and blocks unusual ports, so a tunnel has to use a port that gets through.
- Consumer routers can't join the school network in a way we control, so a Linux machine (the Mac mini) joins it and hands the connection to our own router.

> [!IMPORTANT]
> The OCS team has permission for this network. If you build this somewhere else, get written approval from the network owner first.

**Why the Flint 2 and not the Brume 2.** The Flint 2 (GL-MT6000) has Wi-Fi 6 and 1 WAN + 5 LAN ports, so it does wired LAN and Wi-Fi in one box, and it can run the planned WireGuard client too. The Brume 2 (GL-MT2500A) has no Wi-Fi radio and 1 WAN + 1 LAN. It's kept as a spare.

### Hardware and addresses

| Item | Details |
|---|---|
| Mac mini | Ubuntu with NetworkManager; the school-facing uplink |
| Its built-in Wi-Fi | Broadcom BCM4360, PCI ID `14e4:43a0`, interface `wlp2s0`. Needs the proprietary `wl` driver |
| Its Ethernet | Broadcom NetXtreme Gigabit, `enp3s0f0` |
| USB Wi-Fi dongle (fallback) | Ralink RT5370, USB ID `148f:5370`, in-kernel `rt2800usb` driver. Supports OWE |
| Router | GL.iNet Flint 2 (GL-MT6000). Brume 2 kept as a spare |

| Network | Subnet | Who hands out addresses | Fixed addresses |
|---|---|---|---|
| School Wi-Fi | Whatever the district gives | District DHCP | None |
| Mac mini → router link | `10.42.0.0/24` | Mac mini (NetworkManager shared mode) | Mac mini = `10.42.0.1` |
| OCS LAN (wired + `OCS_Intel`) | `192.168.8.0/24` | Flint 2 | Flint = `192.168.8.1`; Rig 1 = `192.168.8.112`, Rig 2 = `192.168.8.213` (seen 2026-10-22/23) |

Every subnet must differ from the others, or routing breaks. The planned tunnel will need one more that overlaps none of these.

**Before you start:** a keyboard and monitor (or SSH) on the Mac mini, with sudo, and Ethernet cables (Mac mini to the Flint's WAN port, one per wired device). Steps 1–5 take about 2 hours.

## What we did

### Step 1: Get the Mac mini's built-in Wi-Fi working

Ubuntu doesn't ship a working driver for the BCM4360, so the card is invisible until you install one.

1. Find the card by Broadcom's vendor ID (a plain `grep network` can miss it):

   ```bash
   lspci -nn | grep -i 14e4     # expect a line ending in [14e4:43a0] -> BCM4360
   ```

   With a USB dongle too, compare `lsusb` with it unplugged and plugged in. `0a5c:4500` is the Bluetooth controller, not Wi-Fi.

2. Install the driver and reboot:

   ```bash
   sudo apt update
   sudo apt install -y dkms linux-headers-$(uname -r) broadcom-sta-dkms
   sudo reboot
   ```

3. Check it:

   ```bash
   dkms status                            # broadcom-sta ... installed
   lsmod | grep -E "wl|b43|bcma|ssb"      # wl loaded; b43/bcma/ssb NOT loaded
   nmcli device                           # wlp2s0 listed as wifi
   nmcli device wifi list ifname wlp2s0   # school SSIDs show up
   ```

> [!WARNING]
> With Secure Boot on, the DKMS module must be enrolled (MOK) or it won't load. A kernel update can also break the rebuild. Re-run the checks above after every kernel update.

### Step 2: Join the school Wi-Fi from the Mac mini

`PUSD-Onboard` uses OWE (encrypted open Wi-Fi) in transition mode, so it appears as a pair: an OWE side and a plain open side. The `wl` driver can't do OWE, so the built-in card joins the open side, pinned to one access point.

1. Pick the access point. Choose the strongest entry **not** marked OWE and copy its BSSID:

   ```bash
   nmcli -f SSID,BSSID,SECURITY,CHAN,SIGNAL device wifi list ifname wlp2s0 | grep -i onboard
   ```

2. Create the profile:

   ```bash
   nmcli connection add type wifi ifname wlp2s0 con-name "PUSD open test" \
       ssid PUSD-Onboard 802-11-wireless.bssid <BSSID_FROM_ABOVE> \
       connection.autoconnect yes
   nmcli connection up "PUSD open test"
   ```

3. Check it: `ip route` must show the default route on `dev wlp2s0`, and `curl -I https://example.com` must return headers. `ping 8.8.8.8` fails here, and that's expected: the school network appears to drop ICMP. Test with `curl`.

What failed, so nobody repeats it:

| Attempt | Result |
|---|---|
| Clone the dongle's OWE profile onto `wlp2s0` | Stuck configuring; association took too long. Deleted |
| Point the original OWE profile at `wlp2s0` | Network not found (`wl` can't do OWE) |
| OWE profile pinned to one BSSID | Network not found |
| New open profile pinned to one BSSID | **Worked** |

At a different school: if the card supports OWE (most mac80211 drivers, like the RT5370), use `wifi-sec.key-mgmt owe` for encryption. With WPA2-Enterprise (PEAP/MSCHAPv2), add the 802-1x settings with school credentials instead.

### Step 3: Share the Mac mini's connection over Ethernet

NetworkManager's shared mode turns on IP forwarding, NAT, and a small DHCP server on the Ethernet port in one command.

1. Plug a cable from the Mac mini into the router's **WAN** port.
2. Create and start the shared profile:

   ```bash
   nmcli connection add type ethernet ifname enp3s0f0 con-name "brume-link" \
       ipv4.method shared connection.autoconnect yes
   nmcli connection up "brume-link"
   ```

3. Check it:

   ```bash
   nmcli device                                          # enp3s0f0 connected, brume-link
   ip addr show enp3s0f0                                 # inet 10.42.0.1/24
   sysctl net.ipv4.ip_forward                            # = 1
   cat /var/lib/NetworkManager/dnsmasq-enp3s0f0.leases   # the router's WAN lease appears
   ```

The profile is called `brume-link` because it was first tested with the Brume 2. The name doesn't matter; it works the same with the Flint 2.

### Step 4: Set up the Flint 2

1. Connect a computer to the Flint (a cable to a LAN port, or the default Wi-Fi on its label).
2. Open `http://192.168.8.1`. Set a strong admin password and write it down somewhere private: anything on the OCS LAN can reach this page.
3. **Internet:** it should already show Ethernet connected by DHCP with a `10.42.0.x` address. If so, leave it, and don't change the network mode.
4. **Wireless:** name the network `OCS_Intel`, use WPA2/WPA3, and set a strong password. The team runs it on 5 GHz only, with 2.4 GHz off.
5. From that computer, `curl -I https://example.com`. Headers back means the whole chain works: school Wi-Fi → Mac mini → Flint.

### Step 5: Connect the rigs

Both rigs are wired (Rig 2 moved off its temporary USB Wi-Fi dongle by 2026-10-20).

1. Run an Ethernet cable from each rig to a Flint LAN port: **Rig 2 to port 2, Rig 1 to port 3.** Port 4 is for orchestrator testing. Ports 5 and 6 are used by other groups in the class.
2. In the Flint admin panel, under Clients, reserve each rig's address so it never changes.
3. On each rig: `curl -I https://example.com`, and `ethtool enp0s31f6 | grep Speed` should say `1000Mb/s`.

| Rig | Connection | Address |
|---|---|---|
| Rig 2 | Ethernet, Flint port 2 | `192.168.8.213` |
| Rig 1 | Ethernet, Flint port 3 | `192.168.8.112` |

Traffic between the rigs stays on the Flint and never touches the school network. Only internet traffic uses the Mac mini's Wi-Fi.

**Measured afterwards** (2026-10-22/23, [link](../captures/2026-10-22-rig1-gigabit-link.md), [rig to rig](../captures/2026-10-22-rig-to-rig-iperf3.md), [internet](../captures/2026-10-23-rig-internet-throughput.md)): both rigs link at 1 Gb/s full duplex. `iperf3` between them carries 934 Mb/s each way, and the router answers in ~0.5 ms. The internet gets ~60–90 Mb/s each way, shared: ~84 Mb/s combined with both rigs downloading. Rig 1 first linked at only 100 Mb/s; a cable or port change on 2026-10-22 fixed it.

## How to check it

| Check | Pass looks like | If it fails |
|---|---|---|
| Mac mini: `ip route` | Default route on `dev wlp2s0` | `nmcli connection up "PUSD open test"`; see Pitfalls |
| Mac mini: `nmcli device` | `wlp2s0` connected, `enp3s0f0` connected (`brume-link`) | Re-run Step 1's checks |
| Mac mini: `sysctl net.ipv4.ip_forward` | `1` | `nmcli connection up brume-link` |
| Flint admin → Internet | Ethernet, DHCP, a `10.42.0.x` address | The cable is in a LAN port instead of WAN, or `brume-link` is down |
| Each rig: `ethtool enp0s31f6 \| grep -E 'Speed\|Duplex'` | `1000Mb/s`, `Full` | Swap the cable or the Flint port (Rig 1 linked at 100 Mb/s until a cable/port change) |
| Each rig: `curl -I https://example.com` | HTTP headers | Check the chain upstream: the Flint, then the Mac mini |

## Pitfalls

| Symptom | Likely cause | Fix |
|---|---|---|
| `wlp2s0` missing from `nmcli device` | `wl` driver not loaded (kernel update or Secure Boot) | Re-run Step 1's checks; reinstall `broadcom-sta-dkms`; enroll the MOK if Secure Boot is on. Use the USB dongle meanwhile |
| `PUSD open test` won't connect | The pinned access point is down, or the Mac mini moved rooms | Redo Step 2's scan and update the BSSID with `nmcli connection modify` |
| Router has no WAN address | Cable in a LAN port, or `brume-link` is down | Use the WAN port; `nmcli connection up brume-link` |
| `ping` fails but browsing works | The school drops ICMP | Normal. Test with `curl` |
| A rig links at 100 Mb/s | Cable or port | Swap the cable or move to another Flint port, then re-check `ethtool` |

**Fallback uplink:** the Mac mini's USB dongle can carry the school connection on the encrypted OWE side: `nmcli connection up "PUSD onboard" ifname $(nmcli -t -f DEVICE device | grep ^wlx)`.

## Open items

- **The WireGuard tunnel to EC2** is Sprint 5 networking work. Its planned steps are in the [pending playbook](../pending-playbook.md).
- **Mac mini reboot test** with the USB dongle unplugged: pending. It must pass before anything depends on the uplink.
- **The uplink is unencrypted.** The built-in card is on the open side of the school Wi-Fi. Until the tunnel is live, anything not using HTTPS can be seen by others on that Wi-Fi.
- **Throughput.** Every byte to the internet crosses one Wi-Fi link and the Mac mini. Measured ~84 Mb/s shared on 2026-10-23. The hops haven't been measured one by one.
- **Double NAT.** The Mac mini and the Flint both NAT. Outbound is fine. Inbound access should come through NetBird (or the planned tunnel), not port forwarding.
- **Single points of failure:** one Mac mini, one pinned access point, and one out-of-tree driver carry the whole network. `wl` is unmaintained, so a routine kernel update can take down the uplink.
- **The LAN is shared.** Other groups use Flint ports 5 and 6, so their devices are on the rigs' subnet. The rigs' orchestrators listen on `0.0.0.0:9000` with no host firewall ([status](../../docs/status.md)). Firewalling them is a Sprint 5 item.

## Sources

- The team's original PDF of this playbook (2026-10-16), replaced by this version on 2026-10-23. It's in the git history at `evidence/sprint4/OCS_Rig_Routing_Playbook.pdf`, and it holds the planned tunnel steps as first written
- Ports, SSID, and 5 GHz-only Wi-Fi: reported by the team on 2026-10-23
- Measurements: [Rig 1 gigabit link](../captures/2026-10-22-rig1-gigabit-link.md), [rig-to-rig iperf3](../captures/2026-10-22-rig-to-rig-iperf3.md), [internet throughput](../captures/2026-10-23-rig-internet-throughput.md)
- [Network](../../docs/architecture/network.md#the-ocs-lan), the canonical description of the LAN
