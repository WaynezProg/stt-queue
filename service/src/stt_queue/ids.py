from datetime import datetime, timezone
from secrets import token_hex


def new_job_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"stt_{stamp}_{token_hex(4)}"
