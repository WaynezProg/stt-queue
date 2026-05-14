#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd -P)"
# shellcheck source=common.sh
source "$SCRIPT_DIR/common.sh"

if [[ $# -ne 1 ]]; then
  echo "Usage: retry_job.sh JOB_ID" >&2
  exit 2
fi

stt_curl -X POST "$(stt_base_url)/stt/jobs/$1/retry"
printf '\n'
