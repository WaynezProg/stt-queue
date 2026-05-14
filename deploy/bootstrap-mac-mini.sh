#!/usr/bin/env bash
set -euo pipefail

SERVICE_HOME="${STT_SERVICE_HOME:-$HOME/stt-service}"
APP_DIR="$SERVICE_HOME/app"
RUNTIME_DIR="$SERVICE_HOME/runtime"
MODEL_DIR="${STT_MODEL_DIR:-$HOME/stt-models/whisper.cpp}"
MODEL_NAME="${STT_MODEL_NAME:-large-v3-turbo-q5_0}"
MODEL_PATH="$MODEL_DIR/ggml-$MODEL_NAME.bin"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd -P)"
SOLUTION_DIR="$(cd -- "$SCRIPT_DIR/.." >/dev/null 2>&1 && pwd -P)"

brew install whisper-cpp ffmpeg

command -v uv >/dev/null 2>&1 || {
  echo "uv is required. Install it with the existing environment standard before continuing." >&2
  exit 1
}

mkdir -p "$APP_DIR" "$RUNTIME_DIR" "$MODEL_DIR"
rsync -a --delete \
  --exclude '.venv' \
  --exclude '.pytest_cache' \
  "$SOLUTION_DIR/service/" "$APP_DIR/"

if [[ ! -f "$MODEL_PATH" ]]; then
  curl -L \
    --output "$MODEL_PATH" \
    "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-$MODEL_NAME.bin"
fi

cd "$APP_DIR"
uv sync --extra dev

cat <<EOF
STT service staged.

App:     $APP_DIR
Runtime: $RUNTIME_DIR
Model:   $MODEL_PATH

Manual API:
  STT_ROOT_DIR=$RUNTIME_DIR STT_MODEL=large-v3-turbo-q5_0 STT_MODEL_PATH=$MODEL_PATH uv run uvicorn stt_queue.api:app --host 127.0.0.1 --port 8787

Manual worker:
  STT_ROOT_DIR=$RUNTIME_DIR STT_MODEL=large-v3-turbo-q5_0 STT_MODEL_PATH=$MODEL_PATH uv run python -m stt_queue.worker --once
EOF
