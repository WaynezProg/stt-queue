from pathlib import Path
import wave

from stt_queue.audio import safe_suffix, sha256_file, store_upload_path, wav_duration_sec


def test_safe_suffix_rejects_shell_names():
    assert safe_suffix("voice.m4a") == ".m4a"
    assert safe_suffix("../../voice;rm.wav") == ".wav"
    assert safe_suffix("voice") == ".bin"


def test_sha256_file(tmp_path: Path):
    path = tmp_path / "a.txt"
    path.write_bytes(b"abc")
    assert sha256_file(path) == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_store_upload_path(tmp_path: Path):
    target = store_upload_path(tmp_path, "job_1", "voice.m4a")
    assert target == tmp_path / "job_1" / "original.m4a"


def test_wav_duration_sec(tmp_path: Path):
    path = tmp_path / "sample.wav"
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b"\x00\x00" * 32000)
    assert wav_duration_sec(path) == 2.0
