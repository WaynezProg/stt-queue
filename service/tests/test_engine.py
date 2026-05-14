from pathlib import Path

from stt_queue.engine import WhisperCppEngine


def test_whisper_command_uses_model_audio_and_output_prefix(tmp_path: Path):
    engine = WhisperCppEngine(binary="whisper-cli", model_path=Path("/models/ggml-small.bin"))
    command = engine.build_command(
        audio_path=Path("/tmp/input.wav"),
        output_prefix=tmp_path / "job_1",
        language="zh",
    )
    assert command[:4] == ["whisper-cli", "-m", "/models/ggml-small.bin", "-f"]
    assert str(Path("/tmp/input.wav")) in command
    assert "-l" in command
    assert "zh" in command
    assert "-otxt" in command
    assert "-oj" in command
    assert "-of" in command
    assert "-nt" in command
