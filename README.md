# stt-queue

Async speech-to-text queue service for Apple Silicon Macs. Built on whisper.cpp + SQLite + FastAPI. Designed to run locally on a Mac Mini (or any Apple Silicon Mac) so audio never leaves your machine.

## What it does

Audio is uploaded to the API once. The service stores it on disk, queues a transcription job, runs whisper.cpp locally, and serves the transcript via poll. Long audio never blocks the caller — submit, get a job ID, poll until done.

```text
Client
  -> POST /stt/jobs   (upload audio)
  -> GET  /stt/jobs/{id}  (poll for transcript)

Worker (background)
  -> picks queued jobs
  -> ffmpeg normalize
  -> whisper.cpp transcribe
  -> writes transcript to disk
```

## Components

| Component | Implementation |
|---|---|
| API | FastAPI (Python) |
| Queue DB | SQLite (WAL mode) |
| Audio store | Local filesystem |
| Worker | Single-process, one job at a time |
| STT engine | whisper.cpp (`whisper-cli`) |
| Audio normalization | ffmpeg |

## Quick start

### Requirements

- Apple Silicon Mac (M1/M2/M3/M4)
- macOS 13+
- [uv](https://docs.astral.sh/uv/) (`brew install uv`)
- Homebrew

### 1. Install system dependencies

```bash
brew install whisper-cpp ffmpeg
```

### 2. Download a whisper model

```bash
mkdir -p ~/stt-models/whisper.cpp
curl -L -o ~/stt-models/whisper.cpp/ggml-large-v3-turbo-q5_0.bin \
  "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo-q5_0.bin"
```

Other models: `small`, `medium-q5_0`, `large-v3-turbo-q5_0` (recommended default).

### 3. Install service dependencies

```bash
cd service
uv sync --extra dev
```

### 4. Start API and worker

In one terminal:

```bash
cd service
STT_ROOT_DIR=/tmp/stt-dev \
STT_MODEL_PATH=~/stt-models/whisper.cpp/ggml-large-v3-turbo-q5_0.bin \
uv run uvicorn stt_queue.api:app --host 127.0.0.1 --port 8787
```

In another:

```bash
cd service
STT_ROOT_DIR=/tmp/stt-dev \
STT_MODEL_PATH=~/stt-models/whisper.cpp/ggml-large-v3-turbo-q5_0.bin \
uv run python -m stt_queue.worker --warmup
```

### 5. Submit a job

```bash
curl -s -X POST http://127.0.0.1:8787/stt/jobs \
  -F "audio=@/path/to/audio.m4a" \
  -F "language=zh"
# {"id":"stt_...","status":"queued"}
```

### 6. Poll for result

```bash
curl -s http://127.0.0.1:8787/stt/jobs/stt_...
# {"id":"stt_...","status":"done","text":"...","metrics":{...}}
```

## API

### `POST /stt/jobs`

Submit an audio file for transcription.

| Field | Type | Required | Description |
|---|---|---|---|
| `audio` | file | yes | Audio file (m4a, mp3, wav, ogg, …) |
| `source` | string | no | Label for the origin (default: `manual`) |
| `language` | string | no | Language hint (e.g. `zh`, `en`) |
| `model` | string | no | Override default model name |
| `priority` | int | no | Lower = higher priority (default: 100) |
| `callback_url` | string | no | Webhook URL to POST result when done |
| `metadata_json` | string | no | Arbitrary JSON stored with the job |

Returns `{"id": "stt_...", "status": "queued"}`.

### `GET /stt/jobs/{id}`

Poll job status.

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

Status values: `queued` → `processing` → `done` / `failed`.

### `POST /stt/jobs/{id}/retry`

Requeue a failed job.

### `GET /health`

Returns `{"ok": true}`.

## Authentication

Set `STT_API_TOKEN` to enable bearer token auth. All `/stt/*` endpoints require `Authorization: Bearer <token>`. Unset = no auth (local-only use).

## Production deployment (Mac Mini + launchd)

See [mac-mini-deployment.md](mac-mini-deployment.md) for full setup instructions including:

- Bootstrap script (`deploy/bootstrap-mac-mini.sh`)
- launchd plist templates (`deploy/*.plist.example`)
- Nginx reverse proxy config (`deploy/nginx-stt-location.conf`)

Quick bootstrap:

```bash
cd deploy
bash bootstrap-mac-mini.sh
```

## Shell scripts (agent / automation use)

`agent-skill/stt-queue/scripts/` contains shell scripts for submitting, polling, and retrying jobs from an AI agent or automation context. Set `STT_BASE_URL` and optionally `STT_API_TOKEN` to configure the endpoint.

```bash
# health check
./agent-skill/stt-queue/scripts/health.sh

# submit
./agent-skill/stt-queue/scripts/submit_audio.sh /path/to/audio.m4a --source agent --language zh

# poll
./agent-skill/stt-queue/scripts/poll_job.sh stt_...

# retry failed
./agent-skill/stt-queue/scripts/retry_job.sh stt_...
```

The `agent-skill/stt-queue/SKILL.md` file is a ready-to-use playbook for AI agent frameworks (Claude Code, OpenClaw, n8n, or any tool that supports skill/prompt files).

## Configuration

All settings via environment variables. See [service/README.md](service/README.md) for the full list.

Key variables:

| Variable | Default | Description |
|---|---|---|
| `STT_ROOT_DIR` | `~/stt-service` | Runtime data root |
| `STT_MODEL_PATH` | — | Path to `.bin` model file (required) |
| `STT_MODEL` | `large-v3-turbo-q5_0` | Model name (metadata label) |
| `STT_API_TOKEN` | — | Bearer token (disabled if unset) |
| `STT_PORT` | `8787` | API port |

## Docs

English and Traditional Chinese versions are provided for each doc.

| Doc | English | 繁體中文 |
|---|---|---|
| Architecture | [architecture.md](architecture.md) | [architecture.zh.md](architecture.zh.md) |
| Queue contract | [queue-contract.md](queue-contract.md) | [queue-contract.zh.md](queue-contract.zh.md) |
| macOS deployment | [mac-mini-deployment.md](mac-mini-deployment.md) | [mac-mini-deployment.zh.md](mac-mini-deployment.zh.md) |
| Benchmark plan | [benchmark-plan.md](benchmark-plan.md) | [benchmark-plan.zh.md](benchmark-plan.zh.md) |
| Service dev guide | [service/README.md](service/README.md) | — |

## License

MIT
