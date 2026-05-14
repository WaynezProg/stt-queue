from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path


def remove_old_files(root: Path, older_than_hours: int) -> int:
    if not root.exists():
        return 0
    cutoff = datetime.now(timezone.utc) - timedelta(hours=older_than_hours)
    removed = 0
    for path in sorted(root.rglob("*"), reverse=True):
        if path.is_file():
            modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
            if modified < cutoff:
                path.unlink()
                removed += 1
    for path in sorted(root.rglob("*"), reverse=True):
        if path.is_dir():
            try:
                path.rmdir()
            except OSError:
                pass
    return removed
