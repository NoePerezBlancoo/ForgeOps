import os
import uuid

import pytest
from rq import Queue, SimpleWorker
from rq.serializers import JSONSerializer

from app.core.config import settings
from app.core.database import SessionLocal, set_database_context
from app.core.enums import JobStatus
from app.core.redis import get_queue_redis
from app.jobs.models import BackgroundJob
from app.jobs.service import enqueue_job

pytestmark = pytest.mark.skipif(
    os.getenv("TEST_WORKER_INTEGRATION") != "true",
    reason="Requiere PostgreSQL y Redis reales",
)


def test_durable_job_roundtrip_through_redis_and_worker():
    key = f"worker-integration:{uuid.uuid4()}"
    job_id = None
    original_dispatch = settings.job_dispatch_enabled
    settings.job_dispatch_enabled = True
    try:
        with SessionLocal() as db:
            set_database_context(db, "system")
            job = enqueue_job(db, "HEALTHCHECK", {"value": "ok"}, key)
            job_id = job.id

        connection = get_queue_redis()
        queue = Queue(settings.job_queue_name, connection=connection, serializer=JSONSerializer)
        worker = SimpleWorker([queue], connection=connection, serializer=JSONSerializer)
        assert worker.work(burst=True)

        with SessionLocal() as db:
            set_database_context(db, "system")
            completed = db.get(BackgroundJob, job_id)
            assert completed.status == JobStatus.SUCCEEDED
            assert completed.attempts == 1
            assert completed.result_summary == "worker:ok"
            db.delete(completed)
            db.commit()
        queue.fetch_job(str(job_id)).delete()
    finally:
        settings.job_dispatch_enabled = original_dispatch
