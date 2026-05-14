#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd -P)"
# shellcheck source=common.sh
source "$SCRIPT_DIR/common.sh"

usage() {
  cat >&2 <<'EOF'
Usage:
  submit_audio.sh AUDIO_PATH [--source SOURCE] [--language LANG] [--priority N] [--callback-url URL] [--metadata-json JSON]

Defaults:
  source=manual
  priority=100
EOF
}

if [[ $# -lt 1 ]]; then
  usage
  exit 2
fi

AUDIO_PATH="$1"
shift

SOURCE="manual"
LANGUAGE=""
PRIORITY="100"
CALLBACK_URL=""
METADATA_JSON=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --source)
      SOURCE="$2"
      shift 2
      ;;
    --language)
      LANGUAGE="$2"
      shift 2
      ;;
    --priority)
      PRIORITY="$2"
      shift 2
      ;;
    --callback-url)
      CALLBACK_URL="$2"
      shift 2
      ;;
    --metadata-json)
      METADATA_JSON="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if [[ ! -f "$AUDIO_PATH" ]]; then
  echo "Audio file not found: $AUDIO_PATH" >&2
  exit 1
fi

ARGS=(
  -F "audio=@${AUDIO_PATH}"
  -F "source=${SOURCE}"
  -F "priority=${PRIORITY}"
)

if [[ -n "$LANGUAGE" ]]; then
  ARGS+=(-F "language=${LANGUAGE}")
fi
if [[ -n "$CALLBACK_URL" ]]; then
  ARGS+=(-F "callback_url=${CALLBACK_URL}")
fi
if [[ -n "$METADATA_JSON" ]]; then
  ARGS+=(-F "metadata_json=${METADATA_JSON}")
fi

stt_curl "${ARGS[@]}" "$(stt_base_url)/stt/jobs"
printf '\n'
