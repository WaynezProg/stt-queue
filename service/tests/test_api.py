from fastapi.testclient import TestClient

from stt_queue.api import create_app
from stt_queue.config import Settings
from stt_queue.db import Database


def test_submit_and_poll_job(tmp_path):
    app = create_app(Settings(root_dir=tmp_path))
    client = TestClient(app)
    response = client.post(
        "/stt/jobs",
        data={"source": "manual", "model": "small"},
        files={"audio": ("voice.m4a", b"fake-audio", "audio/mp4")},
    )
    assert response.status_code == 200
    job_id = response.json()["id"]
    poll = client.get(f"/stt/jobs/{job_id}")
    assert poll.status_code == 200
    assert poll.json()["status"] == "queued"
    assert poll.json()["metrics"]["queue_latency_sec"] is None


def test_bearer_token_required_when_configured(tmp_path):
    app = create_app(Settings(root_dir=tmp_path, api_token="secret"))
    client = TestClient(app)
    response = client.get("/stt/jobs/missing")
    assert response.status_code == 401


def test_poll_done_job_returns_latency_metrics(tmp_path):
    settings = Settings(root_dir=tmp_path)
    db = Database(settings.db_path)
    db.init()
    text_path = tmp_path / "transcripts" / "job_1.txt"
    json_path = tmp_path / "transcripts" / "job_1.json"
    text_path.parent.mkdir(parents=True)
    text_path.write_text("hello", encoding="utf-8")
    json_path.write_text('{"text":"hello"}', encoding="utf-8")
    db.create_job("job_1", "manual", "/tmp/input.wav", "whisper.cpp", "large-v3-turbo-q5_0", 100, "en", 2)
    db.claim_next_job()
    db.mark_done(
        "job_1",
        str(text_path),
        str(json_path),
        4.5,
        normalize_sec=0.2,
        transcribe_sec=1.5,
        processing_sec=1.8,
        queue_latency_sec=0.1,
    )

    client = TestClient(create_app(settings))
    response = client.get("/stt/jobs/job_1")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "done"
    assert payload["metrics"] == {
        "queue_latency_sec": 0.1,
        "normalize_sec": 0.2,
        "transcribe_sec": 1.5,
        "processing_sec": 1.8,
    }
