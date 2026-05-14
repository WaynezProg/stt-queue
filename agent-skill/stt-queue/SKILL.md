---
name: stt-queue
description: Use when an AI agent needs to transcribe audio files through the local STT queue service. Covers voice messages, meeting recordings, and any speech input that must be converted to text before continuing a workflow.
---

# STT Queue

Use this skill when an audio file must be transcribed before continuing a workflow.

## Contract

- STT service default URL: `http://127.0.0.1:8787`
- Production engine: `whisper.cpp`
- Production model: `large-v3-turbo-q5_0`
- Queue mode: async SQLite job queue
- Worker mode: one worker processes one job at a time; worker runs warmup on start.
- Long audio must be submitted as a job and polled; do not block webhook flows waiting for long transcription.

## When To Use

- A voice message or audio clip needs transcription.
- A workflow receives an audio file and needs the text before reasoning.
- A meeting or call recording should be queued rather than processed synchronously.

## Do Not

- Do not use Qwen-ASR, SenseVoice, FunASR, or other mainland China ASR models.
- Do not claim transcription quality is final without checking the returned text.
- Do not expose `/stt/` publicly without bearer token protection.
- Do not block a webhook response waiting for long audio — submit and poll.

## Quick Commands

Run commands from this skill directory.

Health:

```bash
scripts/health.sh
```

Submit audio:

```bash
scripts/submit_audio.sh /path/to/audio.m4a --source agent --language zh
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

If the job is still `queued` or `processing`, respond with a short pending acknowledgement and continue by job id later.
