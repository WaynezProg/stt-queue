from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


VALID_STATUSES = {"queued", "processing", "done", "failed", "canceled"}


@dataclass(frozen=True)
class Job:
    id: str
    source: str
    status: str
    priority: int
    engine: str
    model: str
    audio_path: Path
    language: str | None = None
    normalized_audio_path: Path | None = None
    transcript_text_path: Path | None = None
    transcript_json_path: Path | None = None
    duration_sec: float | None = None
    checksum_sha256: str | None = None
    retry_count: int = 0
    max_retries: int = 2
    error_code: str | None = None
    error_message: str | None = None
    callback_url: str | None = None
    metadata_json: str | None = None
    queue_latency_sec: float | None = None
    normalize_sec: float | None = None
    transcribe_sec: float | None = None
    processing_sec: float | None = None
