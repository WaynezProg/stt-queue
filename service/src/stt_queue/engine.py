from __future__ import annotations

from pathlib import Path
import subprocess


class WhisperCppEngine:
    def __init__(self, binary: str, model_path: Path):
        self.binary = binary
        self.model_path = model_path

    def build_command(self, audio_path: Path, output_prefix: Path, language: str | None) -> list[str]:
        command = [
            self.binary,
            "-m",
            str(self.model_path),
            "-f",
            str(audio_path),
            "-otxt",
            "-oj",
            "-of",
            str(output_prefix),
            "-nt",
        ]
        command.extend(["-l", language or "auto"])
        return command

    def transcribe(self, audio_path: Path, output_prefix: Path, language: str | None) -> tuple[Path, Path]:
        output_prefix.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            self.build_command(audio_path, output_prefix, language),
            check=True,
            capture_output=True,
            text=True,
        )
        text_path = output_prefix.with_suffix(".txt")
        json_path = output_prefix.with_suffix(".json")
        if not text_path.exists() or not json_path.exists():
            raise RuntimeError(f"whisper.cpp did not create expected outputs for {output_prefix}")
        return text_path, json_path
