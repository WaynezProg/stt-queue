# STT Queue Service

Local Mac Mini STT queue service using whisper.cpp + SQLite.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- `whisper-cli` and `ffmpeg` (install via `brew install whisper-cpp ffmpeg`)
- A whisper.cpp model file (e.g. `ggml-large-v3-turbo-q5_0.bin`)

## Setup

```bash
uv sync --extra dev
```

## Run tests

```bash
uv run pytest
```

## Run API

```bash
STT_ROOT_DIR=/path/to/stt-service \
STT_MODEL_PATH=/path/to/ggml-large-v3-turbo-q5_0.bin \
uv run uvicorn stt_queue.api:app --host 127.0.0.1 --port 8787
```

## Run worker

```bash
# Continuous (with warmup on start):
STT_ROOT_DIR=/path/to/stt-service \
STT_MODEL_PATH=/path/to/ggml-large-v3-turbo-q5_0.bin \
uv run python -m stt_queue.worker --warmup

# Process one job then exit:
STT_ROOT_DIR=/path/to/stt-service \
STT_MODEL_PATH=/path/to/ggml-large-v3-turbo-q5_0.bin \
uv run python -m stt_queue.worker --warmup --once

# Warmup only (verify model loads):
STT_ROOT_DIR=/path/to/stt-service \
STT_MODEL_PATH=/path/to/ggml-large-v3-turbo-q5_0.bin \
uv run python -m stt_queue.worker --warmup-only
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `STT_ROOT_DIR` | `~/stt-service` | Base directory for runtime data |
| `STT_HOST` | `127.0.0.1` | API bind address |
| `STT_PORT` | `8787` | API port |
| `STT_ENGINE` | `whisper.cpp` | Transcription engine |
| `STT_MODEL` | `large-v3-turbo-q5_0` | Model name (for metadata only) |
| `STT_MODEL_PATH` | — | Absolute path to the `.bin` model file |
| `STT_WHISPER_BINARY` | `whisper-cli` | Path to `whisper-cli` binary |
| `STT_FFMPEG_BINARY` | `ffmpeg` | Path to `ffmpeg` binary |
| `STT_MAX_RETRIES` | `2` | Max auto-retries per job |
| `STT_API_TOKEN` | — | Bearer token for API auth (disabled if unset) |

## Poll Response

Poll responses include latency metrics:

```json
{
  "id": "stt_...",
  "status": "done",
  "engine": "whisper.cpp",
  "model": "large-v3-turbo-q5_0",
  "duration_sec": 4.9,
  "metrics": {
    "queue_latency_sec": 0.05,
    "normalize_sec": 0.2,
    "transcribe_sec": 1.5,
    "processing_sec": 1.8
  },
  "text": "transcript here"
}
```
