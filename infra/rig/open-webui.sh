#!/bin/sh
# Open WebUI on Rig 1, as it runs now. Reconstructed from `docker inspect open-webui` on 2026-10-29
# (the container was started by hand; no compose file exists on the rig).
# Its OpenAI connections live in the database on the volume, not here: see docs/reference/hosts.md.
# Only OLLAMA_BASE_URL was passed at `docker run`; every other env var is the image default.
set -eu
docker run -d \
  --name open-webui \
  --restart always \
  -p 3000:8080 \
  --add-host host.docker.internal:host-gateway \
  -v open-webui:/app/backend/data \
  -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
  ghcr.io/open-webui/open-webui:main
