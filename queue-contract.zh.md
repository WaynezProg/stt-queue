# STT Queue Contract

## 目錄建議

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

## Job 狀態

```text
queued -> processing -> done
queued -> processing -> failed
queued -> canceled
failed -> queued
```

`failed -> queued` 只允許 retry 次數未超過上限。

## SQLite schema

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

## Atomic claim

Worker claim job 時必須用 transaction，避免多 worker 搶同一筆。

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
audio: required file
source: api | webhook | agent | manual
language: optional
model: optional
priority: optional
callback_url: optional
metadata_json: optional
```

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
  "model": "small"
}
```

### Retry

```http
POST /stt/jobs/{id}/retry
```

只允許 `failed` job。

## Worker timeout

| 音檔長度 | timeout |
|---|---:|
| <= 60 秒 | 120 秒 |
| <= 10 分鐘 | 20 分鐘 |
| > 10 分鐘 | background-only，禁止同步等待 |

## Retention

| 資料 | 建議保留 |
|---|---:|
| 原始音檔 | 24 小時 |
| normalized wav | 24 小時 |
| transcript txt/json | 30 天 |
| failed audio | 7 天 |
