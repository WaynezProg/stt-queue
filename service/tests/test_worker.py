from pathlib import Path
import time

from stt_queue.db import Database
from stt_queue.worker import process_one, warmup_engine


class FakeEngine:
    def transcribe(self, audio_path: Path, output_prefix: Path, language: str | None):
        time.sleep(0.001)
        txt = output_prefix.with_suffix(".txt")
        js = output_prefix.with_suffix(".json")
        txt.parent.mkdir(parents=True, exist_ok=True)
        txt.write_text("hello", encoding="utf-8")
        js.write_text('{"text":"hello"}', encoding="utf-8")
        return txt, js


def fake_normalize(ffmpeg_binary: str, input_path: Path, output_path: Path) -> None:
    time.sleep(0.001)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(input_path.read_bytes())


def test_process_one_normalizes_and_marks_done(tmp_path: Path):
    audio = tmp_path / "input.m4a"
    audio.write_bytes(b"fake")
    db = Database(tmp_path / "jobs.sqlite")
    db.init()
    db.create_job("job_1", "manual", str(audio), "whisper.cpp", "small", 100, None, 2)
    assert process_one(
        db=db,
        engine=FakeEngine(),
        processing_dir=tmp_path / "processing",
        transcripts_dir=tmp_path / "transcripts",
        normalize_func=fake_normalize,
    ) is True
    job = db.get_job("job_1")
    assert job.status == "done"
    assert Path(job.normalized_audio_path).exists()
    assert Path(job.transcript_text_path).read_text(encoding="utf-8") == "hello"
    assert job.normalize_sec is not None
    assert job.transcribe_sec is not None
    assert job.processing_sec is not None
    assert job.queue_latency_sec is not None


def test_warmup_engine_creates_silence_and_runs_engine(tmp_path: Path):
    result = warmup_engine(FakeEngine(), tmp_path / "warmup")
    assert result["status"] == "ok"
    assert result["warmup_sec"] is not None
    assert (tmp_path / "warmup" / "warmup.wav").exists()
    assert (tmp_path / "warmup" / "warmup.txt").exists()
