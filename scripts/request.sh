#!/usr/bin/env bash
# Send one chat completion to https://ai.opencodingsociety.com/v1
#
#   ./scripts/request.sh
#   ./scripts/request.sh "Explain recursion in one sentence."
#   ./scripts/request.sh -m qwen3.8:27b "Name two sorting algorithms."
#   ./scripts/request.sh --stream "Count to five."

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi

: "${OCS_BASE_URL:=https://ai.opencodingsociety.com/v1}"
: "${OCS_API_KEY:?Set OCS_API_KEY in .env (see .env.example)}"

MODEL="qwen2.5:0.5b"
STREAM=false
MAX_TOKENS=80

while [[ $# -gt 0 ]]; do
  case "$1" in
    -m|--model)
      MODEL="$2"
      shift 2
      ;;
    -n|--max-tokens)
      MAX_TOKENS="$2"
      shift 2
      ;;
    --stream)
      STREAM=true
      shift
      ;;
    -h|--help)
      sed -n '2,8p' "$0"
      exit 0
      ;;
    --)
      shift
      break
      ;;
    -*)
      echo "Unknown flag: $1" >&2
      exit 2
      ;;
    *)
      break
      ;;
  esac
done

PROMPT="${*:-Say hello in one short sentence.}"
OCS_BASE_URL="${OCS_BASE_URL%/}"

BODY=$(python3 -c 'import json,sys; print(json.dumps({
  "model": sys.argv[1],
  "stream": sys.argv[2] == "true",
  "max_tokens": int(sys.argv[3]),
  "messages": [{"role": "user", "content": sys.argv[4]}],
}))' "$MODEL" "$STREAM" "$MAX_TOKENS" "$PROMPT")

curl -sS ${STREAM:+-N} \
  "$OCS_BASE_URL/chat/completions" \
  -H "Authorization: Bearer $OCS_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$BODY"
echo
