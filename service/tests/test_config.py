from pathlib import Path

from stt_queue.config import Settings


def test_settings_defaults_to_loopback_and_local_data(tmp_path: Path):
    settings = Settings(root_dir=tmp_path)
    assert settings.host == "127.0.0.1"
    assert settings.port == 8787
    assert settings.db_path == tmp_path / "db" / "stt_jobs.sqlite"
    assert settings.incoming_dir == tmp_path / "data" / "incoming"
    assert settings.ffmpeg_binary == "ffmpeg"
    assert settings.default_model == "large-v3-turbo-q5_0"


def test_settings_from_env_reads_runtime_values(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("STT_ROOT_DIR", str(tmp_path))
    monkeypatch.setenv("STT_MODEL_PATH", "/models/ggml-small.bin")
    monkeypatch.setenv("STT_API_TOKEN", "secret")
    settings = Settings.from_env()
    assert settings.root_dir == tmp_path
    assert settings.model_path == Path("/models/ggml-small.bin")
    assert settings.api_token == "secret"
