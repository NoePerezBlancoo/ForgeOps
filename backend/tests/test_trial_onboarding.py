from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.companies.models import Company
from app.core.config import settings
from app.core.enums import CompanyPlan, SubscriptionStatus
from app.users.models import User
from tests.conftest import login


def trial_payload(email: str = "owner@trial.example") -> dict:
    return {
        "company_name": "Trial Industries",
        "industry": "Automocion",
        "plant_name": "Planta Norte",
        "full_name": "Maria Operaciones",
        "email": email,
        "password": "SecureTrial123!",
        "sample_data": True,
        "terms_accepted": True,
    }


def test_trial_registration_creates_isolated_ready_workspace(client, database):
    response = client.post("/api/v1/auth/register-trial", json=trial_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["access_token"]
    assert response.cookies.get("forgeops_refresh")
    assert body["user"]["role"] == "ADMIN"
    assert body["user"]["company"]["plan"] == "TRIAL"
    assert body["user"]["company"]["access_status"] == "TRIAL"
    assert body["user"]["company"]["trial_days_remaining"] == settings.trial_days
    assert set(body["user"]["company"]["enabled_modules"]) == {
        "PREVENTIVE",
        "INVENTORY",
        "DOCUMENTS",
        "KNOWLEDGE",
    }

    headers = {"Authorization": f"Bearer {body['access_token']}"}
    assert len(client.get("/api/v1/assets", headers=headers).json()) == 3
    assert len(client.get("/api/v1/incidents", headers=headers).json()) == 1
    assert len(client.get("/api/v1/work-orders", headers=headers).json()) == 2

    company = database.scalar(select(Company).where(Company.name == "Trial Industries"))
    assert company
    assert company.tax_id is None
    assert company.plan == CompanyPlan.TRIAL
    assert company.trial_ends_at - company.trial_started_at == timedelta(days=settings.trial_days)


def test_trial_registration_rejects_duplicate_email_and_missing_consent(client):
    assert client.post("/api/v1/auth/register-trial", json=trial_payload()).status_code == 201
    duplicate = client.post("/api/v1/auth/register-trial", json=trial_payload())
    assert duplicate.status_code == 409

    without_consent = trial_payload("other@trial.example")
    without_consent["terms_accepted"] = False
    assert client.post("/api/v1/auth/register-trial", json=without_consent).status_code == 422


def test_trial_registration_can_be_disabled(client, monkeypatch):
    monkeypatch.setattr(settings, "trial_signup_enabled", False)
    response = client.post("/api/v1/auth/register-trial", json=trial_payload())
    assert response.status_code == 503


def test_expired_trial_is_read_only_but_can_sign_in(client, database):
    company = database.scalar(select(Company).where(Company.tax_id == "A00000001"))
    company.plan = CompanyPlan.TRIAL
    company.subscription_status = SubscriptionStatus.TRIAL
    company.trial_started_at = datetime.now(UTC) - timedelta(days=31)
    company.trial_ends_at = datetime.now(UTC) - timedelta(days=1)
    database.commit()

    headers = login(client, "admin@alpha.local", "Admin123!")
    assert client.get("/api/v1/assets", headers=headers).status_code == 200
    blocked = client.post("/api/v1/assets", headers=headers, json={})
    assert blocked.status_code == 402
    assert "prueba ha finalizado" in blocked.json()["detail"]
    assert client.post("/api/v1/notifications/read-all", headers=headers).status_code == 200
    assert client.post(
        "/api/v1/invitations",
        headers=headers,
        json={
            "email": "blocked@alpha.local",
            "full_name": "Blocked Invitation",
            "role": "VIEWER",
        },
    ).status_code == 402


def test_admin_can_configure_modules_and_dependencies(client):
    headers = login(client, "admin@alpha.local", "Admin123!")

    response = client.patch(
        "/api/v1/companies/current/modules",
        headers=headers,
        json={"enabled_modules": ["INVENTORY"]},
    )
    assert response.status_code == 200
    assert response.json()["enabled_modules"] == ["INVENTORY"]
    assert client.get("/api/v1/inventory", headers=headers).status_code == 200
    assert client.get("/api/v1/preventive-maintenance", headers=headers).status_code == 403

    response = client.patch(
        "/api/v1/companies/current/modules",
        headers=headers,
        json={"enabled_modules": ["KNOWLEDGE"]},
    )
    assert response.status_code == 200
    assert response.json()["enabled_modules"] == ["DOCUMENTS", "KNOWLEDGE"]


def test_non_admin_cannot_configure_modules(client):
    headers = login(client, "viewer@alpha.local", "Viewer123!")
    response = client.patch(
        "/api/v1/companies/current/modules",
        headers=headers,
        json={"enabled_modules": []},
    )
    assert response.status_code == 403


def test_onboarding_tracks_automatic_and_manual_steps(client, database):
    headers = login(client, "admin@alpha.local", "Admin123!")
    initial = client.get("/api/v1/onboarding", headers=headers)
    assert initial.status_code == 200
    assert any(step["key"] == "ASSET" and step["complete"] for step in initial.json()["steps"])
    assert any(
        step["key"] == "WELCOME" and not step["complete"]
        for step in initial.json()["steps"]
    )

    updated = client.patch(
        "/api/v1/onboarding",
        headers=headers,
        json={"completed_step": "WELCOME", "tour_completed": True},
    )
    assert updated.status_code == 200
    assert updated.json()["tour_completed"] is True
    assert any(
        step["key"] == "WELCOME" and step["complete"]
        for step in updated.json()["steps"]
    )

    invalid = client.patch(
        "/api/v1/onboarding",
        headers=headers,
        json={"completed_step": "ASSET"},
    )
    assert invalid.status_code == 422
    user = database.scalar(select(User).where(User.email == "admin@alpha.local"))
    assert user
