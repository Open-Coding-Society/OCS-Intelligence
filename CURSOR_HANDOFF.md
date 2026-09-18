# Cursor Agent Handoff: OCS Intelligence Inference Orchestrator

## 1. Project Goal & Core Objective

Host a low-latency, OpenAI-compatible API (`https://ai.opencodingsociety.com/v1/`) for **1–3 concurrent students** using **GitHub Copilot Chat**, while maintaining the existing Open WebUI interface at `https://ai.opencodingsociety.com/`.

### The Core Problem: Inter-GPU Latency Bottleneck
- The GPU rig has **7× NVIDIA GeForce GTX 1070** (8GB each, Pascal architecture / `sm_61`).
- All 7 GPUs are connected via **PCIe Gen 1 x1 risers (~250 MB/s physical bandwidth ceiling)**.
- Baseline with Ollama running across all 7 GPUs:
  - **~12.5 tokens/s** generation, ~2s warm TTFT, ~2.5 min cold start.
  - Every generated token requires **6 sequential inter-GPU transfers** across 250 MB/s x1 riser links.

### The Solution: 5+2 GPU Topology Split
Rather than distributing a model across all 7 cards (6 hops per token), split the rig into two isolated `llama-server` workers:
1. **Worker A (Group A — 5 GPUs):** GPUs 0, 1, 2, 3, 4 (`03:00.0` through `0C:00.0`)
   - Model: `qwen3.8:27b` (Q4_K_M, ~16.8 GB weights)
   - VRAM: 5 × 8 GB = 40 GB total VRAM. Leaves ~23 GB for KV cache and context.
   - Hops per token: **4 hops** (reduced from 6). Pinned always warm.
   - Note: GPUs 0 & 1 are the only `PIX` pair (PCIe switch connection); GPUs 2, 3, 4 are `PHB`.
2. **Worker B (Group B — 2 GPUs):** GPUs 5, 6 (`0E:00.0` and `0F:00.0`)
   - Model: `qwen2.5:0.5b` (Q4_K_M, ~380 MB weights)
   - VRAM: 2 × 8 GB = 16 GB total VRAM.
   - Hops per token: **1 hop** only! Ultra-fast responses for quick reasoning/queries.
3. **FastAPI Orchestrator:**
   - Runs locally on the rig at `0.0.0.0:9000`.
   - Routes requests by `model` name:
     - `qwen3.8:27b` -> `http://127.0.0.1:8081` (Worker A)
     - `qwen2.5:0.5b` -> `http://127.0.0.1:8082` (Worker B)
   - Provides Bearer API key auth, streaming SSE passthrough, connection pooling, and health checks.
4. **EC2 Gateway (`ai.opencodingsociety.com`):**
   - Nginx proxies `/v1/` over NetBird to `http://100.75.123.203:9000` (rig orchestrator).
   - Nginx keeps `/` proxying to `http://100.75.123.203:3000` (Open WebUI).

---

## 2. Infrastructure & Access Guide (Cursor Terminal Instructions)

The local machine accesses remote hosts over a NetBird overlay network running inside a Docker container named `netbird-dev`.

### How to Open an Interactive Shell
Because NetBird SSH uses web-based SSO, launching commands non-interactively triggers an SSO authentication link for each individual command. **To avoid repeated auth prompts, open an interactive terminal in Cursor:**

```bash
docker exec -it netbird-dev sh
```

From inside the container, SSH into the target machine:
```bash
# To access the GPU Rig:
ssh root@100.75.123.203

# To access the EC2 Gateway:
ssh root@100.75.172.167
```

**SSO Login:**
When you first run `ssh root@100.75.123.203`, NetBird will output:
```text
SSH authentication required.
Please do the SSO login in your browser.
URL: https://login.netbird.io/activate?user_code=XXXX-XXXX
```
Open that link in your browser, approve it, and the terminal will immediately log in as `root@ocs-intelligence-rig`. **As long as you keep that terminal session open, you can run all commands interactively without re-authenticating.**

---

## 3. Host Details & Network Topology

| Host | NetBird IP | Role | OS / Hardware | Ports |
|---|---|---|---|---|
| **GPU Rig** (`ocs-intelligence-rig`) | `100.75.123.203` | Inference workers + Orchestrator + Open WebUI | Ubuntu 24.04.4, ASUS B250 Mining Expert, 7× GTX 1070 (8GB) | `3000` (WebUI), `8081` (Worker A), `8082` (Worker B), `9000` (Orchestrator) |
| **EC2 Gateway** (`ip-172-31-42-43`) | `100.75.172.167` | Public TLS Gateway / Reverse Proxy | Ubuntu 24.04, AWS m5.large | `80`, `443` (`ai.opencodingsociety.com`) |

### GPU Inventory on Rig
Verified via `nvidia-smi`:
- GPU 0: `GPU-24899ea8-3258-0dd0-5aa4-6ef9104cdc68` (`03:00.0`, PIX with GPU 1) -> Group A
- GPU 1: `GPU-728d79b7-b5ed-e1ec-cf29-0572f97956ba` (`08:00.0`, PIX with GPU 0) -> Group A
- GPU 2: `GPU-fb4eb983-84aa-664f-b97d-94b12caffb37` (`0A:00.0`, PHB) -> Group A
- GPU 3: `GPU-71f15481-4db3-9d2a-8d30-6e68dba08617` (`0B:00.0`, PHB) -> Group A
- GPU 4: `GPU-bc07dc85-473b-9927-538e-986f80b80486` (`0C:00.0`, PHB) -> Group A
- GPU 5: `GPU-2a70bbf9-ed03-162f-ddd5-c7ed42149d84` (`0E:00.0`, PHB) -> Group B
- GPU 6: `GPU-a25606af-913d-22d1-5ebe-ecea656819cb` (`0F:00.0`, PHB) -> Group B

### Existing Model Blobs on Rig
Ollama stores GGUF files in raw blob format at `/usr/share/ollama/.ollama/models/blobs/`:
- **27B Model:** `sha256-f5f1dd8920d417aac2718b0bda3403da274301efdd6760b4f0f4b864ff2ad57d` (16,810,714,464 bytes, ~16 GB)
- **0.5B Model:** `sha256-c5396e06af294bd101b30dce59131a76d2b773e76950acc870eda801d3ab0515` (380 MB)

---

## 4. Current Work Done & Files Created in this Repo

The following production code and configurations have already been written into `/home/adikatre/nighthawk/OCS-Intelligence/`:

### Orchestrator Code (`orchestrator/`)
- `orchestrator/__init__.py`: Package init.
- `orchestrator/config.py`: Configuration loaded via environment variables (`GROUP_A_URL`, `GROUP_B_URL`, `GROUP_A_MODEL_ALIAS`, `GROUP_B_MODEL_ALIAS`, `WORKER_API_KEY`, `PUBLIC_API_KEYS`, etc.).
- `orchestrator/auth.py`: Bearer token authentication against `PUBLIC_API_KEYS`.
- `orchestrator/health.py`: Background poller monitoring health status of Worker A and Worker B.
- `orchestrator/proxy.py`: Streaming SSE proxy (`httpx.AsyncClient` with connection pooling) and blocking proxy with client disconnect detection (`request.is_disconnected()`).
- `orchestrator/routing.py`: Model name resolver mapping requests to Worker A or B with proper OpenAI error envelopes (404, 503, 429).
- `orchestrator/main.py`: FastAPI app exposing `/healthz`, `/readyz`, `GET /v1/models`, `POST /v1/chat/completions`.
- `orchestrator/requirements.txt`: `fastapi`, `uvicorn[standard]`, `httpx`.

### systemd Services & Templates (`systemd/`)
- `systemd/ocs-llama-a.service`: Worker A service running `llama-server` on `127.0.0.1:8081` with `--parallel 2 --cont-batching --flash-attn --split-mode layer`.
- `systemd/ocs-llama-b.service`: Worker B service running `llama-server` on `127.0.0.1:8082`.
- `systemd/ocs-orchestrator.service`: Orchestrator service running Uvicorn on `0.0.0.0:9000`.
- `systemd/worker-a.env.template`: Pinned UUIDs for GPUs 0-4, context 4096, tensor split `1,1,1,1,1`.
- `systemd/worker-b.env.template`: Pinned UUIDs for GPUs 5,6, context 8192, tensor split `1,1`.
- `systemd/orchestrator.env.template`: Orchestrator environment settings and secrets placeholder.

---

## 5. Critical Technical Blocker & Resolution (CUDA 12 vs Pascal Architecture)

### The Issue
- The rig had `nvcc` installed in a Python virtual environment (`/home/ocs/.venv/...`) at version **CUDA 13.3**.
- **CUDA 13 completely dropped support for Pascal GPUs (`sm_61` / `compute_61`)!**
- Attempting `cmake -DCMAKE_CUDA_ARCHITECTURES=61` with CUDA 13 fails with:
  `nvcc fatal : Unsupported gpu architecture 'compute_61'`

### The Resolution
**Must install CUDA Toolkit 12.x on the rig** (CUDA 12 supports `compute_61`).
NVIDIA provides Ubuntu 24.04 packages:

```bash
# On the rig as root:
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/cuda-keyring_1.1-1_all.deb -O /tmp/cuda-keyring.deb
dpkg -i /tmp/cuda-keyring.deb
apt-get update
apt-get install -y cuda-toolkit-12-6
```

---

## 6. Step-by-Step Execution Plan for Cursor Agent

Follow these exact steps inside the interactive SSH terminal (`ssh root@100.75.123.203`):

### Step 1: Install CUDA 12.6 & Build Tools on Rig
```bash
apt-get update
apt-get install -y cmake git build-essential wget
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/cuda-keyring_1.1-1_all.deb -O /tmp/cuda-keyring.deb
dpkg -i /tmp/cuda-keyring.deb
apt-get update
apt-get install -y cuda-toolkit-12-6

# Verify nvcc
/usr/local/cuda-12.6/bin/nvcc --version
```

### Step 2: Compile llama.cpp with CUDA Architecture 61
```bash
mkdir -p /opt/llama.cpp
cd /opt/llama.cpp

if [ ! -d "src" ]; then
    git clone --depth=1 https://github.com/ggml-org/llama.cpp.git src
fi

cd src
rm -rf build
cmake -S . -B build \
  -DGGML_CUDA=ON \
  -DCMAKE_CUDA_COMPILER=/usr/local/cuda-12.6/bin/nvcc \
  -DCUDAToolkit_ROOT=/usr/local/cuda-12.6 \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CUDA_ARCHITECTURES=61

cmake --build build --config Release --parallel $(nproc)

# Install binaries to /opt/llama.cpp/bin
mkdir -p /opt/llama.cpp/bin
install -m 0755 build/bin/llama-server /opt/llama.cpp/bin/llama-server
install -m 0755 build/bin/llama-bench /opt/llama.cpp/bin/llama-bench

# Verify
/opt/llama.cpp/bin/llama-server --version
```

### Step 3: Set Up Model Directories and Symlinks
```bash
mkdir -p /srv/ocs-intelligence/models
mkdir -p /var/lib/ocs-intelligence
mkdir -p /etc/ocs-intelligence

# Symlink Ollama's 27B model blob:
ln -sf /usr/share/ollama/.ollama/models/blobs/sha256-f5f1dd8920d417aac2718b0bda3403da274301efdd6760b4f0f4b864ff2ad57d \
  /srv/ocs-intelligence/models/qwen3.8-27b-q4_k_m.gguf

# Symlink Ollama's 0.5B model blob:
ln -sf /usr/share/ollama/.ollama/models/blobs/sha256-c5396e06af294bd101b30dce59131a76d2b773e76950acc870eda801d3ab0515 \
  /srv/ocs-intelligence/models/qwen2.5-0.5b.gguf

ls -lh /srv/ocs-intelligence/models/
```

### Step 4: Configure & Enable llama.cpp systemd Workers
Generate a secure worker secret (e.g., `openssl rand -hex 24`).

**Create `/etc/ocs-intelligence/worker-a.env`:**
```ini
CUDA_VISIBLE_DEVICES=GPU-24899ea8-3258-0dd0-5aa4-6ef9104cdc68,GPU-728d79b7-b5ed-e1ec-cf29-0572f97956ba,GPU-fb4eb983-84aa-664f-b97d-94b12caffb37,GPU-71f15481-4db3-9d2a-8d30-6e68dba08617,GPU-bc07dc85-473b-9927-538e-986f80b80486
DEFAULT_MODEL_GGUF=/srv/ocs-intelligence/models/qwen3.8-27b-q4_k_m.gguf
DEFAULT_MODEL_ID=qwen3.8:27b
CONTEXT_SIZE=4096
TENSOR_SPLIT=1,1,1,1,1
WORKER_API_KEY=YOUR_SECURE_WORKER_SECRET
```

**Create `/etc/ocs-intelligence/worker-b.env`:**
```ini
CUDA_VISIBLE_DEVICES=GPU-2a70bbf9-ed03-162f-ddd5-c7ed42149d84,GPU-a25606af-913d-22d1-5ebe-ecea656819cb
SPEED_MODEL_GGUF=/srv/ocs-intelligence/models/qwen2.5-0.5b.gguf
SPEED_MODEL_ID=qwen2.5:0.5b
CONTEXT_SIZE=8192
TENSOR_SPLIT=1,1
WORKER_API_KEY=YOUR_SECURE_WORKER_SECRET
```

Secure the permissions:
```bash
chmod 0600 /etc/ocs-intelligence/worker-a.env /etc/ocs-intelligence/worker-b.env
```

Copy systemd files from repo (`systemd/ocs-llama-a.service`, `ocs-llama-b.service`) to `/etc/systemd/system/`:
```bash
# From the repo directory on the host:
# scp or copy into /etc/systemd/system/
systemctl daemon-reload
systemctl enable ocs-llama-a.service ocs-llama-b.service

# Note: Before starting, stop Ollama so VRAM is completely free:
systemctl stop ollama.service

systemctl start ocs-llama-a.service
systemctl start ocs-llama-b.service

# Check health:
curl -H "Authorization: Bearer YOUR_SECURE_WORKER_SECRET" http://127.0.0.1:8081/health
curl -H "Authorization: Bearer YOUR_SECURE_WORKER_SECRET" http://127.0.0.1:8082/health
```

### Step 5: Deploy the Orchestrator on Rig
```bash
mkdir -p /opt/ocs-orchestrator
mkdir -p /var/lib/ocs-orchestrator
mkdir -p /etc/ocs-orchestrator

# Copy orchestrator/ code from repo to /opt/ocs-orchestrator/
# Create venv:
python3 -m venv /opt/ocs-orchestrator/.venv
/opt/ocs-orchestrator/.venv/bin/pip install -r /opt/ocs-orchestrator/requirements.txt
```

**Create `/etc/ocs-orchestrator/orchestrator.env`:**
```ini
GROUP_A_URL=http://127.0.0.1:8081
GROUP_B_URL=http://127.0.0.1:8082
GROUP_A_MODEL_ALIAS=qwen3.8:27b
GROUP_B_MODEL_ALIAS=qwen2.5:0.5b
WORKER_API_KEY=YOUR_SECURE_WORKER_SECRET
PUBLIC_API_KEYS=sk-ocs-student-copilot-key
QUEUE_CAPACITY_PER_WORKER=16
CONNECT_TIMEOUT_SECONDS=5
RESPONSE_HEADER_TIMEOUT_SECONDS=600
STREAM_IDLE_TIMEOUT_SECONDS=300
HEALTH_INTERVAL_SECONDS=5
```

Install and start orchestrator service:
```bash
chmod 0600 /etc/ocs-orchestrator/orchestrator.env
cp systemd/ocs-orchestrator.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now ocs-orchestrator.service

# Test orchestrator locally on rig:
curl http://127.0.0.1:9000/healthz
curl -H "Authorization: Bearer sk-ocs-student-copilot-key" http://127.0.0.1:9000/v1/models
```

### Step 6: Update EC2 Nginx (`root@100.75.172.167`)
In `/etc/nginx/sites-available/llm-relay` (or active config for `ai.opencodingsociety.com`), add the `/v1/` block inside the `server { listen 443 ssl; ... }` block, directly before the `location /` block:

```nginx
location /v1/ {
    proxy_pass http://100.75.123.203:9000;
    proxy_http_version 1.1;

    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    proxy_set_header Connection "";
    proxy_buffering off;
    proxy_request_buffering off;
    proxy_cache off;

    proxy_connect_timeout 5s;
    proxy_read_timeout 600s;
    proxy_send_timeout 600s;

    client_max_body_size 2m;
}

location = /healthz {
    proxy_pass http://100.75.123.203:9000/healthz;
    access_log off;
}
```

Validate and reload Nginx on EC2:
```bash
nginx -t && systemctl reload nginx
```

### Step 7: Validation Test from Outside
From any development machine:
```bash
# 1. Test model list
curl -k https://ai.opencodingsociety.com/v1/models \
  -H "Authorization: Bearer sk-ocs-student-copilot-key"

# 2. Test fast model (0.5b on 2 GPUs)
curl -k -N https://ai.opencodingsociety.com/v1/chat/completions \
  -H "Authorization: Bearer sk-ocs-student-copilot-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5:0.5b",
    "messages": [{"role": "user", "content": "Write quick bubble sort in python"}],
    "stream": true
  }'

# 3. Test quality model (27b on 5 GPUs)
curl -k -N https://ai.opencodingsociety.com/v1/chat/completions \
  -H "Authorization: Bearer sk-ocs-student-copilot-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3.8:27b",
    "messages": [{"role": "user", "content": "Explain quicksort vs mergesort"}],
    "stream": true
  }'
```
