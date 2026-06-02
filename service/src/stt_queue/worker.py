from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import time
from typing import Callable
import wave
import re

from stt_queue.audio import normalize_audio, wav_duration_sec
from stt_queue.config import Settings
from stt_queue.db import Database
from stt_queue.engine import WhisperCppEngine


NormalizeFunc = Callable[[str, Path, Path], None]


def _safe_output_name(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return safe[:120] or None


def _copy_to_n8n_data(text_path: Path, json_path: Path, metadata_json: str | None) -> None:
    """Copy transcript to shared n8n-data directory for file-based detection."""
    if not metadata_json:
        return
    try:
        meta = json.loads(metadata_json)
    except Exception:
        return
    project_id = meta.get("projectId")
    if not project_id:
        return

    n8n_root = Path(os.environ.get("N8N_DATA_ROOT", str(Path.home() / "n8n-data"))).expanduser()
    whisper_dir = n8n_root / project_id / "whisper"
    try:
        whisper_dir.mkdir(parents=True, exist_ok=True)
        file_id = _safe_output_name(meta.get("fileId"))
        audio_count = meta.get("audioCount")
        if file_id:
            output_stem = f"transcript-{file_id}"
            shutil.copy2(text_path, whisper_dir / f"{output_stem}.txt")
            shutil.copy2(json_path, whisper_dir / f"{output_stem}.json")
            if audio_count in (None, 1, "1"):
                shutil.copy2(text_path, whisper_dir / "transcript.txt")
                shutil.copy2(json_path, whisper_dir / "transcript.json")
        else:
            shutil.copy2(text_path, whisper_dir / "transcript.txt")
            shutil.copy2(json_path, whisper_dir / "transcript.json")
        print(f"[STT] Copied transcript to {whisper_dir}", flush=True)
    except Exception as exc:
        print(f"[STT] Failed to copy to n8n-data: {exc}", flush=True)


def _elapsed(start: float) -> float:
    return round(time.perf_counter() - start, 6)


def _write_silence_wav(path: Path, duration_sec: float = 0.25, sample_rate: int = 16000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame_count = int(duration_sec * sample_rate)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b"\x00\x00" * frame_count)


def warmup_engine(
    engine: WhisperCppEngine,
    warmup_dir: Path,
    language: str | None = None,
) -> dict[str, object]:
    warmup_audio = warmup_dir / "warmup.wav"
    output_prefix = warmup_dir / "warmup"
    _write_silence_wav(warmup_audio)
    started = time.perf_counter()
    text_path, json_path = engine.transcribe(warmup_audio, output_prefix, language)
    return {
        "status": "ok",
        "warmup_sec": _elapsed(started),
        "audio_path": str(warmup_audio),
        "transcript_text_path": str(text_path),
        "transcript_json_path": str(json_path),
    }


def process_one(
    db: Database,
    engine: WhisperCppEngine,
    processing_dir: Path,
    transcripts_dir: Path,
    normalize_func: NormalizeFunc = normalize_audio,
    ffmpeg_binary: str = "ffmpeg",
) -> bool:
    job = db.claim_next_job()
    if job is None:
        return False

    try:
        processing_started = time.perf_counter()
        normalized_path = processing_dir / job.id / "input.wav"
        normalize_started = time.perf_counter()
        normalize_func(ffmpeg_binary, job.audio_path, normalized_path)
        normalize_sec = _elapsed(normalize_started)
        db.set_normalized_audio_path(job.id, str(normalized_path))
        duration_sec = wav_duration_sec(normalized_path)
        output_prefix = transcripts_dir / job.id
        transcribe_started = time.perf_counter()
        text_path, json_path = engine.transcribe(normalized_path, output_prefix, job.language)
        transcribe_sec = _elapsed(transcribe_started)
        db.mark_done(
            job.id,
            str(text_path),
            str(json_path),
            duration_sec,
            normalize_sec=normalize_sec,
            transcribe_sec=transcribe_sec,
            processing_sec=_elapsed(processing_started),
            queue_latency_sec=job.queue_latency_sec,
        )
        # Copy transcript to shared n8n-data for file-based pipeline detection
        _copy_to_n8n_data(text_path, json_path, job.metadata_json)
    except Exception as exc:
        db.mark_failed(job.id, "worker_error", str(exc))
    return True


def run_forever(
    db: Database,
    engine: WhisperCppEngine,
    processing_dir: Path,
    transcripts_dir: Path,
    ffmpeg_binary: str = "ffmpeg",
    sleep_sec: float = 2.0,
) -> None:
    while True:
        did_work = process_one(
            db=db,
            engine=engine,
            processing_dir=processing_dir,
            transcripts_dir=transcripts_dir,
            ffmpeg_binary=ffmpeg_binary,
        )
        if not did_work:
            time.sleep(sleep_sec)


def build_runtime(settings: Settings) -> tuple[Database, WhisperCppEngine]:
    if settings.model_path is None:
        raise SystemExit("STT_MODEL_PATH is required for worker")
    db = Database(settings.db_path)
    db.init()
    engine = WhisperCppEngine(settings.whisper_binary, settings.model_path)
    return db, engine


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="process one queued job and exit")
    parser.add_argument("--warmup", action="store_true", help="run a tiny warmup transcription before polling jobs")
    parser.add_argument("--warmup-only", action="store_true", help="run warmup and exit without processing jobs")
    args = parser.parse_args()
    settings = Settings.from_env()
    db, engine = build_runtime(settings)
    if args.warmup or args.warmup_only:
        result = warmup_engine(engine, settings.root_dir / "data" / "warmup")
        print(json.dumps(result, ensure_ascii=False), flush=True)
    if args.warmup_only:
        return
    if args.once:
        process_one(
            db=db,
            engine=engine,
            processing_dir=settings.processing_dir,
            transcripts_dir=settings.transcripts_dir,
            ffmpeg_binary=settings.ffmpeg_binary,
        )
        return
    run_forever(
        db=db,
        engine=engine,
        processing_dir=settings.processing_dir,
        transcripts_dir=settings.transcripts_dir,
        ffmpeg_binary=settings.ffmpeg_binary,
    )


if __name__ == "__main__":
    main()
