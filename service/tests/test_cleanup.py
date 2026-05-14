from datetime import datetime, timedelta, timezone
from pathlib import Path
import os

from stt_queue.cleanup import remove_old_files


def test_remove_old_files_deletes_expired_file(tmp_path: Path):
    old_file = tmp_path / "old.wav"
    old_file.write_bytes(b"x")
    old_time = (datetime.now(timezone.utc) - timedelta(days=2)).timestamp()
    os.utime(old_file, (old_time, old_time))
    removed = remove_old_files(tmp_path, older_than_hours=24)
    assert removed == 1
    assert not old_file.exists()
