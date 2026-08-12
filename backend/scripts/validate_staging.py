import json
import os
import secrets
import time
import uuid

import httpx
import pyotp
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
from app.auth.security import hash_password
from app.companies.models import Company
from app.core.config import settings
from app.core.database import SessionLocal, engine, set_database_context
from app.core.enums import JobStatus, UserRole
from app.core.redis import get_queue_redis
from app.documents.storage import S3StorageService, get_document_storage
from app.jobs.models import BackgroundJob
from app.jobs.service import enqueue_job
from app.operators.models import OperatorAuditEvent, PlatformOperator
from app.operators.security import encrypt_mfa_secret, generate_mfa_secret
from app.plants.models import Plant
from app.users.models import User


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


def _assert_cookie(response: httpx.Response, name: str, same_site: str) -> None:
    header = response.headers.get("set-cookie", "")
    required = (name, "HttpOnly", "Secure", f"SameSite={same_site}")
    if not all(value.lower() in header.lower() for value in required):
        raise AssertionError(f"La cookie {name} no incluye todos los atributos seguros")
    if "domain=" in header.lower():
        raise AssertionError(f"La cookie {name} no es host-only")


def validate_http_tenancy_and_auth() -> dict:
    suffix = uuid.uuid4().hex[:10]
    password = f"Staging-{secrets.token_urlsafe(18)}!9a"
    company_a_id = company_b_id = plant_a_id = None
    try:
        with SessionLocal() as db:
            set_database_context(db, "system")
            company_a = Company(name=f"HTTP Tenant A {suffix}", tax_id=f"HT-A-{suffix}")
            company_b = Company(name=f"HTTP Tenant B {suffix}", tax_id=f"HT-B-{suffix}")
            db.add_all([company_a, company_b])
            db.flush()
            plant_a = Plant(company_id=company_a.id, name="HTTP Plant A", code=f"HA{suffix}")
            plant_b = Plant(company_id=company_b.id, name="HTTP Plant B", code=f"HB{suffix}")
            user_a = User(
                company_id=company_a.id,
                full_name="HTTP Admin A",
                email=f"http-a-{suffix}@forgeops.local",
                password_hash=hash_password(password),
                role=UserRole.ADMIN,
                active=True,
            )
            user_b = User(
                company_id=company_b.id,
                full_name="HTTP Admin B",
                email=f"http-b-{suffix}@forgeops.local",
                password_hash=hash_password(password),
                role=UserRole.ADMIN,
                active=True,
            )
            db.add_all([plant_a, plant_b, user_a, user_b])
            db.commit()
            company_a_id, company_b_id = company_a.id, company_b.id
            plant_a_id = plant_a.id
            email_a, email_b = user_a.email, user_b.email

        origin = settings.frontend_url.rstrip("/")
        with httpx.Client(base_url=settings.api_url, timeout=20) as client_a, httpx.Client(
            base_url=settings.api_url, timeout=20
        ) as client_b:
            login_a = client_a.post(
                f"{settings.api_prefix}/auth/login",
                json={"email": email_a, "password": password},
                headers={"Origin": origin, "X-Request-ID": "staging-http-a"},
            )
            login_b = client_b.post(
                f"{settings.api_prefix}/auth/login",
                json={"email": email_b, "password": password},
                headers={"Origin": origin, "X-Request-ID": "staging-http-b"},
            )
            if login_a.status_code != 200 or login_b.status_code != 200:
                raise AssertionError("El login HTTP de los tenants sinteticos fallo")
            _assert_cookie(login_a, "forgeops_refresh", "None")
            _assert_cookie(login_b, "forgeops_refresh", "None")
            token_a = login_a.json()["access_token"]
            token_b = login_b.json()["access_token"]
            headers_a = {"Authorization": f"Bearer {token_a}", "Origin": origin}
            headers_b = {"Authorization": f"Bearer {token_b}", "Origin": origin}

            asset = client_a.post(
                f"{settings.api_prefix}/assets",
                headers=headers_a,
                json={
                    "plant_id": str(plant_a_id),
                    "code": f"HTTP-{suffix}",
                    "name": "HTTP isolation asset",
                    "status": "ACTIVE",
                    "criticality": "HIGH",
                },
            )
            if asset.status_code != 201:
                raise AssertionError("No se pudo crear el activo HTTP sintetico")
            asset_id = asset.json()["id"]
            own_asset = client_a.get(
                f"{settings.api_prefix}/assets/{asset_id}", headers=headers_a
            )
            if own_asset.status_code != 200:
                raise AssertionError("El tenant propietario no puede leer su activo")
            blocked_statuses = {
                client_b.get(
                    f"{settings.api_prefix}/assets/{asset_id}", headers=headers_b
                ).status_code,
                client_b.patch(
                    f"{settings.api_prefix}/assets/{asset_id}",
                    headers=headers_b,
                    json={"name": "Cross tenant HTTP update"},
                ).status_code,
                client_b.post(
                    f"{settings.api_prefix}/assets",
                    headers=headers_b,
                    json={
                        "plant_id": str(plant_a_id),
                        "code": f"CROSS-{suffix}",
                        "name": "Cross tenant HTTP insert",
                        "status": "ACTIVE",
                        "criticality": "LOW",
                    },
                ).status_code,
            }
            if blocked_statuses != {404}:
                raise AssertionError(f"IDOR HTTP no quedo oculto: {sorted(blocked_statuses)}")
            tenant_b_assets = client_b.get(
                f"{settings.api_prefix}/assets", headers=headers_b
            ).json()
            if tenant_b_assets:
                raise AssertionError("El listado HTTP filtro datos de otra empresa")

            refresh = client_a.post(f"{settings.api_prefix}/auth/refresh", json={})
            if refresh.status_code != 200:
                raise AssertionError("La rotacion de refresh cookie fallo")
            _assert_cookie(refresh, "forgeops_refresh", "None")
            unauthenticated = httpx.get(
                f"{settings.api_url}{settings.api_prefix}/assets/{asset_id}", timeout=20
            )
            if unauthenticated.status_code != 401:
                raise AssertionError("Un activo fue accesible sin autenticacion")

            preflight = httpx.options(
                f"{settings.api_url}{settings.api_prefix}/assets",
                headers={
                    "Origin": origin,
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "authorization,content-type",
                },
                timeout=20,
            )
            rejected_origin = httpx.options(
                f"{settings.api_url}{settings.api_prefix}/assets",
                headers={
                    "Origin": "https://untrusted.invalid",
                    "Access-Control-Request-Method": "GET",
                },
                timeout=20,
            )
            if (
                preflight.status_code != 200
                or preflight.headers.get("access-control-allow-origin") != origin
                or preflight.headers.get("access-control-allow-credentials") != "true"
                or rejected_origin.headers.get("access-control-allow-origin")
            ):
                raise AssertionError("La politica CORS no es estricta")
            security_headers = {
                "strict-transport-security": "max-age=31536000; includeSubDomains",
                "x-content-type-options": "nosniff",
                "x-frame-options": "DENY",
                "content-security-policy": "frame-ancestors 'none'",
            }
            if any(login_a.headers.get(key) != value for key, value in security_headers.items()):
                raise AssertionError("Faltan cabeceras de seguridad HTTP")
            if login_a.headers.get("x-request-id") != "staging-http-a":
                raise AssertionError("No se preservo el identificador de peticion")
            if httpx.get(f"{settings.api_url}/docs", timeout=20).status_code != 404:
                raise AssertionError("La documentacion API esta expuesta en STAGING")

        return {
            "login_and_refresh_rotation": True,
            "secure_host_only_cookie": True,
            "http_idor_read_update_insert_blocked": True,
            "unauthenticated_access_blocked": True,
            "cors_origin_allowlist": True,
            "security_headers": True,
            "request_correlation": True,
            "api_docs_disabled": True,
        }
    finally:
        if company_a_id and company_b_id:
            with SessionLocal() as db:
                set_database_context(db, "system")
                db.execute(delete(Company).where(Company.id.in_([company_a_id, company_b_id])))
                db.commit()


def validate_operator_control() -> dict:
    suffix = uuid.uuid4().hex[:10]
    email = f"operator-{suffix}@forgeops.local"
    password = f"Operator-{secrets.token_urlsafe(18)}!7z"
    mfa_secret = generate_mfa_secret()
    operator_id = None
    try:
        with SessionLocal() as db:
            set_database_context(db, "system")
            operator = PlatformOperator(
                full_name="STAGING Validation Operator",
                email=email,
                password_hash=hash_password(password),
                mfa_secret_encrypted=encrypt_mfa_secret(mfa_secret),
                mfa_enabled=True,
                active=True,
            )
            db.add(operator)
            db.commit()
            operator_id = operator.id

        endpoint = f"{settings.api_url}{settings.api_prefix}/operator-auth/login"
        invalid = httpx.post(
            endpoint,
            json={"email": email, "password": password, "totp_code": "000000"},
            timeout=20,
        )
        if invalid.status_code != 401:
            raise AssertionError("El acceso de operador acepto un TOTP incorrecto")
        totp_code = pyotp.TOTP(mfa_secret).now()
        login = httpx.post(
            endpoint,
            json={"email": email, "password": password, "totp_code": totp_code},
            timeout=20,
        )
        if login.status_code != 200:
            raise AssertionError("El acceso MFA del operador fallo")
        _assert_cookie(login, "forgeops_operator_refresh", "Strict")
        operator_token = login.json()["access_token"]
        operator_headers = {"Authorization": f"Bearer {operator_token}"}
        dashboard = httpx.get(
            f"{settings.api_url}{settings.api_prefix}/operator/dashboard",
            headers=operator_headers,
            timeout=20,
        )
        if dashboard.status_code != 200 or dashboard.json().get("environment") != "staging":
            raise AssertionError("El panel de operador no responde con el entorno STAGING")
        user_endpoint = httpx.get(
            f"{settings.api_url}{settings.api_prefix}/auth/me",
            headers=operator_headers,
            timeout=20,
        )
        replay = httpx.post(
            endpoint,
            json={"email": email, "password": password, "totp_code": totp_code},
            timeout=20,
        )
        if user_endpoint.status_code != 401 or replay.status_code != 401:
            raise AssertionError("La separacion de actores o el anti-replay MFA fallo")
        return {
            "invalid_totp_rejected": True,
            "valid_totp_login": True,
            "totp_replay_rejected": True,
            "operator_cookie_strict": True,
            "operator_dashboard": True,
            "operator_token_rejected_by_tenant_api": True,
        }
    finally:
        if operator_id:
            with SessionLocal() as db:
                set_database_context(db, "system")
                db.execute(
                    delete(OperatorAuditEvent).where(
                        (OperatorAuditEvent.operator_id == operator_id)
                        | (OperatorAuditEvent.target_id == operator_id)
                    )
                )
                operator = db.get(PlatformOperator, operator_id)
                if operator:
                    db.delete(operator)
                db.commit()


def main() -> None:
    require_staging()
    results = {
        "schema_and_role": validate_schema_and_role(),
        "rls_and_pgbouncer": validate_rls_and_pool_reuse(),
        "redis_and_worker": validate_redis_and_worker(),
        "s3": validate_s3(),
        "http_tenancy_and_auth": validate_http_tenancy_and_auth(),
        "operator_control": validate_operator_control(),
        "safe_email_backend": settings.email_backend == "development",
    }
    if not results["safe_email_backend"]:
        raise AssertionError("STAGING no utiliza un backend de correo seguro")
    print(json.dumps({"staging_validation": "passed", "checks": results}, sort_keys=True))


if __name__ == "__main__":
    main()
