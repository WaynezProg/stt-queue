from pathlib import Path

from stt_queue.db import Database


def test_create_and_claim_job(tmp_path: Path):
    db = Database(tmp_path / "jobs.sqlite")
    db.init()
    db.create_job(
        job_id="job_1",
        source="manual",
        audio_path="/tmp/input.m4a",
        engine="whisper.cpp",
        model="small",
        priority=100,
        language=None,
        max_retries=2,
        callback_url=None,
        metadata_json=None,
        checksum_sha256="abc",
    )
    job = db.claim_next_job()
    assert job is not None
    assert job.id == "job_1"
    assert job.status == "processing"
    assert job.queue_latency_sec is not None
    assert db.claim_next_job() is None


def test_retry_failed_job(tmp_path: Path):
    db = Database(tmp_path / "jobs.sqlite")
    db.init()
    db.create_job("job_1", "manual", "/tmp/input.m4a", "whisper.cpp", "small", 100, None, 2)
    db.mark_failed("job_1", "engine_error", "failed")
    assert db.retry_job("job_1") is True
    assert db.get_job("job_1").status == "queued"


def test_stale_processing_job_can_be_requeued(tmp_path: Path):
    db = Database(tmp_path / "jobs.sqlite")
    db.init()
    db.create_job("job_1", "manual", "/tmp/input.m4a", "whisper.cpp", "small", 100, None, 2)
    db.claim_next_job()
    assert db.requeue_stale_processing_jobs(older_than_seconds=0) == 1
    assert db.get_job("job_1").status == "queued"


def test_recent_processing_job_is_not_requeued_when_threshold_not_met(tmp_path: Path):
    db = Database(tmp_path / "jobs.sqlite")
    db.init()
    db.create_job("job_1", "manual", "/tmp/input.m4a", "whisper.cpp", "small", 100, None, 2)
    db.claim_next_job()
    assert db.requeue_stale_processing_jobs(older_than_seconds=3600) == 0
    assert db.get_job("job_1").status == "processing"


def test_mark_done_persists_latency_metrics(tmp_path: Path):
    db = Database(tmp_path / "jobs.sqlite")
    db.init()
    db.create_job("job_1", "manual", "/tmp/input.m4a", "whisper.cpp", "large-v3-turbo-q5_0", 100, None, 2)
    db.claim_next_job()
    db.mark_done(
        "job_1",
        "/tmp/out.txt",
        "/tmp/out.json",
        10.0,
        normalize_sec=0.25,
        transcribe_sec=1.75,
        processing_sec=2.0,
        queue_latency_sec=0.05,
    )
    job = db.get_job("job_1")
    assert job.normalize_sec == 0.25
    assert job.transcribe_sec == 1.75
    assert job.processing_sec == 2.0
    assert job.queue_latency_sec == 0.05


def test_init_migrates_existing_db_with_latency_columns(tmp_path: Path):
    db = Database(tmp_path / "jobs.sqlite")
    with db.connect() as conn:
        conn.execute(
            """
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
            )
            """
        )

    db.init()
    db.create_job("job_1", "manual", "/tmp/input.m4a", "whisper.cpp", "large-v3-turbo-q5_0", 100, None, 2)
    db.claim_next_job()
    db.mark_done(
        "job_1",
        "/tmp/out.txt",
        "/tmp/out.json",
        10.0,
        normalize_sec=0.25,
        transcribe_sec=1.75,
        processing_sec=2.0,
        queue_latency_sec=0.05,
    )

    assert db.get_job("job_1").processing_sec == 2.0
