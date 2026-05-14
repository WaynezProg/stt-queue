#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd -P)"
# shellcheck source=common.sh
source "$SCRIPT_DIR/common.sh"

stt_curl "$(stt_base_url)/health"
printf '\n'
