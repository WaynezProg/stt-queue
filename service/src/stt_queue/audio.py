from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
import wave


ALLOWED_SUFFIXES = {
    ".aac",
    ".aiff",
    ".flac",
    ".m4a",
    ".mp3",
    ".mp4",
    ".oga",
    ".ogg",
    ".wav",
    ".webm",
}


def safe_suffix(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if not suffix:
        return ".bin"
    return suffix if suffix in ALLOWED_SUFFIXES else ".bin"


def store_upload_path(incoming_dir: Path, job_id: str, filename: str) -> Path:
    return incoming_dir / job_id / f"original{safe_suffix(filename)}"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_audio(ffmpeg_binary: str, input_path: Path, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            ffmpeg_binary,
            "-y",
            "-i",
            str(input_path),
            "-ar",
            "16000",
            "-ac",
            "1",
            "-vn",
            str(output_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def wav_duration_sec(path: Path) -> float | None:
    try:
        with wave.open(str(path), "rb") as wav:
            frames = wav.getnframes()
            rate = wav.getframerate()
        return round(frames / float(rate), 3) if rate else None
    except (OSError, wave.Error, EOFError):
        return None
