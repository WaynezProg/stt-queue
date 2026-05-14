from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    root_dir: Path
    host: str = "127.0.0.1"
    port: int = 8787
    whisper_binary: str = "whisper-cli"
    ffmpeg_binary: str = "ffmpeg"
    default_engine: str = "whisper.cpp"
    default_model: str = "large-v3-turbo-q5_0"
    model_path: Path | None = None
    max_retries: int = 2
    api_token: str | None = None

    @classmethod
    def from_env(cls) -> "Settings":
        root = Path(os.environ.get("STT_ROOT_DIR", str(Path.home() / "stt-service"))).expanduser()
        model_path = os.environ.get("STT_MODEL_PATH")
        return cls(
            root_dir=root,
            host=os.environ.get("STT_HOST", "127.0.0.1"),
            port=int(os.environ.get("STT_PORT", "8787")),
            whisper_binary=os.environ.get("STT_WHISPER_BINARY", "whisper-cli"),
            ffmpeg_binary=os.environ.get("STT_FFMPEG_BINARY", "ffmpeg"),
            default_engine=os.environ.get("STT_ENGINE", "whisper.cpp"),
            default_model=os.environ.get("STT_MODEL", "large-v3-turbo-q5_0"),
            model_path=Path(model_path).expanduser() if model_path else None,
            max_retries=int(os.environ.get("STT_MAX_RETRIES", "2")),
            api_token=os.environ.get("STT_API_TOKEN"),
        )

    @property
    def db_path(self) -> Path:
        return self.root_dir / "db" / "stt_jobs.sqlite"

    @property
    def incoming_dir(self) -> Path:
        return self.root_dir / "data" / "incoming"

    @property
    def processing_dir(self) -> Path:
        return self.root_dir / "data" / "processing"

    @property
    def transcripts_dir(self) -> Path:
        return self.root_dir / "data" / "transcripts"
