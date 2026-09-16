# OCS Intelligence Inference Orchestrator Deployment Guide

## Purpose

This runbook describes how to turn the current single-path deployment into a topology-aware inference service using:

- the existing Ubuntu EC2 instance as the public TLS gateway and inference orchestrator;
- the existing seven-GPU GTX 1070 rig as two isolated inference workers, split 4 GPUs and 3 GPUs;
- Open WebUI as the user-facing interface;
- `llama-server` as the inference runtime; and
- an OpenAI-compatible API for Open WebUI and external clients.

The intended request path is:

```text
Client
  |
  | HTTPS: ai.opencodingsociety.com
  v
EC2 Nginx (TLS, request limits)
  |                         \
  | /v1/*                    \ /
  v                           v
FastAPI orchestrator       Open WebUI
  |
  | NetBird only
  +----------------------+----------------------+
  |                                             |
  v                                             v
Group A: pinned worker                    Group B: flexible worker
4 topology-selected GPUs                 3 topology-selected GPUs
default model always warm                one allow-listed model at a time
```

This is a one-rig deployment. A second rig can later be registered as additional workers without changing the public API.

## Why this design

The current issue baseline reports approximately:

| Metric | Existing result |
|---|---:|
| Prompt evaluation | 10.85 tokens/s |
| Generation | 12.50 tokens/s |
| Warm time to first token | about 2 seconds |
| Cold time to first token | about 2 minutes 27 seconds |

The current seven-GPU model split makes every request depend on all seven GPUs and their motherboard/riser paths. Two independent workers using four GPUs and three GPUs remove all inference traffic **between the two groups** and permit two requests to execute concurrently. They do not eliminate transfers **within** each group. A PCIe x1 riser remains a physical bandwidth ceiling; software cannot turn it into an x8 or x16 link.

The initial runtime must use llama.cpp's `layer` split. Row and tensor splitting exchange more data across GPUs and are poor defaults for slow riser links. The production topology will be accepted only after comparison with the existing seven-GPU baseline.

## Scope and safety rules

- Perform the audit first. Audit commands are read-only and may run while the service is live.
- Do not stop Ollama, Open WebUI, Nginx, or a model process until an announced maintenance window begins.
- Never put SSH keys, API keys, NetBird authentication tokens, public IP addresses, or passwords in this repository.
- Use NetBird DNS names or private addresses in deployed configuration, but write placeholders in committed examples.
- Back up every active configuration before changing it.
- Do not expose either `llama-server` worker to the public Internet.
- Do not enable `GGML_CUDA_P2P=1` unless the CUDA peer-to-peer tests pass for every pair in that group and a correctness soak test passes. Some motherboard/IOMMU combinations fail or corrupt output with forced P2P.
- Do not allow public callers to download arbitrary model files. The flexible worker serves an administrator-maintained preset allow-list only.

## Deployment variables

Record these values in an operator-only worksheet before making changes. Values ending in `_SECRET` belong in root-readable environment files, not in Git.

```text
EC2_NETBIRD_NAME=
EC2_NETBIRD_IP=
RIG_NETBIRD_NAME=
RIG_NETBIRD_IP=

GROUP_A_GPU_UUIDS=GPU-...,GPU-...,GPU-...,GPU-...
GROUP_B_GPU_UUIDS=GPU-...,GPU-...,GPU-...

DEFAULT_MODEL_ID=
DEFAULT_MODEL_GGUF=/srv/ocs-intelligence/models/<file>.gguf
MODELS_PRESET=/etc/ocs-intelligence/models.ini

GROUP_A_TENSOR_SPLIT=1,1,1,1
GROUP_B_TENSOR_SPLIT=1,1,1
CONTEXT_SIZE=

WORKER_API_KEY_SECRET=
PUBLIC_API_KEY_SECRET=
```

Use GPU UUIDs in `CUDA_VISIBLE_DEVICES`. CUDA indices can change after a reboot or driver update; UUIDs remain tied to the physical cards.

---

## Phase 1: Read-only discovery over SSH

Save the outputs in the deployment record with secrets and user information removed. Run all timestamps in UTC so EC2 and rig events can be correlated.

Connect using the private host names supplied by the operator and verify each host key out of band on first use:

```bash
ssh -o IdentitiesOnly=yes -i <PATH_TO_PRIVATE_KEY> ubuntu@<EC2_PRIVATE_NAME>
ssh -o IdentitiesOnly=yes -i <PATH_TO_PRIVATE_KEY> <RIG_ADMIN_USER>@<RIG_PRIVATE_NAME>
```

Do not copy the private key into the repository or include it in a shell transcript committed with the deployment record.

### 1.1 Both hosts

```bash
date -u
hostnamectl
uname -a
cat /etc/os-release
ip -brief address
netbird status
timedatectl status
systemctl --failed
sudo ss -lntup
sudo ufw status verbose
df -hT
free -h
```

Confirm time synchronization before benchmarking. Streaming timestamps from unsynchronized hosts are not comparable.

### 1.2 EC2 gateway

```bash
nginx -v
sudo nginx -T
sudo systemctl status nginx --no-pager
sudo certbot certificates
curl -fsS https://ai.opencodingsociety.com/api/version
```

Record:

- the active Nginx site and certificate paths;
- how Open WebUI is reached today;
- any existing authentication, rate limiting, or upstream health checks; and
- ports currently allowed by the EC2 security group and host firewall.

The repository snapshot shows Nginx forwarding the entire site to Open WebUI on the rig. Verify the live configuration instead of assuming the snapshot is current.

### 1.3 GPU rig: software and processes

```bash
nvidia-smi
nvidia-smi --query-gpu=index,uuid,pci.bus_id,name,driver_version,memory.total,memory.used,utilization.gpu,pstate,power.draw,power.limit --format=csv
nvcc --version
ldconfig -p | rg 'libcuda|libcudart|libnccl'
ollama --version
systemctl list-units --type=service --all | rg -i 'ollama|llama|open-webui|docker'
ps -eo pid,user,etimes,%cpu,%mem,args --sort=-%cpu | rg -i 'ollama|llama|open-webui'
docker ps --no-trunc
sudo ss -lntup
```

If `rg` is unavailable, use `grep -E` for these inspection commands.

Capture the exact current model and its immutable fingerprint:

```bash
find /srv /opt /var/lib/ollama -type f \( -name '*.gguf' -o -name '*.safetensors' \) -print 2>/dev/null
sha256sum /absolute/path/to/the/current/model.gguf
du -h /absolute/path/to/the/current/model.gguf
```

Also record the model architecture, quantization, chat template, configured context, batch size, and existing Ollama parameters. A 27B Q4 model may fit in 32 GB while the same model at Q8 plus a large KV cache may not. Admission is based on measured peak VRAM, not only model-file size.

The split design has a hard feasibility gate: the complete default model, runtime buffers, configured KV cache, and safety margin must fit within the four selected 8 GB cards without CPU offload, and every allow-listed flexible-worker model must fit within the three selected 8 GB cards. Prove each configuration with a clean load and peak-VRAM measurement before continuing. If a configuration does not fit, stop the deployment and either approve a smaller context/quantization as a separately re-baselined configuration or retain the previous topology. Do not hide a failed fit by offloading layers to system RAM; that would move the bottleneck to the same motherboard path this design is intended to avoid.

### 1.4 PCIe and NUMA topology

```bash
nvidia-smi topo -m
nvidia-smi topo -p2p r
nvidia-smi topo -p2p w
lspci -tv
lscpu --extended=CPU,NODE,SOCKET,CORE,ONLINE
numactl --hardware
```

For every GPU bus ID returned by `nvidia-smi`, inspect the negotiated link:

```bash
sudo lspci -s 03:00.0 -vv | rg 'LnkCap|LnkSta'
```

Repeat with the actual bus ID for all seven GPUs. Record both link width and speed. `LnkCap` is the device capability; `LnkSta` is the negotiated reality. A card capable of x16 but reporting `Width x1` is operating through an x1 path.

Run NVIDIA's `p2pBandwidthLatencyTest` if the CUDA samples are already installed:

```bash
find /usr/local/cuda /opt -type f -name p2pBandwidthLatencyTest -perm -111 2>/dev/null
/absolute/path/to/p2pBandwidthLatencyTest
```

If it is unavailable, build the matching CUDA sample during the maintenance preparation stage, not during the live audit:

```bash
sudo git clone --depth=1 https://github.com/NVIDIA/cuda-samples.git /opt/cuda-samples
sudo cmake \
  -S /opt/cuda-samples/cpp/5_Domain_Specific/p2pBandwidthLatencyTest \
  -B /opt/cuda-samples/cpp/5_Domain_Specific/p2pBandwidthLatencyTest/build \
  -DCMAKE_CUDA_ARCHITECTURES=61
sudo cmake --build \
  /opt/cuda-samples/cpp/5_Domain_Specific/p2pBandwidthLatencyTest/build \
  --parallel
/opt/cuda-samples/cpp/5_Domain_Specific/p2pBandwidthLatencyTest/build/p2pBandwidthLatencyTest
```

### 1.5 Select the four-GPU and three-GPU groups

Do not automatically choose indices `0,1,2,3` and `4,5,6,7`.

1. Prefer GPUs sharing the closest PCIe switch/root complex.
2. Maximize measured within-group peer bandwidth and minimize within-group latency.
3. Avoid placing a group across CPU sockets or NUMA nodes when a same-node partition exists.
4. Assign the four most suitable cards to Group A and the remaining three to Group B, balancing GPU health, temperature, VRAM, and compute capability.
5. If all links traverse the same root complex, choose the partition with the best measured four-card and three-card concurrency and document the shared bottleneck.

Record the result by UUID:

| Group | GPU UUID | PCI bus ID | NUMA node | Negotiated link | P2P result |
|---|---|---|---:|---|---|
| A | | | | | |
| A | | | | | |
| A | | | | | |
| A | | | | | |
| B | | | | | |
| B | | | | | |
| B | | | | | |

---

## Phase 2: Establish a reproducible baseline

Run baseline tests before replacing Ollama. Use a fixed prompt corpus containing short, medium, and long prompts. Pin the model, quantization, context size, sampling parameters, output-token count, and random seed.

For the existing Ollama setup, retain the issue's warm command as one comparable case:

```bash
ollama run <CURRENT_MODEL> 'Write a short summary of how photosynthesis works.' --verbose
```

Collect at least 30 warm requests at concurrency 1, then tests at concurrency 2 and 4. Perform one explicitly labeled cold-start test. Record:

- model load duration;
- queue duration;
- p50 and p95 time to first token;
- p50 and p95 inter-token latency;
- prompt and generation tokens per second;
- requests and tokens per second at each concurrency;
- request failures and cancellations;
- CPU and RAM usage; and
- per-GPU utilization, VRAM, power, temperature, and PCIe receive/transmit throughput.

Capture GPU telemetry during each test:

```bash
nvidia-smi dmon -s pucvmet -d 1 -o DT
```

Save the current service arguments and model hash beside the results. Results from a different quantization or context size are not a valid comparison.

---

## Phase 3: Install and verify llama.cpp

Build a pinned llama.cpp revision with CUDA. Record the Git commit in the deployment record so a later update is an explicit rollout, not an accidental rebuild.

```bash
sudo install -d -o root -g root /opt/llama.cpp
sudo git clone https://github.com/ggml-org/llama.cpp.git /opt/llama.cpp/src
cd /opt/llama.cpp/src
sudo git checkout <REVIEWED_COMMIT>
sudo cmake -S . -B build -DGGML_CUDA=ON -DGGML_CUDA_NCCL=ON -DCMAKE_BUILD_TYPE=Release
sudo cmake --build build --config Release --parallel
sudo install -m 0755 build/bin/llama-server /opt/llama.cpp/bin/llama-server
sudo install -m 0755 build/bin/llama-bench /opt/llama.cpp/bin/llama-bench
/opt/llama.cpp/bin/llama-server --version
/opt/llama.cpp/bin/llama-server --list-devices
```

Inspect the CMake output. If NCCL is absent, record it. NCCL primarily affects tensor-mode reductions; production still starts with layer mode.

Create service directories:

```bash
sudo install -d -o root -g root -m 0755 /etc/ocs-intelligence
sudo install -d -o root -g root -m 0755 /srv/ocs-intelligence/models
sudo install -d -o root -g root -m 0755 /var/lib/ocs-intelligence
```

Copy or link only reviewed GGUF files into `/srv/ocs-intelligence/models`. Verify their hashes after the move.

---

## Phase 4: Configure the two rig workers

Start with one inference slot per group. A second slot allocates more KV cache and can cause an otherwise fitting model to OOM. Increase parallelism only after VRAM and throughput testing.

### 4.1 Group A: permanently warm default model

Create `/etc/ocs-intelligence/worker-a.env` on the rig:

```ini
CUDA_VISIBLE_DEVICES=GPU-AAAA,GPU-BBBB,GPU-CCCC,GPU-DDDD
CUDA_SCALE_LAUNCH_QUEUES=4x
RIG_NETBIRD_IP=<RIG_NETBIRD_IP>
DEFAULT_MODEL_GGUF=/srv/ocs-intelligence/models/<default-model>.gguf
DEFAULT_MODEL_ID=<stable-public-model-id>
CONTEXT_SIZE=<validated-context-size>
TENSOR_SPLIT=1,1,1,1
WORKER_API_KEY=<random-worker-only-secret>
```

Protect it:

```bash
sudo chown root:root /etc/ocs-intelligence/worker-a.env
sudo chmod 0600 /etc/ocs-intelligence/worker-a.env
```

Create `/etc/systemd/system/ocs-llama-a.service`:

```ini
[Unit]
Description=OCS llama.cpp pinned worker A
After=network-online.target netbird.service
Wants=network-online.target

[Service]
Type=simple
EnvironmentFile=/etc/ocs-intelligence/worker-a.env
UnsetEnvironment=GGML_CUDA_P2P
ExecStart=/opt/llama.cpp/bin/llama-server \
  --host ${RIG_NETBIRD_IP} \
  --port 8081 \
  --model ${DEFAULT_MODEL_GGUF} \
  --alias ${DEFAULT_MODEL_ID} \
  --api-key ${WORKER_API_KEY} \
  --n-gpu-layers all \
  --split-mode layer \
  --tensor-split ${TENSOR_SPLIT} \
  --ctx-size ${CONTEXT_SIZE} \
  --parallel 1 \
  --cont-batching \
  --flash-attn auto \
  --metrics \
  --slots \
  --warmup
Restart=on-failure
RestartSec=5
TimeoutStartSec=600
TimeoutStopSec=90
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadOnlyPaths=/srv/ocs-intelligence/models
ReadWritePaths=/var/lib/ocs-intelligence
LimitNOFILE=1048576

[Install]
WantedBy=multi-user.target
```

Do not configure sleep-on-idle for Group A. Its purpose is to remove the reported cold start from the default-model path.

### 4.2 Group B: flexible allow-listed worker

Create `/etc/ocs-intelligence/worker-b.env` with the second four UUIDs, port-independent shared settings, and the same private worker key:

```ini
CUDA_VISIBLE_DEVICES=GPU-EEEE,GPU-FFFF,GPU-GGGG
CUDA_SCALE_LAUNCH_QUEUES=4x
RIG_NETBIRD_IP=<RIG_NETBIRD_IP>
MODELS_PRESET=/etc/ocs-intelligence/models.ini
WORKER_API_KEY=<same-random-worker-only-secret>
```

Create `/etc/ocs-intelligence/models.ini`. Only models proven to fit the three Group B GPUs may be listed:

```ini
version = 1

[*]
n-gpu-layers = all
split-mode = layer
tensor-split = 1,1,1
ctx-size = <validated-context-size>
parallel = 1
cont-batching = true
flash-attn = auto
jinja = true
stop-timeout = 90

[<default-model-id>]
model = /srv/ocs-intelligence/models/<default-model>.gguf
load-on-startup = false

[<alternate-model-id>]
model = /srv/ocs-intelligence/models/<alternate-model>.gguf
ctx-size = <validated-context-size-for-this-model>
load-on-startup = false
```

Create `/etc/systemd/system/ocs-llama-b.service`:

```ini
[Unit]
Description=OCS llama.cpp flexible worker B
After=network-online.target netbird.service
Wants=network-online.target

[Service]
Type=simple
EnvironmentFile=/etc/ocs-intelligence/worker-b.env
UnsetEnvironment=GGML_CUDA_P2P
ExecStart=/opt/llama.cpp/bin/llama-server \
  --host ${RIG_NETBIRD_IP} \
  --port 8082 \
  --api-key ${WORKER_API_KEY} \
  --models-preset ${MODELS_PRESET} \
  --models-max 1 \
  --models-autoload \
  --metrics \
  --slots
Restart=on-failure
RestartSec=5
TimeoutStartSec=600
TimeoutStopSec=90
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadOnlyPaths=/srv/ocs-intelligence/models /etc/ocs-intelligence/models.ini
ReadWritePaths=/var/lib/ocs-intelligence
LimitNOFILE=1048576

[Install]
WantedBy=multi-user.target
```

Protect both Group B files:

```bash
sudo chown root:root /etc/ocs-intelligence/worker-b.env /etc/ocs-intelligence/models.ini
sudo chmod 0600 /etc/ocs-intelligence/worker-b.env
sudo chmod 0644 /etc/ocs-intelligence/models.ini
```

### 4.3 Start and validate workers

The old all-GPU Ollama process must be drained and stopped before either worker starts. Do this only inside the maintenance window.

```bash
sudo systemctl daemon-reload
sudo systemctl enable ocs-llama-a.service ocs-llama-b.service
sudo systemctl start ocs-llama-a.service
sudo journalctl -u ocs-llama-a.service -f
```

In another session, confirm exactly four intended UUIDs have allocations and Group A is healthy:

```bash
nvidia-smi --query-compute-apps=gpu_uuid,pid,used_memory --format=csv
curl -fsS -H 'Authorization: Bearer <WORKER_API_KEY>' \
  http://<RIG_NETBIRD_IP>:8081/health
curl -fsS -H 'Authorization: Bearer <WORKER_API_KEY>' \
  http://<RIG_NETBIRD_IP>:8081/v1/models
```

Run the fixed prompt corpus against Group A. Only after it passes should Group B start:

```bash
sudo systemctl start ocs-llama-b.service
curl -fsS -H 'Authorization: Bearer <WORKER_API_KEY>' \
  http://<RIG_NETBIRD_IP>:8082/health
curl -fsS -H 'Authorization: Bearer <WORKER_API_KEY>' \
  http://<RIG_NETBIRD_IP>:8082/models
```

Confirm the two processes have disjoint UUID sets. Stop deployment if either process sees or allocates memory on a GPU assigned to the other group.

---

## Phase 5: EC2 orchestrator contract

Install the orchestrator under `/opt/ocs-orchestrator` in its own Python virtual environment and run it as an unprivileged `ocs-orchestrator` system user. Bind it to `127.0.0.1:9000` for public Nginx traffic. If Open WebUI connects through the EC2 NetBird address, additionally bind through a firewall-restricted private listener or have Nginx expose a NetBird-only internal server block.

### 5.1 Public API

The orchestrator exposes:

| Route | Behavior |
|---|---|
| `GET /healthz` | Process liveness only; never claims workers are healthy |
| `GET /readyz` | Ready only when Group A is healthy with the default model loaded |
| `GET /v1/models` | Merged allow-list with availability/residency metadata removed from the OpenAI response |
| `POST /v1/chat/completions` | OpenAI-compatible blocking or SSE-streaming completion |
| `POST /v1/responses` | OpenAI-compatible Responses API pass-through |
| `GET /metrics` | Prometheus metrics; localhost/private access only |

All `/v1/*` calls require `Authorization: Bearer <PUBLIC_API_KEY>`. The orchestrator replaces that credential with the private worker credential when calling the rig. It must never log either header.

### 5.2 Worker registry

Use an environment file at `/etc/ocs-orchestrator/orchestrator.env`, owned by root with mode `0600`:

```ini
GROUP_A_URL=http://<RIG_NETBIRD_IP>:8081
GROUP_B_URL=http://<RIG_NETBIRD_IP>:8082
DEFAULT_MODEL_ID=<stable-public-model-id>
WORKER_API_KEY=<private-worker-secret>
PUBLIC_API_KEYS=<comma-separated-public-keys>
QUEUE_CAPACITY_PER_WORKER=16
CONNECT_TIMEOUT_SECONDS=5
RESPONSE_HEADER_TIMEOUT_SECONDS=600
STREAM_IDLE_TIMEOUT_SECONDS=300
HEALTH_INTERVAL_SECONDS=5
MODEL_LOAD_TIMEOUT_SECONDS=600
```

Do not place this file in the repository.

### 5.3 Deterministic scheduling policy

Each worker has a state machine:

```text
UNHEALTHY -> STARTING -> IDLE(model or empty) -> LOADING(model)
                                      |              |
                                      v              v
                                  BUSY(model) <------+
```

Scheduling rules, in order:

1. Reject an unknown model with HTTP 404. Model names come only from the reviewed preset allow-list.
2. Route the default model to Group A.
3. If Group A is busy and Group B is healthy, idle, and already holds the default model, use Group B for overflow.
4. Do not evict another model from Group B merely to service default-model overflow; queue that request for Group A.
5. Route a non-default model to Group B.
6. If Group B is idle with a different model, unload it, wait for `unloaded`, load the requested model, wait for `loaded`, perform a one-token warm-up, and then release queued requests for that model.
7. If Group B is busy, queue the request. Never unload a model that has an active request.
8. Use FIFO ordering within each worker, with cancellation removing jobs that have not started.
9. If a queue reaches 16 entries, return HTTP 429 with `Retry-After`; do not create an unbounded backlog.
10. Return HTTP 503 when no eligible worker is healthy or a model load fails, and HTTP 504 on the configured load/header timeout.

The queue is intentionally in-memory. Streaming inference cannot resume after an orchestrator restart, so pretending the request is durable provides no benefit. On restart, clients receive a closed connection and retry explicitly.

### 5.4 Streaming and cancellation

- Stream worker SSE bytes without buffering or accumulating the full answer in EC2 memory.
- Stop reading and close the upstream HTTP stream immediately when the client disconnects.
- Do not retry automatically after the worker begins generation; a retry can produce a different answer and duplicate compute.
- Forward status codes and OpenAI-formatted error bodies before streaming begins.
- Strip hop-by-hop headers and never forward the public API key to a worker.
- Keep one shared asynchronous HTTP client and connection pool per worker.

### 5.5 Metrics and logs

Expose counters/histograms for:

- requests by route, model, worker, and outcome;
- queue depth and queue seconds;
- time to first token and total response seconds;
- prompt and generated tokens;
- worker health and current resident model;
- model load count, duration, and failures;
- active streams and client cancellations; and
- HTTP 429, 503, and 504 responses.

Use request IDs in Nginx, orchestrator, and worker logs. Never log prompts, generated text, authorization headers, or full request bodies by default.

### 5.6 systemd service

Create `/etc/systemd/system/ocs-orchestrator.service`:

```ini
[Unit]
Description=OCS inference orchestrator
After=network-online.target netbird.service
Wants=network-online.target

[Service]
Type=simple
User=ocs-orchestrator
Group=ocs-orchestrator
WorkingDirectory=/opt/ocs-orchestrator
EnvironmentFile=/etc/ocs-orchestrator/orchestrator.env
ExecStart=/opt/ocs-orchestrator/.venv/bin/uvicorn orchestrator.main:app \
  --host 127.0.0.1 --port 9000 --workers 1 --proxy-headers
Restart=on-failure
RestartSec=3
TimeoutStopSec=30
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/ocs-orchestrator
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```

Use one Uvicorn process because queue and worker state are in memory. Horizontal orchestrator replicas require a shared coordinator and are outside this one-EC2 design.

---

## Phase 6: Network controls and Nginx

### 6.1 Rig firewall

Allow worker ports only from the EC2 NetBird address. Adapt commands to the firewall already in use; do not introduce a second firewall manager.

For UFW:

```bash
sudo ufw allow in on wt0 from <EC2_NETBIRD_IP> to any port 8081 proto tcp
sudo ufw allow in on wt0 from <EC2_NETBIRD_IP> to any port 8082 proto tcp
sudo ufw deny 8081/tcp
sudo ufw deny 8082/tcp
sudo ufw status numbered
```

Verify from an unauthorized host that both ports are unreachable. Do not open them in a router, cloud firewall, or public security group.

### 6.2 EC2 Nginx route

Keep the existing `/` location pointed at Open WebUI. Add the API route before it:

```nginx
location /v1/ {
    proxy_pass http://127.0.0.1:9000;
    proxy_http_version 1.1;

    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Request-ID $request_id;

    proxy_set_header Connection "";
    proxy_buffering off;
    proxy_request_buffering off;
    proxy_cache off;

    proxy_connect_timeout 5s;
    proxy_read_timeout 3600s;
    proxy_send_timeout 3600s;

    client_max_body_size 2m;
}

location = /healthz {
    proxy_pass http://127.0.0.1:9000/healthz;
    access_log off;
}

location / {
    proxy_pass http://<RIG_NETBIRD_IP>:3000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection $connection_upgrade;
    proxy_buffering off;
    proxy_read_timeout 300s;
}
```

Do not expose `/metrics`, the worker model-control routes, or worker `/slots` through public Nginx.

Validate before reload:

```bash
sudo nginx -t
sudo systemctl reload nginx
sudo systemctl status nginx --no-pager
```

### 6.3 Open WebUI connection

In Open WebUI's administrator connection settings:

1. Add an OpenAI-compatible connection whose base URL is the EC2 orchestrator `/v1` endpoint.
2. Store a dedicated public API key in Open WebUI's secret/configuration store.
3. Confirm `/v1/models`, normal chat, streaming chat, cancellation, and tool-call formatting.
4. Make the orchestrated connection the default.
5. Disable the old direct Ollama connection only after validation.

Keep a copy of the previous Open WebUI connection settings for rollback.

---

## Phase 7: Validation and acceptance

### 7.1 Functional tests

Test directly through the public gateway:

```bash
curl -fsS https://ai.opencodingsociety.com/v1/models \
  -H 'Authorization: Bearer <PUBLIC_API_KEY>'

curl -N https://ai.opencodingsociety.com/v1/chat/completions \
  -H 'Authorization: Bearer <PUBLIC_API_KEY>' \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "<DEFAULT_MODEL_ID>",
    "stream": true,
    "messages": [{"role": "user", "content": "Write a short summary of how photosynthesis works."}],
    "temperature": 0,
    "max_tokens": 291
  }'
```

Verify:

- invalid/missing keys return 401;
- unknown models return 404;
- a saturated queue returns 429 with `Retry-After`;
- Group A serves the default model without loading it per request;
- Group B never evicts an active model;
- Group B loads an alternate allow-listed model and reports progress correctly;
- client cancellation frees the worker slot;
- worker loss produces 503 rather than a hanging stream; and
- EC2 restart produces a clean service recovery without claiming readiness before Group A is ready.

### 7.2 Performance matrix

Run the same corpus and parameters for every row:

| Configuration | Concurrency | Runs | Required comparison |
|---|---:|---:|---|
| Existing Ollama across seven GPUs | 1, 2, 4 | 30 each | Baseline |
| Group A only | 1 | 30 | Decode rate no worse than 95% of baseline |
| Group B only, default resident | 1 | 30 | Decode rate no worse than 95% of baseline |
| Groups A and B concurrently | 2, 4 | 30 each | At least 1.6x baseline aggregate throughput |
| Group B cold alternate load | 1 | 5 | Record load and first-token delay separately |
| Public path through EC2 | 1, 2, 4 | 30 each | Quantify gateway/queue overhead |

The pinned default model must meet all of these:

- p95 warm TTFT below 3 seconds for the standard short prompt;
- zero steady-state cold loads;
- identical model hash and sampling configuration to the baseline;
- no material response-quality or formatting regression;
- no GPU OOM, process restart, or corrupted output during the soak test; and
- correct isolation to its assigned four UUIDs.

Run a minimum two-hour mixed-concurrency soak test, including cancellations and alternate-model requests. Inspect:

```bash
sudo journalctl -u ocs-orchestrator.service --since '2 hours ago'
sudo journalctl -u ocs-llama-a.service --since '2 hours ago'
sudo journalctl -u ocs-llama-b.service --since '2 hours ago'
nvidia-smi --query-gpu=uuid,temperature.gpu,power.draw,memory.used,utilization.gpu --format=csv
```

### 7.3 Tensor-split tuning

Begin with `1,1,1,1` because the cards are nominally identical. If telemetry shows a persistent imbalance, benchmark small layer allocations that give fewer layers to a demonstrably slower card/link. Change one variable at a time and retain a split only when the full request matrix improves. Do not tune from instantaneous GPU utilization alone.

### 7.4 Speculative decoding experiment

Speculative decoding is a second-stage experiment, not part of the initial cutover.

1. Establish the accepted non-speculative Group A 4-GPU and Group B 3-GPU results.
2. Select a compatible draft model and record its additional VRAM/CPU cost.
3. Run the identical corpus and concurrency matrix.
4. Record proposed, accepted, and rejected draft tokens from llama.cpp metrics.
5. Retain the feature only if end-to-end performance improves by at least 10%, output checks pass, and p95 TTFT/ITL do not regress.

The aspirational 60 tokens/s figure from the issue is not a release requirement. The production decision is based on repeatable improvement over the measured 12.50 tokens/s baseline.

### 7.5 Hardware decision gate

Stop software tuning and recommend a hardware change when all are true:

- the four-GPU and three-GPU layer splits and balanced model placement have been tested;
- GPU compute remains underutilized while PCIe links remain saturated;
- negotiated widths are x1 or peer bandwidth remains materially below the cards' useful transfer rate; and
- moving GPUs among available slots does not improve the result.

Evaluate hardware changes in this order:

1. reseat and validate risers, cables, power, and BIOS PCIe generation;
2. move the four-card and three-card groups onto the best available root complexes/slots;
3. replace x1 USB-style risers with direct-lane cabling where the motherboard exposes lanes;
4. use a suitable PCIe switch/backplane; or
5. replace the mining-style motherboard/platform with one providing sufficient CPU PCIe lanes.

GTX 1070 cards do not provide an NVLink path, so NVLink is not an available fix for this rig.

---

## Phase 8: Cutover procedure

1. Announce the maintenance window and stop admission of new chats.
2. Wait for current generations to finish; do not terminate active student requests.
3. Back up Nginx, Open WebUI settings/data, Ollama service overrides, model configuration, and firewall rules.
4. Record the running service state and active model hash.
5. Stop the old all-GPU Ollama inference process.
6. Start Group A and complete its functional and isolation tests.
7. Start Group B and complete its dynamic-load and isolation tests.
8. Start the EC2 orchestrator and verify `/healthz`, `/readyz`, and a private completion.
9. Add the Nginx `/v1/` location, run `nginx -t`, and reload Nginx.
10. Add and test the orchestrated OpenAI connection in Open WebUI.
11. Run public streaming, concurrency, cancellation, and error-path smoke tests.
12. Reopen traffic while watching queue depth, TTFT, failures, temperatures, and VRAM.
13. Keep the old Ollama configuration intact but stopped through the soak period.

Suggested backup pattern on each host:

```bash
deploy_stamp=$(date -u +%Y%m%dT%H%M%SZ)
sudo install -d -m 0700 "/var/backups/ocs-intelligence/${deploy_stamp}"
sudo cp -a /etc/nginx "/var/backups/ocs-intelligence/${deploy_stamp}/" 2>/dev/null || true
sudo systemctl cat ollama 2>/dev/null \
  | sudo tee "/var/backups/ocs-intelligence/${deploy_stamp}/ollama-service.txt" >/dev/null || true
```

Back up Open WebUI according to its actual deployment method: named Docker volume, bind-mounted data directory, or systemd-managed path. Verify the backup exists before proceeding.

---

## Failure behavior

| Failure | Required behavior |
|---|---|
| Group A crashes | Mark unhealthy immediately; use Group B only if the default model is already resident, otherwise return/queue according to the documented policy |
| Group B crashes during a non-default request | Terminate the stream, report failure, restart via systemd, and do not silently replay generation |
| GPU OOM | Mark the model/config unhealthy, preserve logs, reject new requests, and reduce context/parallelism before retrying |
| Flexible model load fails | Keep Group A untouched, return 503 for that model, and expose a sanitized error/request ID |
| Group B is occupied | Queue without eviction; return 429 when the bounded queue is full |
| Client disconnects | Cancel queued work or close the active upstream stream immediately |
| EC2 restarts | Uvicorn/Nginx restart through systemd; in-flight requests fail visibly; readiness waits for Group A |
| Rig is unavailable | `/readyz` fails and inference returns 503; Open WebUI itself may remain reachable |
| NetBird link fails | Treat both workers as unhealthy; never fall back to a public worker port |

---

## Rollback

Rollback if acceptance thresholds fail, errors rise materially, output is corrupted, GPU isolation fails, or the system cannot complete the soak test.

1. Stop admitting new requests and drain active orchestrated streams.
2. Restore Open WebUI's previous direct Ollama connection.
3. Restore the saved Nginx site, validate it, and reload Nginx.
4. Stop and disable the two llama.cpp workers and EC2 orchestrator.
5. Start the previous Ollama service/configuration.
6. Confirm the original model loads across the expected GPUs.
7. Test the public Open WebUI path and one warm completion.
8. Record the rollback reason and retain orchestrator/worker logs for analysis.

Representative commands, after checking the exact saved paths:

```bash
# EC2
sudo systemctl stop ocs-orchestrator.service
sudo cp -a /var/backups/ocs-intelligence/<STAMP>/nginx/. /etc/nginx/
sudo nginx -t
sudo systemctl reload nginx

# Rig
sudo systemctl stop ocs-llama-a.service ocs-llama-b.service
sudo systemctl start ollama.service
sudo systemctl status ollama.service --no-pager
```

Do not delete the new model files, services, or benchmark records during rollback. A rollback restores service; cleanup is a separate reviewed change.

---

## Adding a second rig later

A second rig should use the same worker contract: stable worker ID, NetBird-only URL, health endpoint, model list/status, slot status, and OpenAI-compatible inference routes. Add its topology-selected groups to the orchestrator registry and extend scheduling by model residency, health, queue depth, and measured capacity. Do not shard a single request across rigs over NetBird; route complete requests to one worker.

## Definition of done

- GPU groups are justified by saved topology and bandwidth evidence.
- Each worker allocates memory on exactly its four assigned GPU UUIDs.
- Group A survives idle periods without unloading the default model.
- Group B changes only between allow-listed models and never evicts an active model.
- Public OpenAI-compatible blocking and streaming requests work through EC2.
- Open WebUI uses the orchestrated endpoint successfully.
- Authentication, firewall isolation, bounded queues, cancellation, and failure responses pass.
- Group A and Group B each retain at least 95% of baseline single-request decode speed.
- Concurrent groups achieve at least 1.6x the baseline aggregate throughput.
- The default short-prompt p95 warm TTFT is below 3 seconds.
- The two-hour soak test completes without OOM, corrupted output, or service restart.
- Backups and the tested rollback procedure are available.

## References

- [Repository issue #1: hardware allocation and serving architecture](https://github.com/Open-Coding-Society/OCS-Intelligence/issues/1)
- [Repository issue #4: TPS, TTFT, cold-start, and inter-GPU bottlenecks](https://github.com/Open-Coding-Society/OCS-Intelligence/issues/4)
- [Repository issue #5: client deployment direction](https://github.com/Open-Coding-Society/OCS-Intelligence/issues/5)
- [Repository issue #18: riser and motherboard work](https://github.com/Open-Coding-Society/OCS-Intelligence/issues/18)
- [llama.cpp multi-GPU documentation](https://github.com/ggml-org/llama.cpp/blob/master/docs/multi-gpu.md)
- [llama.cpp server and model-router documentation](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)
- [NVIDIA CUDA samples](https://github.com/NVIDIA/cuda-samples)
