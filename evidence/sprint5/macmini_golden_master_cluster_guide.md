---
date: 2026-10-23
---

# 20-Node Mac mini (`Macmini7,1`) Golden Master & ML Cluster Deployment Guide

This step-by-step runbook covers turning **20 Late 2014 Mac minis (`Macmini7,1`)** into an **80-thread, 320 GB RAM distributed Linux & ML cluster** running [Ubuntu 26.04 LTS (Resolute Raccoon)](https://discourse.ubuntu.com/t/ubuntu-26-04-1-lts-released/86808) using a single **5-port Gigabit Ethernet switch**.

By keeping the Golden Master image under **14 GB of used disk space** and using [Clonezilla Live Lite Server](https://clonezilla.org/show-live-doc-content.php?topic=clonezilla-live/doc/11_lite_server) in UDP multicast mode, you can image **4 Mac minis simultaneously every 4 minutes** (all 19 target machines in 5 quick batches, ~20 minutes total) with working Broadcom BCM4360 Wi-Fi, unique hostnames (`macmini-XXXX`), automatic [Tailscale](https://tailscale.com/docs/features/tailscale-ssh) + [NetBird](https://docs.netbird.io/manage/peers/register-machines-using-setup-keys) mesh registration, [Slurm](https://slurm.schedmd.com/quickstart_admin.html), [Ray](https://docs.ray.io/en/latest/ray-core/starting-ray.html), and distributed LLM inference via [`llama.cpp` RPC](https://sharedllm.org/blog/llama-cpp-rpc-distributed-inference.html) and [FLINT-style](https://arxiv.org/abs/2608.25062) flash-tiered memory mapping.

## 1. Cluster Architecture & Software Stack Overview

Each `Macmini7,1` has an Intel Core i5-4278U (2 cores / 4 threads @ 2.6–3.1 GHz, Haswell-ULT with **AVX2** and **FMA3** vector instructions), **16 GB LPDDR3 RAM**, a **Broadcom BCM4360 (`14e4:43a0` rev 03)** 802.11ac Wi-Fi card, and Gigabit Ethernet.

| Category | Software / Tool | Purpose in the 20-Node Mac mini Cluster |Size Impact |
| :--- | :--- | :--- | :--- |
| **OS & Wi-Fi** | [Ubuntu 26.04 LTS](https://ubuntu.com/desktop/docs/en/latest/how-to/upgrade-ubuntu-desktop/) + [`broadcom-sta-dkms`](https://www.ubuntuupdates.org/package/core/resolute/restricted/base/broadcom-sta-dkms) | Pre-compiles the proprietary Broadcom `wl.ko` kernel module against Linux 7.0 once on the Golden Master so Wi-Fi works on first boot on all 20 nodes. | ~15 MB |
| **Hardware & Cooling** | [`mbpfan`](https://datcu-andrei-2.gitbook.io/maclinuxfancontrol/mbpfan) + `pciutils` (`setpci`) + `lm-sensors` | Spins fans up early (2000 RPM floor, 78°C max) for stacked Macs and programs Intel LPC register `0xa4` ([SuperUser](https://superuser.com/questions/212434/how-to-reboot-after-power-failure-for-mac-mini-running-ubuntu)) so all 20 Macs **auto-boot after a power outage**. | < 5 MB |
| **Memory & Headless Mode** | `zram-tools` (`zstd`) + `multi-user.target` | Compresses 50% of RAM in-memory (~21 GB effective memory per node) and disables the idle GNOME GUI on workers to **save 1.4 GB RAM per node** (28 GB across the cluster) and prevent headless auto-sleep. | < 2 MB |
| **Mesh VPN & Access** | [Tailscale](https://tailscale.com/docs/features/access-control/auth-keys) (`--ssh`) + [NetBird](https://docs.netbird.io/get-started/install/linux) + `openssh-server` | First-boot systemd script registers each cloned node as a unique `macmini-XXXX` peer on your Tailnet and NetBird mesh without duplicate identity collisions. | ~80 MB |
| **Distributed Compute** | [Ray](https://docs.ray.io/en/latest/ray-overview/installation.html) (`ray[default,serve]`) + [`uv`](https://www.anyscale.com/blog/uv-ray-pain-free-python-dependencies-in-clusters) | Replaces a bloated 5 GB Anaconda install with a fast, shared `/opt/cluster-venv` managed by `uv` (~350 MB total) for distributed Python and Ray Serve. | ~350 MB |
| **HPC Job Scheduling** | [Slurm](https://slurm.schedmd.com/quickstart_admin.html) (`slurm-wlm`) + `munge` + `chrony` | Pre-bakes a shared `/etc/munge/munge.key` across all 20 nodes before cloning and enforces strict NTP clock sync via `chrony` so Munge auth never fails. | ~65 MB |
| **LLM Inference Stack** | [`llama.cpp` RPC](https://sharedllm.org/blog/llama-cpp-rpc-distributed-inference.html) (`GGML_RPC=ON`) + Ollama + [Exo](https://github.com/exo-explore/exo) | Runs `rpc-server` on every Mac mini (port `50052`) to pool up to **280+ GB of cluster RAM** for 70B+ GGUF models, plus [FLINT-style](https://arxiv.org/abs/2608.25062) `--mmap` flash streaming from shared storage. | ~180 MB |
| **Cluster Ops & Expansion** | `clustershell` (`clush`), `ansible`, `nfs-common`, `nfs-kernel-server`, `autofs`, `prometheus-node-exporter`, `btop`, `tmux`, `iperf3`, `avahi-daemon` | Parallel shell execution across all 20 nodes (`clush -g all`), shared `/mnt/cluster` NFS storage for LLM weights, `.local` mDNS discovery, and live metrics. | ~120 MB |

## 2. Phase 1: Create Your macOS Recovery Fallback USB (Optional Insurance)

Before wiping your macOS Mac minis, note that you can **always** revert any `Macmini7,1` back to macOS:
1. **Built-in Firmware Recovery (Zero prep):** Hold **Command (⌘) + Option (⌥) + R** at power-on to launch Apple's EFI **Internet Recovery** ([Apple Support](https://support.apple.com/en-us/102655)), open **Disk Utility**, erase the internal drive as **APFS (GUID Partition Map)**, and click **Reinstall macOS**.
2. **Offline USB Installer (Fastest for multiple Macs):** On one of the macOS Mac minis before wiping it, download **macOS Monterey** from the App Store, insert a 16 GB+ USB drive named `MyVolume`, and run Apple's [`createinstallmedia` command](https://support.apple.com/en-us/101578):
   ```bash
   sudo /Applications/Install\ macOS\ Monterey.app/Contents/Resources/createinstallmedia --volume /Volumes/MyVolume
   ```

## 3. Phase 2: Build the Golden Master on Node 1 (`toby@ubuntu-macmini`)

Use your already-installed Ubuntu Mac mini (`toby@ubuntu-macmini`) as the **Golden Master**.

### Step 3.1 — Upgrade to Ubuntu 26.04 LTS & Install Base Packages
If you haven't upgraded from Ubuntu 24.04.4 LTS to [Ubuntu 26.04.1 LTS](https://ubuntu.com/desktop/docs/en/latest/how-to/upgrade-ubuntu-desktop/) yet, run the in-place upgrade first, then install the full cluster toolset:

```bash
# 1. Upgrade 24.04.4 LTS -> 26.04.1 LTS in place (skip if already on 26.04)
sudo apt update && sudo apt full-upgrade -y
sudo do-release-upgrade

# 2. Once booted into Ubuntu 26.04 LTS, enable repositories and install cluster packages
sudo add-apt-repository -y restricted universe multiverse
sudo apt update && sudo apt full-upgrade -y

sudo apt install -y \
  broadcom-sta-dkms openssh-server mbpfan pciutils lm-sensors \
  chrony zram-tools avahi-daemon avahi-utils \
  nfs-common nfs-kernel-server autofs \
  munge slurm-wlm slurm-wlm-doc \
  clustershell pdsh ansible sshpass \
  prometheus-node-exporter btop htop iotop tmux screen \
  iperf3 ethtool net-tools nmap socat jq curl wget rsync git \
  build-essential cmake ninja-build pkg-config \
  libcurl4-openssl-dev libopenblas-dev python3-pip python3-venv
```

### Step 3.2 — Apply `Macmini7,1` Hardware, Thermal, & Headless RAM Tweaks
When 20 Mac minis are stacked on a shelf running distributed LLM or Ray jobs, three hardware issues will bite you unless configured in the Golden Master:
1. **Power Outage Brick:** By default, a `Macmini7,1` stays powered off after an AC power interruption. Setting PCI register `0xa4` on bus `00:1f.0` ([Intel LPC Controller](https://superuser.com/questions/212434/how-to-reboot-after-power-failure-for-mac-mini-running-ubuntu)) tells the Mac mini PMU to boot automatically as soon as power returns.
2. **Thermal Throttling:** Apple's default SMC curve waits too long to spin up the blower fan under Linux. [`mbpfan`](https://datcu-andrei-2.gitbook.io/maclinuxfancontrol/mbpfan) keeps the Haswell CPU cool under sustained AVX2 load.
3. **Headless Suspend & GUI RAM Drain:** Booting into `multi-user.target` saves **~1.4 GB RAM per Mac mini** while keeping GNOME installed if you ever plug in a monitor (`sudo systemctl start gdm3`).

Run this block on the Golden Master:

```bash
# 1. Configure mbpfan for stacked cluster cooling (2000 RPM min, 78C max target)
sudo sed -i 's/^min_fan1_speed.*/min_fan1_speed = 2000/' /etc/mbpfan.conf
sudo sed -i 's/^max_temp.*/max_temp = 78/' /etc/mbpfan.conf
sudo systemctl enable --now mbpfan

# 2. Create systemd service to enable Auto-Power-On after power loss (Macmini7,1 LPC register)
sudo tee /etc/systemd/system/macmini-autoresume.service > /dev/null << 'EOF'
[Unit]
Description=Enable Macmini7,1 Auto Power-On After AC Power Loss
After=multi-user.target

[Service]
Type=oneshot
ExecStart=/usr/bin/setpci -s 00:1f.0 0xa4.b=0
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl enable --now macmini-autoresume.service

# 3. Enable ZRAM compressed swap (50% of 16GB RAM with zstd = ~21GB effective RAM headroom)
sudo tee /etc/default/zramswap > /dev/null << 'EOF'
ALGO=zstd
PERCENT=50
PRIORITY=100
EOF
sudo systemctl restart zramswap

# 4. Tune sysctl for distributed ML networking (Ray, Slurm, and llama.cpp RPC)
sudo tee /etc/sysctl.d/99-macmini-cluster.conf > /dev/null << 'EOF'
vm.swappiness = 80
vm.overcommit_memory = 1
net.core.rmem_max = 67108864
net.core.wmem_max = 67108864
net.ipv4.tcp_rmem = 4096 87380 67108864
net.ipv4.tcp_wmem = 4096 65536 67108864
fs.inotify.max_user_watches = 524288
EOF
sudo sysctl --system

# 5. Disable sleep/suspend and set headless multi-user boot target
sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target
sudo systemctl set-default multi-user.target
```

### Step 3.3 — Install `uv` + Ray + Slurm/Munge (Keeping Disk Size Small)
Your screenshot shows `(base)` from Conda/Miniconda. A full Anaconda directory can easily bloat to 5–8 GB. If you aren't using heavy Conda environments yet, replace or supplement it with [`uv`](https://www.anyscale.com/blog/uv-ray-pain-free-python-dependencies-in-clusters) and a clean shared `/opt/cluster-venv` (~350 MB):

```bash
# 1. Install uv globally to /usr/local/bin
curl -LsSf https://astral.sh/uv/install.sh | sudo env UV_INSTALL_DIR="/usr/local/bin" sh

# 2. Create a lean shared Python environment in /opt/cluster-venv with Ray & ML clients
sudo mkdir -p /opt/cluster-venv && sudo chown -R toby:toby /opt/cluster-venv
uv venv /opt/cluster-venv --python 3.12
source /opt/cluster-venv/bin/activate
uv pip install --no-cache-dir \
  "ray[default,serve,data]" \
  openai huggingface_hub hf_transfer \
  numpy scipy psutil requests tqdm fastapi uvicorn

# Make /opt/cluster-venv default for non-interactive SSH, Slurm, and Ray workers
sudo tee /etc/profile.d/cluster-venv.sh > /dev/null << 'EOF'
export PATH="/opt/cluster-venv/bin:/usr/local/bin:$PATH"
export HF_HUB_ENABLE_HF_TRANSFER=1
EOF

# 3. Pre-generate the shared Munge cryptographic key for Slurm!
# Because we do this BEFORE cloning, all 20 Mac minis will share the exact same key automatically.
sudo create-munge-key -f
sudo chown munge:munge /etc/munge/munge.key
sudo chmod 0400 /etc/munge/munge.key
sudo systemctl enable --now munge

# 4. Create shared NFS directory structure for LLM weights and Slurm job scripts
sudo mkdir -p /mnt/cluster/models /mnt/cluster/jobs /mnt/cluster/ray
sudo chown -R toby:toby /mnt/cluster
```

### Step 3.4 — Build the Distributed LLM Inference Stack (`llama.cpp` RPC + FLINT Flash Tiering + Ollama)
Because the `Macmini7,1` uses an Intel Haswell CPU (AVX2, no discrete NVIDIA GPU) with 16 GB LPDDR3 RAM and flash storage, the best-performing LLM inference stack combines three complementary modes:
* **Distributed RAM Pooling (`llama.cpp` with `GGML_RPC=ON`):** Runs a lightweight `rpc-server` daemon on port `50052` on every Mac mini ([`llama.cpp` RPC Docs](https://sharedllm.org/blog/llama-cpp-rpc-distributed-inference.html)), allowing your head node to slice a 70B+ parameter model across 4–8 Mac minis over the network.
* **FLINT-Style Flash-Tiered Streaming (`--mmap` + Sparse MoE GGUF):** Inspired by [FLINT (Flash Inference Tier)](https://arxiv.org/abs/2608.25062), running Mixture-of-Experts models (such as `Qwen3-30B-A3B-GGUF` where only 3B parameters are active per token) with memory-mapped flash I/O (`--mmap`) lets each 16 GB Mac mini stream inactive expert weights directly from SSD/flash while keeping hot attention and router weights pinned in RAM.
* **Scale-Out Ray Serve + Ollama:** Runs 20 independent quantized 8B–14B models (one per Mac mini) behind a single OpenAI-compatible router.

Compile and enable the inference stack on the Golden Master (**do not download multi-GB model `.gguf` files yet** so your clone image stays tiny!):

```bash
# 1. Compile llama.cpp with Distributed RPC (GGML_RPC=ON) and Haswell AVX2 + OpenBLAS
sudo mkdir -p /opt/llama.cpp && sudo chown -R toby:toby /opt/llama.cpp
git clone --depth 1 https://github.com/ggml-org/llama.cpp.git /opt/llama.cpp
cd /opt/llama.cpp

cmake -B build \
  -DGGML_RPC=ON \
  -DGGML_BLAS=ON \
  -DGGML_BLAS_VENDOR=OpenBLAS \
  -DGGML_NATIVE=ON \
  -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release -j 4
sudo cp build/bin/llama-server build/bin/llama-cli build/bin/rpc-server build/bin/llama-bench /usr/local/bin/
rm -rf /opt/llama.cpp/build

# 2. Create systemd service so every cloned Mac mini runs an RPC memory worker automatically
sudo tee /etc/systemd/system/llama-rpc.service > /dev/null << 'EOF'
[Unit]
Description=llama.cpp Distributed RPC Worker (Exposes 14 GB RAM on Port 50052)
After=network-online.target
Wants=network-online.target

[Service]
User=toby
ExecStart=/usr/local/bin/rpc-server -H 0.0.0.0 -p 50052 -m 14000
Restart=always
RestartSec=5
LimitMEMLOCK=infinity

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl enable llama-rpc.service

# 3. Install Ollama binary (configured to listen on 0.0.0.0 and read models from /mnt/cluster/models)
curl -fsSL https://ollama.com/install.sh | sh
sudo mkdir -p /etc/systemd/system/ollama.service.d
sudo tee /etc/systemd/system/ollama.service.d/override.conf > /dev/null << 'EOF'
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
Environment="OLLAMA_MODELS=/mnt/cluster/models/ollama"
Environment="OLLAMA_FLASH_ATTENTION=1"
EOF
sudo systemctl daemon-reload
```

## 4. Phase 3: Configure Clone-Safe Tailscale, NetBird, & Passwordless Cluster SSH

**CRITICAL CLONING TRAP:** Never run `tailscale up` or `netbird up` before cloning without wiping their state files afterward. If `/var/lib/tailscale/tailscaled.state` or `/etc/netbird/config.json` is baked into the disk image, all 20 Mac minis will wake up with the **exact same VPN cryptographic node ID** and constantly kick each other off your Tailnet and NetBird network!

Instead, we install the binaries now, set up passwordless intra-cluster SSH for user `toby`, and install a **First-Boot Auto-Join Service (`cluster-firstboot.service`)** that runs once when each cloned Mac mini boots up.

### Step 4.1 — Install Tailscale, NetBird, and Intra-Cluster SSH Keys
```bash
# 1. Install Tailscale and NetBird CLI packages
curl -fsSL https://tailscale.com/install.sh | sh
curl -fsSL https://pkgs.netbird.io/install.sh | sh

# 2. Generate a shared cluster SSH keypair for user 'toby' so any Mac mini can SSH into any other Mac mini
sudo -u toby mkdir -p /home/toby/.ssh
sudo -u toby ssh-keygen -t ed25519 -N "" -f /home/toby/.ssh/id_ed25519
cat /home/toby/.ssh/id_ed25519.pub >> /home/toby/.ssh/authorized_keys

# OPTIONAL: Append your own laptop/workstation public key here too:
# echo "ssh-ed25519 AAAA... your-laptop" >> /home/toby/.ssh/authorized_keys

sudo tee /home/toby/.ssh/config > /dev/null << 'EOF'
Host macmini-* 10.* 100.* 192.168.*
    StrictHostKeyChecking accept-new
    UserKnownHostsFile /dev/null
    LogLevel ERROR
EOF
sudo chown -R toby:toby /home/toby/.ssh
sudo chmod 700 /home/toby/.ssh
sudo chmod 600 /home/toby/.ssh/authorized_keys /home/toby/.ssh/config
```

### Step 4.2 — Create the First-Boot Auto-Provisioning Script (`cluster-firstboot.service`)
1. Open your [Tailscale Admin Console → Settings → Keys](https://tailscale.com/docs/features/access-control/auth-keys) and generate an **Auth Key** with **Reusable = ON** (and Ephemeral = OFF).
2. Open your [NetBird Dashboard → Setup Keys](https://docs.netbird.io/manage/peers/register-machines-using-setup-keys) and create a **Reusable Setup Key** (set usage limit to at least 25).
3. Paste both keys into `/etc/cluster-secrets.env` and install the first-boot script below:

```bash
# 1. Store your reusable Tailscale Auth Key and NetBird Setup Key
sudo tee /etc/cluster-secrets.env > /dev/null << 'EOF'
TS_AUTHKEY="tskey-auth-REPLACE_WITH_YOUR_REUSABLE_TAILSCALE_KEY"
NB_SETUPKEY="REPLACE_WITH_YOUR_REUSABLE_NETBIRD_SETUP_KEY"
WIFI_SSID="YOUR_WIFI_SSID"
WIFI_PASS="YOUR_WIFI_PASSWORD"
EOF
sudo chmod 600 /etc/cluster-secrets.env

# 2. Create the First-Boot script that uniquely names and registers each cloned Mac mini
sudo tee /usr/local/sbin/cluster-firstboot.sh > /dev/null << 'EOF'
#!/usr/bin/env bash
set -euo pipefail
source /etc/cluster-secrets.env

# A. Generate unique hostname from the last 4 hex chars of the hardware MAC address (e.g., macmini-8f2a)
MAC_HEX=$(ip -o link show | awk '/link\/ether/ {print $2; exit}' | tr -d ':' | tail -c 5)
NODE_NAME="macmini-${MAC_HEX}"
hostnamectl set-hostname "${NODE_NAME}"
sed -i "s/^127\.0\.1\.1.*/127.0.1.1\t${NODE_NAME}/" /etc/hosts

# B. Regenerate unique systemd machine-id and OpenSSH host keys
rm -f /etc/machine-id /var/lib/dbus/machine-id
dbus-uuidgen --ensure=/etc/machine-id
systemd-machine-id-setup
rm -f /etc/ssh/ssh_host_*
dpkg-reconfigure openssh-server
systemctl restart ssh

# C. Connect to Wi-Fi via NetworkManager (if WIFI_SSID is set and not already connected)
if [[ -n "${WIFI_SSID:-}" && "${WIFI_SSID}" != "YOUR_WIFI_SSID" ]]; then
    nmcli device wifi rescan || true
    sleep 3
    nmcli device wifi connect "${WIFI_SSID}" password "${WIFI_PASS}" || true
fi

# D. Wait up to 45 seconds for internet connectivity
for i in {1..15}; do
    ping -c 1 -W 2 1.1.1.1 >/dev/null 2>&1 && break
    sleep 3
done

# E. Wipe any stale VPN state, then join Tailscale (with Tailscale SSH enabled) and NetBird
systemctl stop tailscaled netbird || true
rm -rf /var/lib/tailscale/tailscaled.state /etc/netbird/config.json

systemctl enable --now tailscaled
sleep 2
if [[ "${TS_AUTHKEY}" != *"REPLACE"* ]]; then
    tailscale up --auth-key="${TS_AUTHKEY}" --ssh --hostname="${NODE_NAME}" --accept-routes || true
fi

systemctl enable --now netbird
sleep 2
if [[ "${NB_SETUPKEY}" != *"REPLACE"* ]]; then
    netbird up --setup-key="${NB_SETUPKEY}" --hostname="${NODE_NAME}" || true
fi

# F. Mark first-boot complete so this script never runs again
touch /etc/cluster-firstboot-done
systemctl disable cluster-firstboot.service
EOF
sudo chmod +x /usr/local/sbin/cluster-firstboot.sh

# 3. Register the systemd unit
sudo tee /etc/systemd/system/cluster-firstboot.service > /dev/null << 'EOF'
[Unit]
Description=Mac mini Cluster First-Boot Identity, Wi-Fi, Tailscale, and NetBird Provisioner
After=network-online.target NetworkManager.service
Wants=network-online.target
ConditionPathExists=!/etc/cluster-firstboot-done

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/cluster-firstboot.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl enable cluster-firstboot.service
```

### Step 4.3 — Clean, Seal, and Power Off the Golden Master for Cloning
Right before you start cloning, run this cleanup block so your Golden Master disk image is as small as possible and ready for `cluster-firstboot.service` to run on both the Master and all 19 clones:

```bash
# Clean APT caches, Conda caches (if any), and systemd journals to shrink image size
sudo apt autoremove -y && sudo apt clean
sudo journalctl --vacuum-time=1s
rm -rf ~/.cache/pip ~/.cache/uv ~/.cache/huggingface

# Clear VPN identities and machine-id so every machine (including this Master on next boot) gets a clean registration
sudo tailscale logout || true
sudo systemctl stop tailscaled netbird || true
sudo rm -rf /var/lib/tailscale/tailscaled.state /etc/netbird/config.json /etc/cluster-firstboot-done
sudo truncate -s 0 /etc/machine-id
sudo rm -f /etc/ssh/ssh_host_*

# Shut down cleanly
sudo poweroff
```

## 5. Phase 4: Clone 19 Mac minis in 5 Batches Using Your 5-Port Switch

With a **5-port Gigabit Ethernet switch**, you don't need an external hard drive to store an intermediate image, and you don't need the switch connected to your router during cloning. Using [Clonezilla Live Lite Server's `from-device` Multicast mode](https://clonezilla.org/show-live-doc-content.php?topic=clonezilla-live/doc/11_lite_server), your Golden Master streams its internal SSD directly over UDP multicast to **4 target Mac minis simultaneously**.

### Switch Port Layout (5 Batches: 4 + 4 + 4 + 4 + 3 Machines)
* **Port 1:** Golden Master `Macmini7,1` (booted from a Clonezilla Live USB stick — stays running across all 5 batches).
* **Ports 2, 3, 4, 5:** 4 Target `Macmini7,1` machines per batch (each booted from a Clonezilla Live USB stick).
* *Why use 5 cheap USB sticks instead of Apple NetBoot/PXE?* Intel Mac EFI firmware uses Apple's proprietary BSDP protocol rather than standard BIOS PXE, which frequently fails to netboot standard Linux PXE menus without custom DHCP vendor options. Flashing **5 cheap 8 GB USB sticks** with the tiny 450 MB [Clonezilla Live ISO](https://clonezilla.org/downloads.php) takes 2 minutes and works 100% of the time by holding **Option (⌥)**.

### Step 5.1 — Start the Golden Master as the Multicast Lite Server (Port 1)
1. Plug your Golden Master into **Port 1** of the unplugged 5-port switch (keep the switch isolated from your home/office LAN during cloning).
2. Insert Clonezilla USB #1 into the Golden Master, hold **Option (⌥)** at power-on, and choose **EFI Boot**.
3. Follow the Clonezilla prompts on the Golden Master:
   * Choose **Default settings (800x600)** → **Start_Clonezilla**.
   * Select **`lite-server`** (*Start a Clonezilla lite server for massive deployment*).
   * Select **`massive-deployment`** (*Massive deployment by multicast or broadcast*).
   * Select **`from-device`** (*Clone directly from local disk/partition to client machines*).
   * Select **`net-default`** → **`dhcpd`** (*Start DHCP service on this isolated 5-port switch*).
   * Select **`boot-from-live-media`** (*Clients will boot from their own Clonezilla USB sticks*).
   * Select **`savedisk`** (*Clone entire disk*) and pick **`sda`** (your Golden Master internal SSD).
   * When asked whether to check/repair the source filesystem, choose **`-fsck-src-part-y`** (or skip if you just shut down cleanly).
   * Select **`-p poweroff`** (*Clients automatically power off when cloning finishes*).
   * Select **`multicast`** → **`clients + time-to-wait`** → enter **`4`** clients (and `300` seconds timeout).
   * Clonezilla is now waiting for your first batch of 4 target Mac minis to connect!

### Step 5.2 — Clone Batch 1 (4 Target Mac minis on Ports 2–5)
1. Plug 4 macOS Mac minis into **Ports 2, 3, 4, and 5** of the switch and insert Clonezilla USB sticks #2–#5.
2. Hold **Option (⌥)** at power-on on each of the 4 target Mac minis and select **EFI Boot**.
3. On each target Mac mini:
   * Select **Start_Clonezilla** → **`lite-client`** → **`dhcp`**.
   * It will automatically detect the Golden Master server on Port 1 and join the `restoredisk` multicast session!
4. Once the 4th Mac mini joins, Clonezilla automatically wipes the old macOS partitions and streams the ~14 GB Ubuntu 26.04 image to all 4 Mac minis at once in **~4 minutes**.
5. When all 4 target Mac minis automatically power off:
   * Unplug them from the switch, pull out the 4 Clonezilla USB sticks, and plug the next 4 macOS Mac minis into Ports 2–5.
   * On the Golden Master (Port 1), re-run the multicast broadcast for the next batch of 4 (on the 5th and final batch of 3 Mac minis, set client count to **`3`**).

## 6. Phase 5: First Boot & Cluster Activation

As you power on your newly cloned Mac minis (on Wi-Fi or LAN), `cluster-firstboot.service` runs automatically on each node:
* Each node renames itself `macmini-XXXX` (using the last 4 hex digits of its MAC address).
* Each node connects to Wi-Fi via `broadcom-sta-dkms` (or Ethernet).
* Each node joins your **Tailscale** tailnet (with **Tailscale SSH** enabled) and your **NetBird** mesh as a distinct peer!

Verify all 20 nodes from your primary node (which we'll call `macmini-head`):

### Step 6.1 — Configure `ClusterShell` (`clush`) to Control All 20 Nodes at Once
```bash
# Automatically populate /etc/clustershell/groups.d/local.cfg from your active Tailscale nodes
HEAD_HOST=$(hostname)
ALL_NODES=$(tailscale status | awk '/macmini-/ {print $2}' | sort -u | paste -sd, -)
WORKERS=$(tailscale status | awk '/macmini-/ {print $2}' | grep -v "^${HEAD_HOST}$" | sort -u | paste -sd, -)

sudo tee /etc/clustershell/groups.d/local.cfg > /dev/null << EOF
all: ${ALL_NODES}
head: ${HEAD_HOST}
workers: ${WORKERS}
EOF

# Test running a command across all 20 Mac minis in parallel!
clush -g all "hostname && uname -r && ip -br a show wl* && systemctl is-active llama-rpc"
```

### Step 6.2 — Export `/mnt/cluster` Over NFS from the Head Node
So you only ever have to download a 40 GB LLM `.gguf` model or dataset **once**, export `/mnt/cluster` from your head node and mount it across all 19 workers:

```bash
# 1. On the head node, export /mnt/cluster over Tailscale (100.64.0.0/10) and LAN
echo "/mnt/cluster 100.64.0.0/10(rw,sync,no_subtree_check,no_root_squash) 192.168.0.0/16(rw,sync,no_subtree_check,no_root_squash) 10.0.0.0/8(rw,sync,no_subtree_check,no_root_squash)" | sudo tee -a /etc/exports
sudo exportfs -ra
sudo systemctl enable --now nfs-kernel-server

# 2. Mount /mnt/cluster on all 19 worker nodes in one shot via clush
HEAD_IP=$(tailscale ip -4 | head -n 1)
clush -g workers "sudo mount -t nfs ${HEAD_IP}:/mnt/cluster /mnt/cluster && echo '${HEAD_IP}:/mnt/cluster /mnt/cluster nfs defaults,_netdev,nofail 0 0' | sudo tee -a /etc/fstab"
```

### Step 6.3 — Activate Slurm Across All 20 Mac minis
Because `/etc/munge/munge.key` is already identical on all 20 nodes from the Golden Master, you only need to generate `/etc/slurm/slurm.conf` on the head node and broadcast it with `clush`:

```bash
# 1. Build the node list and write /etc/slurm/slurm.conf on the head node
NODE_CSV=$(tailscale status | awk '/macmini-/ {print $2}' | sort -u | paste -sd, -)
HEAD_HOST=$(hostname)

sudo tee /etc/slurm/slurm.conf > /dev/null << EOF
ClusterName=macmini-cluster
SlurmctldHost=${HEAD_HOST}
MungeSocket=/var/run/munge/munge.socket.2
AuthType=auth/munge
CryptoType=crypto/munge
ProctrackType=proctrack/cgroup
ReturnToService=2
SlurmctldPidFile=/var/run/slurmctld.pid
SlurmdPidFile=/var/run/slurmd.pid
SlurmdSpoolDir=/var/spool/slurmd
SlurmUser=slurm
StateSaveLocation=/var/spool/slurmctld
SwitchType=switch/none
TaskPlugin=task/affinity,task/cgroup
SchedulerType=sched/backfill
SelectType=select/cons_tres
SelectTypeParameters=CR_Core_Memory

# Macmini7,1 hardware definition: 1 Socket, 2 CoresPerSocket, 2 ThreadsPerCore (4 CPUs), ~15500MB usable RAM
NodeName=${NODE_CSV} CPUs=4 Sockets=1 CoresPerSocket=2 ThreadsPerCore=2 RealMemory=15000 State=UNKNOWN
PartitionName=macmini Nodes=${NODE_CSV} Default=YES MaxTime=INFINITE State=UP
EOF

sudo tee /etc/slurm/cgroup.conf > /dev/null << 'EOF'
CgroupMountpoint="/sys/fs/cgroup"
ConstrainCores=yes
ConstrainRAMSpace=yes
EOF

# 2. Push slurm.conf and cgroup.conf to all 20 nodes and start Slurm!
clush -g workers --copy /etc/slurm/slurm.conf --dest /etc/slurm/slurm.conf
clush -g workers --copy /etc/slurm/cgroup.conf --dest /etc/slurm/cgroup.conf
sudo mkdir -p /var/spool/slurmctld && sudo chown slurm:slurm /var/spool/slurmctld
sudo systemctl enable --now slurmctld
clush -g all "sudo mkdir -p /var/spool/slurmd && sudo chown slurm:slurm /var/spool/slurmd && sudo systemctl enable --now slurmd"

# 3. Verify all 20 nodes (80 CPUs) are idle and ready in Slurm!
sinfo
srun -N 20 hostname
```

### Step 6.4 — Start the 20-Node Ray Cluster
```bash
# Start Ray Head on your head node (Dashboard on port 8265)
HEAD_IP=$(tailscale ip -4 | head -n 1)
/opt/cluster-venv/bin/ray start --head --node-ip-address="${HEAD_IP}" --port=6379 --dashboard-host=0.0.0.0

# Join all 19 worker Mac minis to the Ray cluster in one command
clush -g workers "/opt/cluster-venv/bin/ray start --address=${HEAD_IP}:6379"

# Check cluster resources (should report 80.0 CPUs and ~300 GiB memory)
/opt/cluster-venv/bin/ray status
```

### Step 6.5 — Run Distributed & Flash-Tiered LLMs Across the Cluster
1. **Download a quantized GGUF model once into `/mnt/cluster/models`:**
   ```bash
   /opt/cluster-venv/bin/hf download bartowski/Qwen_Qwen3-30B-A3B-GGUF \
     Qwen_Qwen3-30B-A3B-Q4_K_M.gguf --local-dir /mnt/cluster/models
   ```
2. **Mode A — Distributed Multi-Node RPC Inference (Sharding 30B–70B+ Models Across Multiple Mac minis):**
   Every worker Mac mini is already running `rpc-server` on port `50052`. Point `llama-server` on the head node at your worker nodes:
   ```bash
   RPC_WORKERS=$(tailscale status | awk '/macmini-/ {print $1":50052"}' | head -n 4 | paste -sd, -)
   llama-server \
     -m /mnt/cluster/models/Qwen_Qwen3-30B-A3B-Q4_K_M.gguf \
     --host 0.0.0.0 --port 8080 \
     --rpc "${RPC_WORKERS}" \
     -ngl 99 --mmap -c 8192
   ```
3. **Mode B — FLINT-Style Single-Node Flash-Tiered MoE Inference (20 Parallel Workers via Slurm or Ray Serve):**
   Because `Qwen3-30B-A3B-Q4_K_M.gguf` (~18 GB) is a Mixture-of-Experts model with only 3B active parameters per token, `--mmap` + your 50% `zram` pool lets a **single** 16 GB Mac mini run it by keeping hot weights in RAM and streaming cold expert layers from flash storage.
