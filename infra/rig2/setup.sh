#!/usr/bin/env bash
# Set up Rig 2: one llama.cpp worker serving qwen3.8:27b across every GPU on 127.0.0.1:8081.
#
#   git pull && sudo ./infra/rig2/setup.sh
#
# Safe to re-run: each step skips itself if already done. An existing
# /etc/ocs-intelligence/worker.env keeps its WORKER_API_KEY.
#
# Overrides (env vars):
#   MODEL=qwen3.8:27b       Ollama model to pull
#   CONTEXT_SIZE=262144     llama-server --ctx-size; lower it if the worker runs out of VRAM
#   LLAMA_CPP_REF=<sha>     llama.cpp commit to build (default: latest master; Rig 1 runs 972d231)
#   REBUILD=1               rebuild llama.cpp even if the binary exists

set -euo pipefail

MODEL="${MODEL:-qwen3.8:27b}"
CONTEXT_SIZE="${CONTEXT_SIZE:-262144}"
LLAMA_CPP_REF="${LLAMA_CPP_REF:-}"
REBUILD="${REBUILD:-0}"

HERE="$(cd "$(dirname "$0")" && pwd)"
CUDA=/usr/local/cuda-12.6
LLAMA=/opt/llama.cpp
MODELS=/srv/ocs-intelligence/models
GGUF="$MODELS/qwen3.8-27b-q4_k_m.gguf"
ENV_FILE=/etc/ocs-intelligence/worker.env
PORT=8081

log() { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }
die() { printf '\033[1;31mERROR: %s\033[0m\n' "$*" >&2; exit 1; }

[[ $EUID -eq 0 ]] || die "run as root: sudo $0"
command -v nvidia-smi >/dev/null || die "nvidia-smi not found; install the NVIDIA driver first"
nvidia-smi -L >/dev/null || die "nvidia-smi can't see the GPUs"

log "GPUs"
nvidia-smi -L
mapfile -t GPU_UUIDS < <(nvidia-smi --query-gpu=uuid --format=csv,noheader | tr -d ' ')
GPU_COUNT=${#GPU_UUIDS[@]}
(( GPU_COUNT > 0 )) || die "no GPUs found"
echo "Found $GPU_COUNT GPU(s)"

# ---------------------------------------------------------------- packages
log "Base packages"
apt-get update
apt-get install -y cmake git build-essential wget curl openssl python3

# ---------------------------------------------------------------- CUDA 12.6
# CUDA 13 dropped Pascal (sm_61), so 12.6 specifically.
if [[ -x $CUDA/bin/nvcc ]]; then
  log "CUDA 12.6 already installed"
else
  log "Installing CUDA 12.6 (~4.5 GB, slow on school Wi-Fi)"
  wget -q https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/cuda-keyring_1.1-1_all.deb -O /tmp/cuda-keyring.deb
  dpkg -i /tmp/cuda-keyring.deb
  apt-get update
  apt-get install -y cuda-toolkit-12-6
fi
$CUDA/bin/nvcc --version | tail -n 2

# ---------------------------------------------------------------- llama.cpp
if [[ -x $LLAMA/bin/llama-server && $REBUILD != 1 ]]; then
  log "llama-server already built (REBUILD=1 to rebuild)"
else
  log "Building llama.cpp for sm_61 (~35 min on 2 cores)"
  mkdir -p $LLAMA
  if [[ ! -d $LLAMA/src ]]; then
    git clone https://github.com/ggml-org/llama.cpp.git $LLAMA/src
  else
    git -C $LLAMA/src fetch origin
  fi
  if [[ -n $LLAMA_CPP_REF ]]; then
    git -C $LLAMA/src checkout "$LLAMA_CPP_REF"
  else
    git -C $LLAMA/src checkout origin/master
  fi
  cd $LLAMA/src
  rm -rf build
  cmake -S . -B build -DGGML_CUDA=ON \
    -DCMAKE_CUDA_COMPILER=$CUDA/bin/nvcc \
    -DCUDAToolkit_ROOT=$CUDA \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_CUDA_ARCHITECTURES=61
  cmake --build build --config Release --parallel "$(nproc)"
  mkdir -p $LLAMA/bin
  # Keep $LLAMA/src/build: the installed binary's RUNPATH points into it.
  install -m 0755 build/bin/llama-server build/bin/llama-bench $LLAMA/bin/
  cd "$HERE"
fi
echo "llama.cpp commit: $(git -C $LLAMA/src rev-parse --short HEAD)"
$LLAMA/bin/llama-server --list-devices

# ---------------------------------------------------------------- model
if [[ -e $GGUF ]]; then
  log "Model already linked at $GGUF"
else
  if ! command -v ollama >/dev/null; then
    log "Installing Ollama"
    curl -fsSL https://ollama.com/install.sh | sh
  fi
  systemctl start ollama
  for _ in $(seq 30); do ollama list >/dev/null 2>&1 && break; sleep 1; done
  log "Pulling $MODEL (~17 GB)"
  ollama pull "$MODEL"
  BLOB="$(ollama show --modelfile "$MODEL" | awk '/^FROM \//{print $2; exit}')"
  [[ -f $BLOB ]] || die "couldn't find the GGUF blob for $MODEL (got '$BLOB')"
  echo "Blob: $BLOB"
  mkdir -p $MODELS
  ln -sf "$BLOB" "$GGUF"
fi
ls -lL "$GGUF"

# Ollama holds VRAM once a model is loaded; keep it off so the worker gets every card.
if systemctl list-unit-files ollama.service >/dev/null 2>&1; then
  log "Stopping and disabling Ollama (frees VRAM)"
  systemctl disable --now ollama || true
fi

# ---------------------------------------------------------------- worker env
log "Writing $ENV_FILE"
mkdir -p /etc/ocs-intelligence /var/lib/ocs-intelligence
KEY=""
[[ -f $ENV_FILE ]] && KEY="$(sed -n 's/^WORKER_API_KEY=//p' "$ENV_FILE")"
[[ -n $KEY && $KEY != CHANGE_ME* ]] || KEY="$(openssl rand -hex 24)"
SPLIT="$(printf '1%.0s,' $(seq "$GPU_COUNT"))"; SPLIT="${SPLIT%,}"
UUIDS="$(IFS=,; echo "${GPU_UUIDS[*]}")"
umask 077
cat > "$ENV_FILE" <<EOF
# Rig 2 worker: $MODEL on all $GPU_COUNT GPUs. Written by infra/rig2/setup.sh.
CUDA_VISIBLE_DEVICES=$UUIDS
DEFAULT_MODEL_GGUF=$GGUF
DEFAULT_MODEL_ID=$MODEL
CONTEXT_SIZE=$CONTEXT_SIZE
TENSOR_SPLIT=$SPLIT
WORKER_API_KEY=$KEY
EOF
chmod 0600 "$ENV_FILE"
echo "TENSOR_SPLIT=$SPLIT, CONTEXT_SIZE=$CONTEXT_SIZE"

# ---------------------------------------------------------------- service
log "Installing and starting ocs-llama.service"
install -m 0644 "$HERE/ocs-llama.service" /etc/systemd/system/ocs-llama.service
systemctl daemon-reload
systemctl enable ocs-llama
systemctl restart ocs-llama

log "Waiting for the worker to load (up to 10 min)"
for i in $(seq 120); do
  if curl -fs -H "Authorization: Bearer $KEY" http://127.0.0.1:$PORT/health >/dev/null; then
    echo "Healthy after ~$((i * 5))s"
    break
  fi
  systemctl is-failed --quiet ocs-llama && { journalctl -u ocs-llama -n 50 --no-pager; die "ocs-llama failed"; }
  sleep 5
done
curl -fs -H "Authorization: Bearer $KEY" http://127.0.0.1:$PORT/health >/dev/null \
  || { journalctl -u ocs-llama -n 50 --no-pager; die "worker not healthy after 10 min"; }

log "Test completion"
curl -s -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  http://127.0.0.1:$PORT/v1/chat/completions \
  -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"Say hello in five words.\"}],\"max_tokens\":64}"
echo
nvidia-smi --query-gpu=index,memory.used,memory.total --format=csv

log "Done: $MODEL on $GPU_COUNT GPUs at http://127.0.0.1:$PORT"
echo "Worker key: sudo grep WORKER_API_KEY $ENV_FILE"
echo "Logs:       journalctl -u ocs-llama -f"
