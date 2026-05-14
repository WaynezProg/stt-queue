# STT Queue Architecture

> 繁體中文版：[architecture.zh.md](architecture.zh.md)

## Goal

Minimize audio transfer cost. Audio is uploaded to the local machine once; decode, normalize, STT, and transcript storage all happen locally. Only the resulting text is handed off to downstream workflows.

## Topology

```text
Client
  -> Local ingress
      -> audio file on disk
      -> SQLite stt_jobs
      -> STT worker
          -> whisper.cpp
          -> transcript JSON / TXT
      -> downstream text workflow
```

## Components

| Component | Choice | Notes |
|---|---|---|
| Ingress API | FastAPI | Receives audio, creates job, returns job id. |
| Queue DB | SQLite WAL | Single-machine queue; no Redis needed initially. |
| Audio store | local filesystem | Audio is not stored in DB — only path and checksum. |
| Worker | single process | Concurrency `1` initially; benchmark before raising. |
| STT engine | whisper.cpp | Production baseline. |
| Optional engine | mlx-whisper / lightning-whisper-mlx | A/B via the same worker interface. |

## Data Flow

1. Ingress receives audio, writes to `data/incoming/{job_id}/original.*`.
2. ffmpeg normalizes to `16kHz mono wav`, writes to `data/processing/{job_id}/input.wav`.
3. Creates a `stt_jobs` row with status `queued`.
4. Worker atomically claims the job, sets status to `processing`.
5. Worker calls the STT engine, generates transcript.
6. Result written to `data/transcripts/{job_id}.json` and `.txt`.
7. Job status set to `done`; if `callback_url` is set, downstream is notified.
8. Raw audio deleted after TTL; transcripts retained longer.

## Why run STT locally

Cross-machine audio transfer adds network cost and ties up remote resources (e.g. a GPU server) with preprocessing work that doesn't need a GPU. Audio is large; text is small. Completing STT at the ingress machine is a cleaner boundary.

## Model Strategy

Production default:

```text
engine: whisper.cpp
model: large-v3-turbo-q5_0
language: auto or zh/en
timestamps: segment-level
```

Fallback:

```text
model: small
```

Speed A/B candidates:

```text
engine: mlx-whisper
model: mlx-community/whisper-small or distil-whisper
```

Excluded (policy):

```text
Qwen-ASR
SenseVoice
FunASR
```
