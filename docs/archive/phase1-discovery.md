# Phase 1 Discovery Record

Status: Phase 1 discovery complete. Deployment is stopped pending hardware
remediation/approval and host-key fingerprint verification.

Audit date: 2026-09-16 (UTC)

## Access path

- NetBird container: `netbird-dev`
- NetBird management and signal: connected
- NetBird client: `0.78.2`
- Local NetBird peer: `adi-wsl-32-108.netbird.cloud`
- NetBird reports 6 peers and 0 connected peers at the time of discovery; both target SSH ports were reachable from the NetBird network namespace.

Retry: 2026-09-16 UTC

- NetBird management and signal remained connected.
- Both target peers were connected: the EC2 peer was P2P and the rig peer was relayed.
- Both target SSH ports remained reachable.

## Target peers identified

| Role | NetBird name | NetBird address | SSH port |
|---|---|---|---|
| EC2 gateway | `ip-172-31-42-43.netbird.cloud` | `100.75.172.167` | reachable |
| GPU rig | `ocs-intelligence-rig.netbird.cloud` | `100.75.123.203` | reachable |

## SSH status

- The local SSH identities were probed through the NetBird network namespace without persisting host keys.
- Authentication was rejected for the tested accounts; no remote audit commands were run.
- No SSH host keys or operator-provided fingerprints were present in the local SSH known-hosts file.

The retry used the two already-known local identities (`id_ed25519` and
`google_compute_engine`) with these bounded account checks:

- EC2: `ubuntu`
- Rig: `ubuntu`, `adikatre`, `aditya`, and `ec2-user`

All checks returned `Permission denied (password)`. No host keys were accepted
or persisted, and no remote audit commands were run.

## Initially pending evidence

The following evidence was pending during the initial access block and is
updated below after authenticated root discovery:

- host OS, kernel, time synchronization, failed services, listeners, firewall, storage, and memory;
- EC2 Nginx, Certbot, Open WebUI, and public endpoint state;
- rig GPU, CUDA, Ollama, model, process, and listener state;
- PCIe, NUMA, topology, P2P, and negotiated-link measurements; and
- the UUID-based four-GPU group selection.

## Resume requirements

Provide, through the operator’s normal secure channel, the expected SSH
host-key fingerprints for both hosts, verified out of band. The working
NetBird SSH account is `root` on both hosts.

No services, firewall rules, model files, or repository deployment configuration were changed.

## Verified EC2 gateway audit

Audit completed at `2026-09-16 23:57:46 UTC` through NetBird SSH.

- Host: `ip-172-31-42-43`; Ubuntu 24.04 LTS on an Amazon EC2 `m5.large`; kernel `6.14.0-1018-aws`.
- Clock: synchronized; NTP active; host timezone UTC.
- NetBird: client/daemon `0.78.1`; management and signal connected; NetBird SSH enabled.
- Tailscale: not installed.
- Nginx: `1.24.0`, active and enabled; configuration syntax test passed.
- Active public listeners: TCP 80 and 443 on Nginx; TCP 22 on OpenSSH.
- UFW: inactive.
- Failed units: `kasm.service` and `snap.certbot.renew.service`.
- Root filesystem: 48G total, 46G used, 1.6G available (97%). Swap is absent. Memory available was 6.5 GiB of 7.6 GiB.
- The active `ai.opencodingsociety.com` server proxies the entire site to `http://100.75.123.203:3000`; no `/v1/` orchestrator route exists yet.
- Nginx also has active default and Kasm virtual hosts.
- The `ai.opencodingsociety.com` certificate is valid through `2026-12-09`. Two Kasm certificates reported expired and should not be disturbed during this phase.
- Public endpoint check succeeded: `/api/version` returned version `0.11.3`.

The full raw Nginx configuration was inspected but is not copied into this
repository because it contains live host and certificate configuration.

## Rig retry status

The rig peer is reachable on TCP 22, but its NetBird SSH authentication did
not complete on the first retry because the JWT request timed out. A fresh
cache-bypassed SSO authorization then succeeded, but the requested `ubuntu`
login was rejected by the rig with `User authentication failed`. Its port-22
banner identifies `NetBird-SSH-Server-0.78.1`. No rig audit command ran. GPU,
model, process, PCIe, NUMA, P2P, and topology evidence therefore remain
uncollected.

The exact authorized rig login username is now confirmed as `root`.

## Verified GPU-rig audit

Audit completed at `2026-09-17 00:07:18 UTC` through root NetBird SSH.

- Host: `ocs-intelligence-rig`; Ubuntu 24.04.4 LTS; kernel `7.0.0-31-generic`.
- Hardware: ASUSTeK `B250 MINING EXPERT`; one NUMA node (node 0); two online CPUs.
- Clock: synchronized; NTP active; local timezone America/Los_Angeles.
- NetBird: client/daemon `0.78.1`; management and signal connected; NetBird SSH enabled.
- Tailscale: not installed.
- Failed units: none.
- UFW: inactive.
- Root filesystem: 228G total, 54G used, 163G available (25%). Memory available was 13 GiB of 15 GiB; 4 GiB swap was unused.
- Active listeners include TCP 22, TCP 3000 for Open WebUI on all interfaces, and TCP 11434 for Ollama on all interfaces. Ollama also has `OLLAMA_ORIGINS=*`.
- Docker is active; the `open-webui` container is healthy and publishes host port 3000 to container port 8080.
- Ollama service is active and enabled; Ollama version `0.33.1`; no model was loaded during discovery.
- CUDA driver: `580.173.02` with reported CUDA version `13.0`. `nvcc` was not installed and `libnccl` was not present in `ldconfig`; only CUDA driver libraries were found.

### GPU inventory and links

Seven GTX 1070s were visible, not the eight GPUs assumed by the deployment
guide. All cards have 8192 MiB VRAM, were idle at 25–28 C and 13–15 W, and
had only the Xorg allocation of approximately 4 MiB.

| Index | GPU UUID | PCI bus | NUMA | Negotiated link | P2P read/write |
|---:|---|---|---:|---|---|
| 0 | `GPU-24899ea8-3258-0dd0-5aa4-6ef9104cdc68` | `03:00.0` | 0 | 2.5 GT/s, x1 (capability 5 GT/s, x16) | CNS / CNS |
| 1 | `GPU-728d79b7-b5ed-e1ec-cf29-0572f97956ba` | `08:00.0` | 0 | 2.5 GT/s, x1 (capability 5 GT/s, x16) | CNS / CNS |
| 2 | `GPU-fb4eb983-84aa-664f-b97d-94b12caffb37` | `0A:00.0` | 0 | 2.5 GT/s, x1 (capability 2.5 GT/s, x16) | CNS / CNS |
| 3 | `GPU-71f15481-4db3-9d2a-8d30-6e68dba08617` | `0B:00.0` | 0 | 2.5 GT/s, x1 (capability 2.5 GT/s, x16) | CNS / CNS |
| 4 | `GPU-bc07dc85-473b-9927-538e-986f80b80486` | `0C:00.0` | 0 | 2.5 GT/s, x1 (capability 2.5 GT/s, x16) | CNS / CNS |
| 5 | `GPU-2a70bbf9-ed03-162f-ddd5-c7ed42149d84` | `0E:00.0` | 0 | 2.5 GT/s, x1 (capability 2.5 GT/s, x16) | CNS / CNS |
| 6 | `GPU-a25606af-913d-22d1-5ebe-ecea656819cb` | `0F:00.0` | 0 | 2.5 GT/s, x1 (capability 2.5 GT/s, x16) | CNS / CNS |

`nvidia-smi topo -m` reports only GPU 0/1 as `PIX`; every other GPU pair
is `PHB`. `nvidia-smi topo -p2p r` and `-p2p w` report `CNS` for every
non-self pair. NVIDIA’s `p2pBandwidthLatencyTest` binary was not installed.

No two four-GPU groups can be selected from seven visible cards. The guide’s
two-group deployment therefore fails its inventory gate before any model
load, P2P enablement, or worker configuration is attempted.

### Existing model and runtime metadata

- Ollama model: `qwen3.8:27b` and `qwen3.8:latest` point to the same model ID.
- Architecture: `qwen35`; 27.3B parameters; model context capability 262,144 tokens.
- Quantization: `Q4_K_M`; model blob size 16,810,714,464 bytes (about 16.81 GB).
- Projector: CLIP; 460.73M parameters; projector blob size 931,146,016 bytes (about 0.93 GB).
- Capabilities: completion, vision, tools, and thinking.
- Modelfile renderer/parser: `qwen3.8` / `qwen3.5`; template is `{{ .Prompt }}`.
- Sampling parameters: temperature 1, top-k 20, top-p 0.95, repeat penalty 1, min-p 0, presence penalty 0, draft token count 4.
- No explicit context-size or batch-size setting was present in the Ollama service. The model was unloaded, so the effective request context and batch behavior remain unmeasured.
- Model manifest SHA-256: `22130167c4c20e20c7b71454612966ca8e8171e9b3cc8ab6ce8aa6cbfec79643`.
- Model blob digest: `sha256:f5f1dd8920d417aac2718b0bda3403da274301efdd6760b4f0f4b864ff2ad57d`.
- Projector blob digest: `sha256:ac3714bfdddeca31351f2752bf1a63f266f4df87c0b68c895e44945ca704448e`.
- Ollama stores the model under `/usr/share/ollama/.ollama/models`; no standalone `.gguf` file was found in the runbook’s `/srv`, `/opt`, or `/var/lib/ollama` search paths.

The exact context/batch configuration and peak VRAM were intentionally not
benchmarked in Phase 1. They belong to the later baseline/clean-load gates,
which must not proceed until the seven-versus-eight GPU inventory discrepancy
is resolved or the topology is separately redesigned and approved.
