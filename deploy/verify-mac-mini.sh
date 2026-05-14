#!/usr/bin/env bash
set -euo pipefail

SERVICE_HOME="${STT_SERVICE_HOME:-$HOME/stt-service}"
APP_DIR="$SERVICE_HOME/app"
RUNTIME_DIR="$SERVICE_HOME/runtime"
MODEL_PATH="${STT_MODEL_PATH:-$HOME/stt-models/whisper.cpp/ggml-large-v3-turbo-q5_0.bin}"

command -v whisper-cli
command -v whisper-server
command -v ffmpeg
command -v uv

test -f "$MODEL_PATH"
test -d "$APP_DIR"

cd "$APP_DIR"
STT_ROOT_DIR="$RUNTIME_DIR" STT_MODEL=large-v3-turbo-q5_0 STT_MODEL_PATH="$MODEL_PATH" uv run pytest -q
curl -fsS http://127.0.0.1:8787/health
