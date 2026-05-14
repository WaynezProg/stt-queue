#!/usr/bin/env bash
set -euo pipefail

stt_base_url() {
  printf '%s' "${STT_BASE_URL:-http://127.0.0.1:8787}"
}

stt_curl() {
  if [[ -n "${STT_API_TOKEN:-}" ]]; then
    curl -fsS -H "Authorization: Bearer ${STT_API_TOKEN}" "$@"
  else
    curl -fsS "$@"
  fi
}
