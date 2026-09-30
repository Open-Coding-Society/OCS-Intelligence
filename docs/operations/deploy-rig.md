---
status: draft
last_verified: 2026-09-18
---

# How to deploy the rig (workers + orchestrator)

Builds llama.cpp for Pascal and brings up Worker A, Worker B, and the orchestrator on a GPU rig. These are the steps **as actually deployed on Rig 1** (2026-09-17), with the fixes found along the way. The original plan is in the [archived handoff](../archive/cursor-handoff.md).

> **Draft:** nobody has re-run this from scratch yet. The blueprint's Week 1 exit is "anyone can reinstall from scratch", so run it on Rig 2, then fix this doc and set it to `current`.

Paths, ports, and unit names: [hosts](../reference/hosts.md). Env vars: [configuration](../reference/configuration.md).

## Before you start

- A root shell on the rig ([NetBird access](../guides/netbird-access.md)). Use one persistent session, because steps take over an hour.
- Ubuntu 24.04, NVIDIA driver installed, `nvidia-smi` shows every card.
- A copy of this repo on the rig, or `scp` access to copy `infra/rig/` and `orchestrator/`.
- Expect slow downloads: CUDA is ~4.5 GB (about 80 min on school Wi-Fi). If an `apt` process hangs on a DNS failure, kill it and clear the `dpkg` lock before retrying.

## 1. CUDA 12.6

CUDA 13 dropped Pascal (`sm_61`), so install 12.6 even if another CUDA is already present.

```bash
apt-get update && apt-get install -y cmake git build-essential wget
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/cuda-keyring_1.1-1_all.deb -O /tmp/cuda-keyring.deb
dpkg -i /tmp/cuda-keyring.deb && apt-get update
apt-get install -y cuda-toolkit-12-6
/usr/local/cuda-12.6/bin/nvcc --version
```

## 2. Build llama.cpp for `sm_61`

About 35 minutes on 2 cores. Point CMake at the 12.6 `nvcc` explicitly.

```bash
mkdir -p /opt/llama.cpp && cd /opt/llama.cpp
[ -d src ] || git clone --depth=1 https://github.com/ggml-org/llama.cpp.git src
cd src && rm -rf build
cmake -S . -B build -DGGML_CUDA=ON \
  -DCMAKE_CUDA_COMPILER=/usr/local/cuda-12.6/bin/nvcc \
  -DCUDAToolkit_ROOT=/usr/local/cuda-12.6 \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_CUDA_ARCHITECTURES=61
cmake --build build --config Release --parallel "$(nproc)"
mkdir -p /opt/llama.cpp/bin
install -m 0755 build/bin/llama-server build/bin/llama-bench /opt/llama.cpp/bin/
/opt/llama.cpp/bin/llama-server --list-devices     # every GPU should appear
```

Record the commit (`git rev-parse --short HEAD`). Rig 1 runs `972d231`. **Keep `/opt/llama.cpp/src/build`:** the installed binary's RUNPATH points into it.

## 3. Model files

Symlink Ollama's blobs instead of copying ~17 GB. Blob hashes: [hosts](../reference/hosts.md#model-files).

```bash
mkdir -p /srv/ocs-intelligence/models /var/lib/ocs-intelligence /etc/ocs-intelligence
B=/usr/share/ollama/.ollama/models/blobs
ln -sf $B/sha256-f5f1dd8920d417aac2718b0bda3403da274301efdd6760b4f0f4b864ff2ad57d /srv/ocs-intelligence/models/qwen3.8-27b-q4_k_m.gguf
ln -sf $B/sha256-c5396e06af294bd101b30dce59131a76d2b773e76950acc870eda801d3ab0515 /srv/ocs-intelligence/models/qwen2.5-0.5b.gguf
```

## 4. Workers

```bash
openssl rand -hex 24                     # the worker secret; used in 3 env files
cp infra/rig/worker-a.env.template /etc/ocs-intelligence/worker-a.env
cp infra/rig/worker-b.env.template /etc/ocs-intelligence/worker-b.env
# edit both: set WORKER_API_KEY; on a different rig, replace the GPU UUIDs (nvidia-smi -L)
chmod 0600 /etc/ocs-intelligence/worker-*.env
cp infra/rig/ocs-llama-a.service infra/rig/ocs-llama-b.service /etc/systemd/system/
systemctl daemon-reload && systemctl enable ocs-llama-a ocs-llama-b
systemctl stop ollama        # frees all VRAM; check with nvidia-smi before starting workers
systemctl start ocs-llama-a ocs-llama-b
curl -H "Authorization: Bearer $WORKER_SECRET" http://127.0.0.1:8081/health
curl -H "Authorization: Bearer $WORKER_SECRET" http://127.0.0.1:8082/health
```

Worker A can take several minutes to load (`TimeoutStartSec=600`). **Gotcha:** this llama.cpp version needs `--flash-attn on`, not a bare `--flash-attn`. The units in `infra/rig/` already have the fix.

## 5. Orchestrator

PyPI is DNS-blocked on the school network, so install the dependencies from Ubuntu and let the venv see them. Ubuntu 24.04 ships FastAPI 0.101.0, older than the `>=0.115` in `orchestrator/requirements.txt`, and it works. Don't `pip install -r` on the rig.

```bash
apt-get install -y python3-venv python3-fastapi python3-uvicorn python3-httpx
mkdir -p /opt/ocs-orchestrator /var/lib/ocs-orchestrator /etc/ocs-orchestrator
cp -r orchestrator /opt/ocs-orchestrator/
python3 -m venv --system-site-packages /opt/ocs-orchestrator/.venv
cp infra/rig/orchestrator.env.template /etc/ocs-orchestrator/orchestrator.env
# edit: WORKER_API_KEY (same secret as step 4) and PUBLIC_API_KEYS (the student key, same as EC2)
chmod 0600 /etc/ocs-orchestrator/orchestrator.env
cp infra/rig/ocs-orchestrator.service /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now ocs-orchestrator
```

## Check it worked

```bash
curl http://127.0.0.1:9000/healthz                  # {"status":"ok"}
curl http://127.0.0.1:9000/readyz                   # {"status":"ready"}
curl -H "Authorization: Bearer $STUDENT_KEY" http://127.0.0.1:9000/v1/models
curl http://127.0.0.1:9000/v1/models                # 401 without a key
```

Then send one completion per model through `:9000`, and save the output and `timings` as a new file in [`evidence/`](../../evidence/evidence.md).

## If something goes wrong

| Symptom | Likely cause | Fix |
|---|---|---|
| `nvcc fatal : Unsupported gpu architecture 'compute_61'` | Building with CUDA 13 | Use `/usr/local/cuda-12.6/bin/nvcc` explicitly |
| Worker crash-loops, log shows `--metrics` parsed as a value | Bare `--flash-attn` | Use `--flash-attn on` |
| Worker fails with out-of-memory at start | Ollama still holds VRAM | `systemctl stop ollama`, check `nvidia-smi` |
| `pip` hangs | PyPI blocked | Use the Ubuntu packages above |
| `llama-server: error while loading shared libraries` | Build dir deleted | Rebuild. The binary needs `/opt/llama.cpp/src/build/bin`. |
