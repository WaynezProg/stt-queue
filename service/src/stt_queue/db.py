from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sqlite3

from stt_queue.models import Job


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _elapsed_seconds(started_at: str | None, ended_at: str) -> float | None:
    if started_at is None:
        return None
    try:
        start = datetime.fromisoformat(started_at)
        end = datetime.fromisoformat(ended_at)
    except ValueError:
        return None
    return max(0.0, (end - start).total_seconds())


class Database:
    def __init__(self, path: Path):
        self.path = path

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def init(self) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS stt_jobs (
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
                  queue_latency_sec REAL,
                  normalize_sec REAL,
                  transcribe_sec REAL,
                  processing_sec REAL,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL,
                  started_at TEXT,
                  finished_at TEXT
                )
                """
            )
            self._ensure_columns(conn)
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_stt_jobs_claim
                  ON stt_jobs(status, priority, created_at)
                """
            )

    def _ensure_columns(self, conn: sqlite3.Connection) -> None:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(stt_jobs)").fetchall()}
        for name in ("queue_latency_sec", "normalize_sec", "transcribe_sec", "processing_sec"):
            if name not in columns:
                conn.execute(f"ALTER TABLE stt_jobs ADD COLUMN {name} REAL")

    def create_job(
        self,
        job_id: str,
        source: str,
        audio_path: str,
        engine: str,
        model: str,
        priority: int,
        language: str | None,
        max_retries: int,
        callback_url: str | None = None,
        metadata_json: str | None = None,
        checksum_sha256: str | None = None,
    ) -> None:
        now = _now()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO stt_jobs (
                  id, source, status, priority, engine, model, language,
                  audio_path, checksum_sha256, max_retries, callback_url,
                  metadata_json, created_at, updated_at
                )
                VALUES (?, ?, 'queued', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    source,
                    priority,
                    engine,
                    model,
                    language,
                    audio_path,
                    checksum_sha256,
                    max_retries,
                    callback_url,
                    metadata_json,
                    now,
                    now,
                ),
            )

    def get_job(self, job_id: str) -> Job | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM stt_jobs WHERE id = ?", (job_id,)).fetchone()
        return self._row_to_job(row) if row else None

    def claim_next_job(self) -> Job | None:
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                """
                SELECT * FROM stt_jobs
                WHERE status = 'queued'
                ORDER BY priority ASC, created_at ASC
                LIMIT 1
                """
            ).fetchone()
            if row is None:
                conn.commit()
                return None
            now = _now()
            queue_latency_sec = _elapsed_seconds(row["created_at"], now)
            updated = conn.execute(
                """
                UPDATE stt_jobs
                SET status = 'processing',
                    started_at = ?,
                    updated_at = ?,
                    queue_latency_sec = ?,
                    error_code = NULL,
                    error_message = NULL
                WHERE id = ? AND status = 'queued'
                """,
                (now, now, queue_latency_sec, row["id"]),
            ).rowcount
            if updated != 1:
                conn.commit()
                return None
            row = conn.execute("SELECT * FROM stt_jobs WHERE id = ?", (row["id"],)).fetchone()
            conn.commit()
            return self._row_to_job(row)

    def set_normalized_audio_path(self, job_id: str, normalized_audio_path: str) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE stt_jobs
                SET normalized_audio_path = ?, updated_at = ?
                WHERE id = ?
                """,
                (normalized_audio_path, _now(), job_id),
            )

    def mark_done(
        self,
        job_id: str,
        text_path: str,
        json_path: str,
        duration_sec: float | None,
        *,
        normalize_sec: float | None = None,
        transcribe_sec: float | None = None,
        processing_sec: float | None = None,
        queue_latency_sec: float | None = None,
    ) -> None:
        now = _now()
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE stt_jobs
                SET status = 'done',
                    transcript_text_path = ?,
                    transcript_json_path = ?,
                    duration_sec = ?,
                    normalize_sec = ?,
                    transcribe_sec = ?,
                    processing_sec = ?,
                    queue_latency_sec = COALESCE(?, queue_latency_sec),
                    updated_at = ?,
                    finished_at = ?,
                    error_code = NULL,
                    error_message = NULL
                WHERE id = ?
                """,
                (
                    text_path,
                    json_path,
                    duration_sec,
                    normalize_sec,
                    transcribe_sec,
                    processing_sec,
                    queue_latency_sec,
                    now,
                    now,
                    job_id,
                ),
            )

    def mark_failed(self, job_id: str, error_code: str, error_message: str) -> None:
        now = _now()
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE stt_jobs
                SET status = 'failed',
                    retry_count = retry_count + 1,
                    error_code = ?,
                    error_message = ?,
                    updated_at = ?,
                    finished_at = ?
                WHERE id = ?
                """,
                (error_code, error_message[:2000], now, now, job_id),
            )

    def retry_job(self, job_id: str) -> bool:
        with self.connect() as conn:
            updated = conn.execute(
                """
                UPDATE stt_jobs
                SET status = 'queued',
                    error_code = NULL,
                    error_message = NULL,
                    started_at = NULL,
                    finished_at = NULL,
                    queue_latency_sec = NULL,
                    normalize_sec = NULL,
                    transcribe_sec = NULL,
                    processing_sec = NULL,
                    updated_at = ?
                WHERE id = ?
                  AND status = 'failed'
                  AND retry_count <= max_retries
                """,
                (_now(), job_id),
            ).rowcount
        return updated == 1

    def requeue_stale_processing_jobs(self, older_than_seconds: int) -> int:
        with self.connect() as conn:
            updated = conn.execute(
                """
                UPDATE stt_jobs
                SET status = 'queued',
                    error_code = 'stale_processing',
                    error_message = 'job was requeued after worker timeout',
                    updated_at = ?
                WHERE status = 'processing'
                  AND datetime(started_at) <= datetime('now', ?)
                """,
                (_now(), f"-{older_than_seconds} seconds"),
            ).rowcount
        return updated

    def _row_to_job(self, row: sqlite3.Row) -> Job:
        return Job(
            id=row["id"],
            source=row["source"],
            status=row["status"],
            priority=row["priority"],
            engine=row["engine"],
            model=row["model"],
            language=row["language"],
            audio_path=Path(row["audio_path"]),
            normalized_audio_path=Path(row["normalized_audio_path"]) if row["normalized_audio_path"] else None,
            transcript_text_path=Path(row["transcript_text_path"]) if row["transcript_text_path"] else None,
            transcript_json_path=Path(row["transcript_json_path"]) if row["transcript_json_path"] else None,
            duration_sec=row["duration_sec"],
            checksum_sha256=row["checksum_sha256"],
            retry_count=row["retry_count"],
            max_retries=row["max_retries"],
            error_code=row["error_code"],
            error_message=row["error_message"],
            callback_url=row["callback_url"],
            metadata_json=row["metadata_json"],
            queue_latency_sec=row["queue_latency_sec"],
            normalize_sec=row["normalize_sec"],
            transcribe_sec=row["transcribe_sec"],
            processing_sec=row["processing_sec"],
        )
