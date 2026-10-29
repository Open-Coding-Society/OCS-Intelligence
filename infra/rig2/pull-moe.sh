#!/usr/bin/env bash
# Download the MoE GGUFs into /srv/ocs-intelligence/models (resumable).
cd /srv/ocs-intelligence/models
HF=https://huggingface.co
get() { curl -fL --retry 20 --retry-delay 5 -C - -o "$2.part" "$HF/$1" && mv "$2.part" "$2" && echo "DONE $2"; }
get unsloth/Qwen3.6-35B-A3B-GGUF/resolve/main/Qwen3.6-35B-A3B-UD-Q4_K_XL.gguf qwen3.6-35b-a3b-ud-q4_k_xl.gguf
get unsloth/Qwen3-Coder-Next-GGUF/resolve/main/Qwen3-Coder-Next-UD-Q4_K_XL.gguf qwen3-coder-next-ud-q4_k_xl.gguf
echo ALL_DONE
