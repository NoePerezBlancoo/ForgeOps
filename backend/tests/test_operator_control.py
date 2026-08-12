from datetime import UTC, datetime, timedelta

import pyotp
from sqlalchemy import select

from app.auth.security import hash_password
from app.companies.models import Company
from app.core.config import settings
from app.core.enums import CompanyPlan, SubscriptionStatus
from app.operators.models import OperatorAuditEvent, OperatorSession, PlatformOperator
from app.operators.security import encrypt_mfa_secret
from tests.conftest import login

MFA_SECRET = "JBSWY3DPEHPK3PXP"
OPERATOR_EMAIL = "owner@forgeops.local"
OPERATOR_PASSWORD = "OwnerControl123!"


def create_operator(database) -> PlatformOperator:
    operator = PlatformOperator(
        full_name="ForgeOps Owner",
        email=OPERATOR_EMAIL,
        password_hash=hash_password(OPERATOR_PASSWORD),
        password_changed_at=datetime.now(UTC),
        mfa_secret_encrypted=encrypt_mfa_secret(MFA_SECRET),
        mfa_enabled=True,
        active=True,
    )
    database.add(operator)
    database.commit()
    return operator


def operator_login(client) -> dict[str, str]:
    response = client.post(
        "/api/v1/operator-auth/login",
        json={
            "email": OPERATOR_EMAIL,
            "password": OPERATOR_PASSWORD,
            "totp_code": pyotp.TOTP(MFA_SECRET).now(),
        },
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_operator_identity_is_separate_and_can_read_platform(client, database):
    create_operator(database)
    tenant_headers = login(client, "admin@alpha.local", "Admin123!")
    assert client.get("/api/v1/operator/dashboard", headers=tenant_headers).status_code == 401

    headers = operator_login(client)
    assert client.get("/api/v1/companies/current", headers=headers).status_code == 401

    dashboard = client.get("/api/v1/operator/dashboard", headers=headers)
    assert dashboard.status_code == 200
    assert dashboard.json()["total_companies"] == 2
    assert dashboard.json()["active_customers"] == 2
    assert dashboard.json()["active_users"] == 4

    companies = client.get("/api/v1/operator/companies?page_size=5", headers=headers)
    assert companies.status_code == 200
    assert companies.json()["total"] == 2
    alpha = next(item for item in companies.json()["items"] if item["name"] == "Alpha Factory")
    assert alpha["users_count"] == 3
    assert alpha["plants_count"] == 1
    assert alpha["assets_count"] == 1

    refreshed = client.post("/api/v1/operator-auth/refresh", json={})
    assert refreshed.status_code == 200
    assert refreshed.json()["operator"]["email"] == OPERATOR_EMAIL


def test_operator_controls_trial_subscription_and_audit(client, database):
    operator = create_operator(database)
    company = database.scalar(select(Company).where(Company.name == "Alpha Factory"))
    tenant_headers = login(client, "admin@alpha.local", "Admin123!")
    headers = operator_login(client)

    invalid = client.patch(
        f"/api/v1/operator/companies/{company.id}",
        headers=headers,
        json={"subscription_status": "SUSPENDED"},
    )
    assert invalid.status_code == 422

    extended = client.post(
        f"/api/v1/operator/companies/{company.id}/extend-trial",
        headers=headers,
        json={"days": 15, "reason": "Piloto industrial acordado"},
    )
    assert extended.status_code == 200
    assert extended.json()["plan"] == "TRIAL"
    assert extended.json()["subscription_status"] == "TRIAL"
    assert extended.json()["trial_days_remaining"] == 15

    suspended = client.patch(
        f"/api/v1/operator/companies/{company.id}",
        headers=headers,
        json={
            "subscription_status": "SUSPENDED",
            "reason": "Fin temporal del piloto",
        },
    )
    assert suspended.status_code == 200
    assert suspended.json()["access_status"] == "SUSPENDED"
    assert client.get("/api/v1/assets", headers=tenant_headers).status_code == 200
    assert (
        client.post(
            "/api/v1/assets",
            headers=tenant_headers,
            json={},
        ).status_code
        == 402
    )

    deactivated = client.patch(
        f"/api/v1/operator/companies/{company.id}",
        headers=headers,
        json={"active": False, "reason": "Solicitud del responsable de cuenta"},
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["active"] is False
    assert client.get("/api/v1/assets", headers=tenant_headers).status_code == 401

    active_sessions = database.scalars(
        select(OperatorSession).where(OperatorSession.operator_id == operator.id)
    ).all()
    assert active_sessions
    actions = set(database.scalars(select(OperatorAuditEvent.action)))
    assert {"LOGIN", "TRIAL_EXTEND", "COMPANY_UPDATE"}.issubset(actions)


def test_operator_modules_are_normalized_and_company_details_are_limited(client, database):
    create_operator(database)
    headers = operator_login(client)
    company = database.scalar(select(Company).where(Company.name == "Beta Factory"))

    updated = client.patch(
        f"/api/v1/operator/companies/{company.id}",
        headers=headers,
        json={"enabled_modules": ["KNOWLEDGE"]},
    )
    assert updated.status_code == 200
    assert updated.json()["enabled_modules"] == ["DOCUMENTS", "KNOWLEDGE"]
    assert updated.json()["administrators"][0]["email"] == "admin@beta.local"
    assert "password_hash" not in updated.text

    activated = client.patch(
        f"/api/v1/operator/companies/{company.id}",
        headers=headers,
        json={"subscription_status": "ACTIVE"},
    )
    assert activated.status_code == 200
    assert activated.json()["plan"] == "PROFESSIONAL"


def test_operator_mfa_replay_and_lockout_are_rejected(client, database):
    operator = create_operator(database)
    code = pyotp.TOTP(MFA_SECRET).now()
    first = client.post(
        "/api/v1/operator-auth/login",
        json={"email": OPERATOR_EMAIL, "password": OPERATOR_PASSWORD, "totp_code": code},
    )
    assert first.status_code == 200
    replay = client.post(
        "/api/v1/operator-auth/login",
        json={"email": OPERATOR_EMAIL, "password": OPERATOR_PASSWORD, "totp_code": code},
    )
    assert replay.status_code == 401

    operator.last_mfa_counter = None
    operator.failed_login_attempts = 0
    operator.locked_until = None
    database.commit()
    wrong_code = "000000" if code != "000000" else "999999"
    for _ in range(settings.operator_lockout_attempts):
        response = client.post(
            "/api/v1/operator-auth/login",
            json={
                "email": OPERATOR_EMAIL,
                "password": OPERATOR_PASSWORD,
                "totp_code": wrong_code,
            },
        )
        assert response.status_code == 401
    locked = client.post(
        "/api/v1/operator-auth/login",
        json={"email": OPERATOR_EMAIL, "password": OPERATOR_PASSWORD, "totp_code": code},
    )
    assert locked.status_code == 429


def test_operator_dashboard_classifies_expired_trials(client, database):
    create_operator(database)
    company = database.scalar(select(Company).where(Company.name == "Beta Factory"))
    company.plan = CompanyPlan.TRIAL
    company.subscription_status = SubscriptionStatus.TRIAL
    company.trial_started_at = datetime.now(UTC) - timedelta(days=40)
    company.trial_ends_at = datetime.now(UTC) - timedelta(days=10)
    database.commit()

    headers = operator_login(client)
    dashboard = client.get("/api/v1/operator/dashboard", headers=headers).json()
    assert dashboard["expired_trials"] == 1
    assert dashboard["active_customers"] == 1
    expired = client.get(
        "/api/v1/operator/companies?access_status=EXPIRED&page_size=5", headers=headers
    )
    assert expired.status_code == 200
    assert expired.json()["total"] == 1
