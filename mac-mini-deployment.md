# macOS Deployment (Mac Mini + launchd)

> 繁體中文版：[mac-mini-deployment.zh.md](mac-mini-deployment.zh.md)

This guide covers deploying the STT queue service on macOS with launchd for process supervision. The service runs on any Mac with Homebrew and Python 3.12+, but the instructions here are optimized for a Mac Mini used as a local AI gateway.

## Runtime Principles

- System tools via Homebrew.
- Python packages via `uv` — do not pollute system Python.
- Do not use `nvm` / `pyenv` / `asdf` / curl installers.
- Do not modify `~/.zshrc` or `~/.profile`.

## Install Dependencies

```bash
brew install whisper-cpp ffmpeg uv
```

## Download a Model

Model files are not included in the repo. Recommended path:

```text
~/stt-models/whisper.cpp/
```

Production default:

```text
ggml-large-v3-turbo-q5_0.bin
```

Fallback:

```text
ggml-small.bin
```

Download:

```bash
mkdir -p ~/stt-models/whisper.cpp
curl -L -o ~/stt-models/whisper.cpp/ggml-large-v3-turbo-q5_0.bin \
  "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo-q5_0.bin"
```

## Service Root

Create an isolated service root:

```text
~/stt-service/
```

Keep this separate from other application directories.

## Bootstrap

The `deploy/bootstrap-mac-mini.sh` script stages the service code and downloads the model:

```bash
cd deploy
bash bootstrap-mac-mini.sh
```

Customize with environment variables:

```bash
STT_SERVICE_HOME=~/stt-service \
STT_MODEL_DIR=~/stt-models/whisper.cpp \
STT_MODEL_NAME=large-v3-turbo-q5_0 \
bash bootstrap-mac-mini.sh
```

## Port

Bind to loopback only:

```text
127.0.0.1:8787
```

If exposed via Nginx, only expose the `/stt/` route and require a bearer token:

```text
/stt/ -> 127.0.0.1:8787
```

See `deploy/nginx-stt-location.conf` for a sample Nginx config.

## launchd (Process Supervision)

Split into two LaunchAgents — API and worker are separate so the worker can be restarted or swapped without disrupting the ingress:

```text
ai.stt.api.plist    — FastAPI server
ai.stt.worker.plist — transcription worker
```

Copy and customize the examples:

```bash
cp deploy/ai.stt.api.plist.example ~/Library/LaunchAgents/ai.stt.api.plist
cp deploy/ai.stt.worker.plist.example ~/Library/LaunchAgents/ai.stt.worker.plist
# Edit both files: replace YOUR_USERNAME and adjust paths
```

Load:

```bash
launchctl load ~/Library/LaunchAgents/ai.stt.api.plist
launchctl load ~/Library/LaunchAgents/ai.stt.worker.plist
```

Verify:

```bash
bash deploy/verify-mac-mini.sh
```

## Worker Profiles

Production:

```text
STT_ENGINE=whisper.cpp
STT_MODEL=large-v3-turbo-q5_0
STT_MODEL_PATH=~/stt-models/whisper.cpp/ggml-large-v3-turbo-q5_0.bin
STT_CONCURRENCY=1
```

A/B (Apple Silicon MLX):

```text
STT_ENGINE=mlx-whisper
STT_MODEL=mlx-community/whisper-small
STT_CONCURRENCY=1
```

Speed experiment:

```text
STT_ENGINE=lightning-whisper-mlx
STT_MODEL=distil-medium.en
STT_CONCURRENCY=1
```

## Downstream Integration

Do not block on long STT jobs. Recommended pattern:

```text
submit audio -> receive job id -> poll / callback -> continue text workflow
```

Short audio (< 30 s) can be polled synchronously; longer audio should return a pending status immediately to avoid webhook timeouts.

## Security

- STT API defaults to loopback only.
- If exposed via Nginx, require a bearer token (`STT_API_TOKEN`).
- Raw audio is deleted after TTL.
- Logs do not record full transcript content to avoid sensitive data exposure.
- Failed job audio is retained for up to 7 days for debugging.
