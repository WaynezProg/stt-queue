---
name: stt-queue
description: Use when OpenClaw needs to transcribe local audio files, LINE voice messages, meeting recordings, or other speech inputs through the Mac Mini STT queue service.
---

# STT Queue

Use this skill when an audio file must be transcribed before continuing an OpenClaw workflow.

## Contract

- STT service default URL: `http://127.0.0.1:8787`
- Production engine: `whisper.cpp`
- Production model: `large-v3-turbo-q5_0`
- Queue mode: async SQLite job queue
- Worker mode: one worker processes one job at a time; launchd worker runs warmup on start.
- Long audio must be submitted as a job and polled; do not block webhook flows waiting for long transcription.

## When To Use

- LINE voice message needs transcription.
- User provides a local audio file path.
- n8n/OpenClaw workflow needs speech converted to text before LLM reasoning.
- Meeting or call audio should be queued rather than sent to Spark as raw audio.

## Do Not

- Do not send raw audio to Spark unless explicitly requested for a separate experiment.
- Do not use Qwen, SenseVoice, FunASR, or other China-mainland ASR models.
- Do not claim transcription quality is final without checking the returned text.
- Do not expose `/stt/` publicly without bearer token protection.

## Quick Commands

Run commands from this skill directory.

Health:

```bash
scripts/health.sh
```

Submit audio:

```bash
scripts/submit_audio.sh /path/to/audio.m4a --source line --language zh
```

Poll:

```bash
scripts/poll_job.sh stt_20260513053605_d0530a2f
```

Retry failed job:

```bash
scripts/retry_job.sh stt_20260513053605_d0530a2f
```

## Workflow

1. Confirm service health with `scripts/health.sh`.
2. Submit the audio file with `scripts/submit_audio.sh`.
3. Save the returned `id`.
4. Poll with `scripts/poll_job.sh <id>` until status is `done` or `failed`.
5. If `done`, use the returned `text` as the transcript.
6. If `failed`, inspect `error_code` and `error_message`; retry once only if the error is transient.

## Environment

Optional environment variables:

```text
STT_BASE_URL=http://127.0.0.1:8787
STT_API_TOKEN=<bearer-token-if-enabled>
```

If `STT_API_TOKEN` is set, scripts send `Authorization: Bearer <token>`.

## Result Handling

Expected poll result:

```json
{
  "id": "stt_...",
  "status": "done",
  "engine": "whisper.cpp",
  "model": "large-v3-turbo-q5_0",
  "duration_sec": 4.939,
  "metrics": {
    "queue_latency_sec": 0.05,
    "normalize_sec": 0.2,
    "transcribe_sec": 1.5,
    "processing_sec": 1.8
  },
  "text": "transcript here"
}
```

For LINE or webhook flows, if the job is still `queued` or `processing`, answer with a short pending message and continue by job id later.
