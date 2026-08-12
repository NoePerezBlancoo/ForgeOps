import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select

from app.core.crypto import decrypt_json
from app.core.database import SessionLocal, set_database_context
from app.core.enums import JobStatus
from app.email.service import get_email_service, message_from_payload
from app.jobs.models import BackgroundJob

logger = logging.getLogger("forgeops.worker")


def execute_job(job_id: str) -> str:
    with SessionLocal() as db:
        set_database_context(db, "system")
        job = db.scalar(
            select(BackgroundJob)
            .where(BackgroundJob.id == uuid.UUID(job_id))
            .with_for_update()
        )
        if not job:
            raise ValueError("Trabajo no encontrado")
        if job.status == JobStatus.SUCCEEDED:
            return job.result_summary or "already_completed"
        job.status = JobStatus.RUNNING
        job.attempts += 1
        job.started_at = datetime.now(UTC)
        job.last_error = None
        payload = decrypt_json(job.payload_encrypted)
        db.commit()
        try:
            result = _run(job.job_type, payload)
        except Exception as exc:
            db.refresh(job)
            job.status = JobStatus.FAILED if job.attempts >= job.max_attempts else JobStatus.QUEUED
            job.last_error = str(exc)[:1000]
            db.commit()
            logger.exception("job_failed", extra={"event": "job_failed"})
            raise
        db.refresh(job)
        job.status = JobStatus.SUCCEEDED
        job.result_summary = result[:500]
        job.finished_at = datetime.now(UTC)
        job.last_error = None
        db.commit()
        return result


def _run(job_type: str, payload: dict) -> str:
    if job_type == "EMAIL_SEND":
        get_email_service().send(message_from_payload(payload))
        return f"email:{payload.get('template', 'generic')}"
    raise ValueError(f"Tipo de trabajo no soportado: {job_type}")
