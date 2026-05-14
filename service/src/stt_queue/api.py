from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile

from stt_queue.audio import sha256_file, store_upload_path
from stt_queue.config import Settings
from stt_queue.db import Database
from stt_queue.ids import new_job_id


def create_app(settings: Settings) -> FastAPI:
    app = FastAPI(title="STT Queue Service")
    db = Database(settings.db_path)
    db.init()

    def require_token(authorization: Annotated[str | None, Header()] = None) -> None:
        if settings.api_token is None:
            return
        if authorization != f"Bearer {settings.api_token}":
            raise HTTPException(status_code=401, detail="unauthorized")

    @app.get("/health")
    def health() -> dict[str, bool]:
        return {"ok": True}

    @app.post("/stt/jobs", dependencies=[Depends(require_token)])
    async def submit_job(
        audio: UploadFile = File(...),
        source: str = Form("manual"),
        language: str | None = Form(None),
        model: str | None = Form(None),
        priority: int = Form(100),
        callback_url: str | None = Form(None),
        metadata_json: str | None = Form(None),
    ) -> dict[str, str]:
        job_id = new_job_id()
        target = store_upload_path(settings.incoming_dir, job_id, audio.filename or "audio.bin")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(await audio.read())
        checksum = sha256_file(target)
        db.create_job(
            job_id=job_id,
            source=source,
            audio_path=str(target),
            engine=settings.default_engine,
            model=model or settings.default_model,
            priority=priority,
            language=language,
            max_retries=settings.max_retries,
            callback_url=callback_url,
            metadata_json=metadata_json,
            checksum_sha256=checksum,
        )
        return {"id": job_id, "status": "queued"}

    @app.get("/stt/jobs/{job_id}", dependencies=[Depends(require_token)])
    def get_job(job_id: str) -> dict[str, object]:
        job = db.get_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="job not found")
        body: dict[str, object] = {
            "id": job.id,
            "status": job.status,
            "source": job.source,
            "engine": job.engine,
            "model": job.model,
            "language": job.language,
            "duration_sec": job.duration_sec,
            "error_code": job.error_code,
            "error_message": job.error_message,
            "metrics": {
                "queue_latency_sec": job.queue_latency_sec,
                "normalize_sec": job.normalize_sec,
                "transcribe_sec": job.transcribe_sec,
                "processing_sec": job.processing_sec,
            },
        }
        if job.transcript_text_path and Path(job.transcript_text_path).exists():
            body["text"] = Path(job.transcript_text_path).read_text(encoding="utf-8").strip()
        return body

    @app.post("/stt/jobs/{job_id}/retry", dependencies=[Depends(require_token)])
    def retry_job(job_id: str) -> dict[str, object]:
        retried = db.retry_job(job_id)
        if not retried:
            raise HTTPException(status_code=409, detail="job cannot be retried")
        return {"id": job_id, "status": "queued"}

    return app


app = create_app(Settings.from_env())
