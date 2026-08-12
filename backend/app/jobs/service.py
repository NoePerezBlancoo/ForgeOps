import logging
import uuid
from datetime import UTC, datetime

from redis.exceptions import RedisError
from rq import Queue, Retry
from rq.serializers import JSONSerializer
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.crypto import encrypt_json
from app.core.enums import JobStatus
from app.core.redis import get_queue_redis
from app.jobs.models import BackgroundJob

logger = logging.getLogger("forgeops.jobs")


def enqueue_job(
    db: Session,
    job_type: str,
    payload: dict,
    idempotency_key: str,
    company_id: uuid.UUID | None = None,
) -> BackgroundJob:
    existing = db.scalar(
        select(BackgroundJob).where(BackgroundJob.idempotency_key == idempotency_key)
    )
    if existing:
        return existing
    job = BackgroundJob(
        company_id=company_id,
        job_type=job_type,
        idempotency_key=idempotency_key,
        status=JobStatus.PENDING,
        payload_encrypted=encrypt_json(payload),
        max_attempts=settings.job_max_attempts,
        available_at=datetime.now(UTC),
    )
    db.add(job)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(
            select(BackgroundJob).where(BackgroundJob.idempotency_key == idempotency_key)
        )
        if existing:
            return existing
        raise
    if settings.job_dispatch_enabled:
        dispatch_job(db, job)
    return job


def dispatch_job(db: Session, job: BackgroundJob) -> bool:
    try:
        queue = Queue(
            settings.job_queue_name,
            connection=get_queue_redis(),
            serializer=JSONSerializer,
            default_timeout=900,
        )
        if job.status == JobStatus.QUEUED and queue.fetch_job(str(job.id)):
            return False
        queue.enqueue(
            "app.jobs.tasks.execute_job",
            str(job.id),
            job_id=str(job.id),
            retry=Retry(max=max(0, job.max_attempts - 1), interval=[10, 60, 300]),
            result_ttl=86400,
            failure_ttl=604800,
        )
        job.status = JobStatus.QUEUED
        job.last_error = None
        db.commit()
        return True
    except (RedisError, OSError) as exc:
        job.status = JobStatus.PENDING
        job.last_error = "Redis no disponible; trabajo pendiente de redistribucion"
        db.commit()
        logger.warning("job_dispatch_deferred", extra={"event": "job_dispatch_deferred"})
        if settings.redis_required and settings.app_env == "production":
            raise RuntimeError("No se pudo distribuir el trabajo") from exc
        return False


def dispatch_pending_jobs(db: Session, limit: int = 100) -> int:
    jobs = list(
        db.scalars(
            select(BackgroundJob)
            .where(BackgroundJob.status.in_([JobStatus.PENDING, JobStatus.QUEUED]))
            .order_by(BackgroundJob.created_at)
            .limit(limit)
        )
    )
    return sum(dispatch_job(db, job) for job in jobs)
