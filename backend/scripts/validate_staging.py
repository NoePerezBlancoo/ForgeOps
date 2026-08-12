import json
import os
import time
import uuid

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from botocore.exceptions import ClientError
from fastapi import HTTPException
from rq import Queue
from rq.serializers import JSONSerializer
from sqlalchemy import delete, select, text, update
from sqlalchemy.exc import DBAPIError

import app.models  # noqa: F401
from app.companies.models import Company
from app.core.config import settings
from app.core.database import SessionLocal, engine, set_database_context
from app.core.enums import JobStatus
from app.core.redis import get_queue_redis
from app.documents.storage import S3StorageService, get_document_storage
from app.jobs.models import BackgroundJob
from app.jobs.service import enqueue_job
from app.plants.models import Plant


def require_staging() -> None:
    if settings.app_env != "staging" or os.getenv("STAGING_VALIDATION_ENABLED") != "true":
        raise RuntimeError("La validacion solo puede ejecutarse en STAGING de forma explicita")


def validate_schema_and_role() -> dict:
    config = Config("alembic.ini")
    expected = set(ScriptDirectory.from_config(config).get_heads())
    with engine.connect() as connection:
        current = set(MigrationContext.configure(connection).get_current_heads())
        role = connection.execute(
            text(
                "SELECT current_user, rolsuper, rolcreaterole, rolcreatedb, "
                "rolinherit, rolcanlogin, rolbypassrls "
                "FROM pg_roles WHERE rolname = current_user"
            )
        ).one()
        owns_tenant_tables = connection.scalar(
            text(
                "SELECT EXISTS ("
                "SELECT 1 FROM pg_class c JOIN pg_roles r ON r.oid = c.relowner "
                "WHERE c.relname IN ('companies', 'plants', 'assets') "
                "AND r.rolname = current_user)"
            )
        )
    if current != expected:
        raise AssertionError("Alembic no esta en head")
    if any((role.rolsuper, role.rolcreaterole, role.rolcreatedb, role.rolbypassrls)):
        raise AssertionError("El usuario runtime tiene privilegios administrativos")
    if role.rolinherit or not role.rolcanlogin or owns_tenant_tables:
        raise AssertionError("El usuario runtime no cumple el perfil restringido")
    return {
        "alembic_head": sorted(current),
        "runtime_login_restricted": True,
        "runtime_owns_tenant_tables": False,
    }


def validate_rls_and_pool_reuse() -> dict:
    suffix = uuid.uuid4().hex[:10]
    company_a_id = company_b_id = plant_a_id = plant_b_id = None
    blocked_insert = blocked_update = blocked_delete = False
    try:
        with SessionLocal() as db:
            set_database_context(db, "system")
            company_a = Company(name=f"STAGING RLS A {suffix}", tax_id=f"SR-A-{suffix}")
            company_b = Company(name=f"STAGING RLS B {suffix}", tax_id=f"SR-B-{suffix}")
            db.add_all([company_a, company_b])
            db.flush()
            plant_a = Plant(company_id=company_a.id, name="RLS Plant A", code=f"A{suffix}")
            plant_b = Plant(company_id=company_b.id, name="RLS Plant B", code=f"B{suffix}")
            db.add_all([plant_a, plant_b])
            db.commit()
            company_a_id, company_b_id = company_a.id, company_b.id
            plant_a_id, plant_b_id = plant_a.id, plant_b.id

        expected = ((company_a_id, plant_a_id), (company_b_id, plant_b_id))
        for company_id, visible_id in expected * 20:
            with SessionLocal() as db:
                set_database_context(db, "tenant", company_id)
                visible = list(db.scalars(select(Plant.id).order_by(Plant.id)))
                if visible != [visible_id]:
                    raise AssertionError("RLS permitio lectura entre empresas")
                db.commit()
            with SessionLocal() as db:
                if list(db.scalars(select(Plant.id))):
                    raise AssertionError("El contexto RLS sobrevivio a la transaccion")
                db.commit()

        with SessionLocal() as db:
            set_database_context(db, "tenant", company_a_id)
            blocked_update = (
                db.execute(
                    update(Plant).where(Plant.id == plant_b_id).values(name="Cross tenant update")
                ).rowcount
                == 0
            )
            blocked_delete = db.execute(delete(Plant).where(Plant.id == plant_b_id)).rowcount == 0
            db.commit()

        with SessionLocal() as db:
            set_database_context(db, "tenant", company_a_id)
            db.add(Plant(company_id=company_b_id, name="Cross tenant insert", code=f"X{suffix}"))
            try:
                db.commit()
            except DBAPIError:
                blocked_insert = True
                db.rollback()

        if not all((blocked_insert, blocked_update, blocked_delete)):
            raise AssertionError("RLS no bloqueo todo el CRUD cruzado")
        return {
            "tenant_read_isolation": True,
            "cross_tenant_insert_blocked": blocked_insert,
            "cross_tenant_update_blocked": blocked_update,
            "cross_tenant_delete_blocked": blocked_delete,
            "pgbouncer_transaction_reuse_cycles": 40,
            "context_reset_after_transaction": True,
        }
    finally:
        if company_a_id and company_b_id:
            with SessionLocal() as db:
                set_database_context(db, "system")
                db.execute(delete(Company).where(Company.id.in_([company_a_id, company_b_id])))
                db.commit()


def validate_redis_and_worker() -> dict:
    redis = get_queue_redis()
    if not redis.ping():
        raise AssertionError("Redis no responde")
    idempotency_key = f"staging-validation:{uuid.uuid4()}"
    job_id = None
    try:
        with SessionLocal() as db:
            set_database_context(db, "system")
            first = enqueue_job(db, "HEALTHCHECK", {"value": "staging"}, idempotency_key)
            second = enqueue_job(db, "HEALTHCHECK", {"value": "ignored"}, idempotency_key)
            if first.id != second.id:
                raise AssertionError("La clave idempotente creo trabajos duplicados")
            job_id = first.id

        deadline = time.monotonic() + 90
        completed = None
        while time.monotonic() < deadline:
            with SessionLocal() as db:
                set_database_context(db, "system")
                completed = db.get(BackgroundJob, job_id)
                if completed and completed.status in {JobStatus.SUCCEEDED, JobStatus.FAILED}:
                    status_value = completed.status
                    attempts = completed.attempts
                    result_summary = completed.result_summary
                    last_error = completed.last_error
                    break
            time.sleep(1)
        else:
            raise AssertionError("El worker no completo el trabajo dentro del plazo")
        if status_value != JobStatus.SUCCEEDED or attempts != 1:
            raise AssertionError(f"El worker fallo: {last_error or status_value.value}")
        if result_summary != "worker:staging":
            raise AssertionError("El worker devolvio un resultado inesperado")
        return {
            "redis_ping": True,
            "worker_roundtrip": True,
            "job_attempts": attempts,
            "idempotency_prevented_duplicate": True,
        }
    finally:
        if job_id:
            with SessionLocal() as db:
                set_database_context(db, "system")
                job = db.get(BackgroundJob, job_id)
                if job:
                    db.delete(job)
                    db.commit()
            queue = Queue(
                settings.job_queue_name,
                connection=redis,
                serializer=JSONSerializer,
            )
            queued = queue.fetch_job(str(job_id))
            if queued:
                queued.delete()


def validate_s3() -> dict:
    storage = get_document_storage()
    if not isinstance(storage, S3StorageService):
        raise AssertionError("STAGING no utiliza almacenamiento S3")
    company_a_id = uuid.uuid4()
    company_b_id = uuid.uuid4()
    asset_id = uuid.uuid4()
    payload = b"ForgeOps STAGING S3 validation\n"
    stored = storage.store(company_a_id, asset_id, "validation.txt", payload, "text/plain")
    try:
        if storage.read(company_a_id, stored.key) != payload:
            raise AssertionError("S3 devolvio contenido distinto")
        target = storage.download(company_a_id, stored.key)
        if not target.signed_url or "X-Amz-Signature" not in target.signed_url:
            raise AssertionError("S3 no genero una descarga firmada")
        cross_tenant_blocked = False
        try:
            storage.read(company_b_id, stored.key)
        except HTTPException as exc:
            cross_tenant_blocked = exc.status_code == 404
        if not cross_tenant_blocked:
            raise AssertionError("S3 permitio leer una clave de otra empresa")
    finally:
        storage.delete(company_a_id, stored.key)

    deleted = False
    try:
        storage.client.head_object(Bucket=storage.bucket, Key=stored.key)
    except ClientError as exc:
        deleted = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode") == 404
    if not deleted:
        raise AssertionError("S3 no elimino el objeto de validacion")
    return {
        "upload_and_read": True,
        "presigned_download": True,
        "cross_tenant_key_blocked": True,
        "delete_confirmed": True,
    }


def main() -> None:
    require_staging()
    results = {
        "schema_and_role": validate_schema_and_role(),
        "rls_and_pgbouncer": validate_rls_and_pool_reuse(),
        "redis_and_worker": validate_redis_and_worker(),
        "s3": validate_s3(),
        "safe_email_backend": settings.email_backend == "development",
    }
    if not results["safe_email_backend"]:
        raise AssertionError("STAGING no utiliza un backend de correo seguro")
    print(json.dumps({"staging_validation": "passed", "checks": results}, sort_keys=True))


if __name__ == "__main__":
    main()
