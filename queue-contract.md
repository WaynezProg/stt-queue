# STT Queue Contract

> 繁體中文版：[queue-contract.zh.md](queue-contract.zh.md)

## Directory Layout

```text
stt-service/
  data/
    incoming/
    processing/
    transcripts/
    done/
    failed/
  db/
    stt_jobs.sqlite
  logs/
```

## Job States

```text
queued -> processing -> done
queued -> processing -> failed
queued -> canceled
failed -> queued
```

`failed -> queued` transition is only allowed when retry count is below the limit.

## SQLite Schema

```sql
CREATE TABLE stt_jobs (
  id TEXT PRIMARY KEY,
  source TEXT NOT NULL,
  status TEXT NOT NULL,
  priority INTEGER NOT NULL DEFAULT 100,
  engine TEXT NOT NULL DEFAULT 'whisper.cpp',
  model TEXT NOT NULL,
  language TEXT,
  audio_path TEXT NOT NULL,
  normalized_audio_path TEXT,
  transcript_text_path TEXT,
  transcript_json_path TEXT,
  duration_sec REAL,
  checksum_sha256 TEXT,
  retry_count INTEGER NOT NULL DEFAULT 0,
  max_retries INTEGER NOT NULL DEFAULT 2,
  error_code TEXT,
  error_message TEXT,
  callback_url TEXT,
  metadata_json TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  started_at TEXT,
  finished_at TEXT
);

CREATE INDEX idx_stt_jobs_claim
  ON stt_jobs(status, priority, created_at);
```

## Atomic Claim

Workers must claim jobs inside a transaction to prevent multiple workers from picking the same job.

```sql
BEGIN IMMEDIATE;

SELECT id
FROM stt_jobs
WHERE status = 'queued'
ORDER BY priority ASC, created_at ASC
LIMIT 1;

UPDATE stt_jobs
SET status = 'processing',
    started_at = CURRENT_TIMESTAMP,
    updated_at = CURRENT_TIMESTAMP
WHERE id = ? AND status = 'queued';

COMMIT;
```

## HTTP API

### Submit

```http
POST /stt/jobs
Content-Type: multipart/form-data
```

Fields:

```text
audio:         required file
source:        api | webhook | agent | manual
language:      optional
model:         optional
priority:      optional (lower = higher priority, default 100)
callback_url:  optional
metadata_json: optional
```

Meeting Pipeline multi-audio jobs should send project/file metadata in `metadata_json`:

```json
{
  "projectId": "project-id",
  "fileId": "audio-file-id",
  "storedFilename": "stored-name.m4a",
  "originalName": "防詐會議1.m4a",
  "audioIndex": 0,
  "audioCount": 3
}
```

When `projectId` and `fileId` are present, the worker copies completed transcripts to
`$N8N_DATA_ROOT/<projectId>/whisper/transcript-<fileId>.txt` and
`$N8N_DATA_ROOT/<projectId>/whisper/transcript-<fileId>.json`. For single-audio jobs
or jobs without `fileId`, the legacy `transcript.txt` / `transcript.json` outputs remain supported.

Response:

```json
{
  "id": "stt_20260513_abcdef",
  "status": "queued"
}
```

### Poll

```http
GET /stt/jobs/{id}
```

Response:

```json
{
  "id": "stt_20260513_abcdef",
  "status": "done",
  "text": "transcript here",
  "duration_sec": 18.2,
  "engine": "whisper.cpp",
  "model": "large-v3-turbo-q5_0",
  "metrics": {
    "queue_latency_sec": 0.05,
    "normalize_sec": 0.2,
    "transcribe_sec": 1.5,
    "processing_sec": 1.8
  }
}
```

### Retry

```http
POST /stt/jobs/{id}/retry
```

Only allowed for `failed` jobs.

## Worker Timeout

| Audio length | Timeout |
|---|---:|
| <= 60 s | 120 s |
| <= 10 min | 20 min |
| > 10 min | background only — do not block synchronously |

## Retention

| Data | Recommended retention |
|---|---:|
| Raw audio | 24 hours |
| Normalized wav | 24 hours |
| Transcript txt/json | 30 days |
| Failed job audio | 7 days |
