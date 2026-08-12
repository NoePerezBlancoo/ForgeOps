import logging

from rq import Queue, Worker
from rq.serializers import JSONSerializer

from app.core.config import settings
from app.core.database import SessionLocal, set_database_context
from app.core.logging import configure_logging
from app.core.redis import get_redis
from app.jobs.service import dispatch_pending_jobs


def main() -> None:
    configure_logging()
    logger = logging.getLogger("forgeops.worker")
    with SessionLocal() as db:
        set_database_context(db, "system")
        dispatched = dispatch_pending_jobs(db)
    logger.info("worker_started", extra={"event": "worker_started"})
    if dispatched:
        logger.info("pending_jobs_dispatched", extra={"event": "pending_jobs_dispatched"})
    connection = get_redis()
    queue = Queue(settings.job_queue_name, connection=connection, serializer=JSONSerializer)
    worker = Worker([queue], connection=connection, serializer=JSONSerializer)
    worker.work(with_scheduler=True)


if __name__ == "__main__":
    main()
