import uuid
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import func, select

from app.auth.models import PasswordResetToken
from app.core.config import Settings
from app.core.crypto import decrypt_json
from app.documents.storage import LocalStorageService
from app.jobs.models import BackgroundJob
from app.jobs.service import enqueue_job
from tests.conftest import login


def test_production_configuration_rejects_insecure_defaults():
    with pytest.raises(ValidationError) as error:
        Settings(app_env="production")
    message = str(error.value)
    assert "Configuracion de produccion insegura" in message
    assert "STORAGE_BACKEND debe ser s3" in message
    assert "COOKIE_SECURE debe estar activo" in message


def test_local_storage_validates_signature_and_tenant_boundary(tmp_path):
    storage = LocalStorageService(tmp_path)
    company_id = uuid.uuid4()
    asset_id = uuid.uuid4()
    stored = storage.store(
        company_id,
        asset_id,
        "../manual.txt",
        b"Procedimiento industrial controlado",
        "text/plain",
    )
    assert stored.original_name == "manual.txt"
    assert stored.key.startswith(f"companies/{company_id}/assets/{asset_id}/documents/")
    assert storage.read(company_id, stored.key) == b"Procedimiento industrial controlado"

    with pytest.raises(HTTPException) as wrong_tenant:
        storage.read(uuid.uuid4(), stored.key)
    assert wrong_tenant.value.status_code == 404

    with pytest.raises(HTTPException) as invalid_signature:
        storage.store(company_id, asset_id, "evidence.png", b"not-png", "image/png")
    assert invalid_signature.value.status_code == 422


def test_jobs_are_idempotent_and_payload_is_encrypted(database):
    payload = {"recipient": "admin@alpha.local", "token": "sensitive-value"}
    first = enqueue_job(database, "EMAIL_SEND", payload, "email:test:one")
    second = enqueue_job(database, "EMAIL_SEND", payload, "email:test:one")
    assert first.id == second.id
    assert database.scalar(select(func.count(BackgroundJob.id))) == 1
    assert "sensitive-value" not in first.payload_encrypted
    assert decrypt_json(first.payload_encrypted) == payload


def test_password_reset_is_generic_single_use_and_revokes_sessions(client, database):
    old_headers = login(client, "admin@alpha.local", "Admin123!")
    requested = client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "admin@alpha.local"},
    )
    assert requested.status_code == 202
    assert "Si la cuenta existe" in requested.json()["message"]

    reset = database.scalar(select(PasswordResetToken))
    job = database.scalar(select(BackgroundJob).where(BackgroundJob.job_type == "EMAIL_SEND"))
    payload = decrypt_json(job.payload_encrypted)
    reset_url = payload["text_body"].rsplit(" ", 1)[-1]
    token = parse_qs(urlparse(reset_url).query)["token"][0]
    assert reset.token_hash != token

    confirmed = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": token, "password": "NewSecure123!"},
    )
    assert confirmed.status_code == 200
    repeated = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": token, "password": "AnotherSecure123!"},
    )
    assert repeated.status_code == 422
    assert client.get("/api/v1/auth/me", headers=old_headers).status_code == 200
    assert client.post(
        "/api/v1/auth/login",
        json={"email": "admin@alpha.local", "password": "Admin123!"},
    ).status_code == 401
    assert client.post(
        "/api/v1/auth/login",
        json={"email": "admin@alpha.local", "password": "NewSecure123!"},
    ).status_code == 200


def test_password_reset_does_not_disclose_unknown_accounts(client, database):
    response = client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "unknown@example.com"},
    )
    assert response.status_code == 202
    assert database.scalar(select(func.count(PasswordResetToken.id))) == 0
