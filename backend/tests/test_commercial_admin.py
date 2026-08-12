from uuid import UUID

from sqlalchemy import func, select

from app.assets.models import Asset
from app.audit.models import AuditEvent
from app.auth.models import RefreshSession
from app.core.enums import AssetStatus, Criticality
from app.plants.models import Plant
from app.users.models import User
from tests.conftest import login


def test_company_and_plant_administration_is_audited_and_tenant_scoped(client, database):
    alpha_headers = login(client, "admin@alpha.local", "Admin123!")
    viewer_headers = login(client, "viewer@alpha.local", "Viewer123!")

    denied = client.patch(
        "/api/v1/companies/current",
        headers=viewer_headers,
        json={"industry": "Metal"},
    )
    assert denied.status_code == 403

    company = client.patch(
        "/api/v1/companies/current",
        headers=alpha_headers,
        json={
            "industry": "Metal",
            "timezone": "Europe/Madrid",
            "work_order_prefix": "MW",
        },
    )
    assert company.status_code == 200
    assert company.json()["industry"] == "Metal"
    assert company.json()["work_order_prefix"] == "MW"

    created = client.post(
        "/api/v1/plants",
        headers=alpha_headers,
        json={"name": "North Plant", "code": "north", "address": "Industrial Park"},
    )
    assert created.status_code == 201
    assert created.json()["code"] == "NORTH"

    duplicate = client.post(
        "/api/v1/plants",
        headers=alpha_headers,
        json={"name": "Duplicate", "code": "NORTH"},
    )
    assert duplicate.status_code == 409

    beta_headers = login(client, "admin@beta.local", "Admin123!")
    hidden = client.get(f"/api/v1/plants/{created.json()['id']}", headers=beta_headers)
    assert hidden.status_code == 404

    event_actions = set(
        database.scalars(
            select(AuditEvent.action).where(
                AuditEvent.company_id == UUID(company.json()["id"])
            )
        )
    )
    assert {"LOGIN", "UPDATE", "CREATE"}.issubset(event_actions)


def test_plant_with_assets_cannot_be_deactivated_and_dashboard_filters_by_plant(
    client, database
):
    headers = login(client, "admin@alpha.local", "Admin123!")
    first_asset = client.get("/api/v1/assets", headers=headers).json()[0]
    blocked = client.patch(
        f"/api/v1/plants/{first_asset['plant_id']}",
        headers=headers,
        json={"active": False},
    )
    assert blocked.status_code == 409

    company_id = UUID(first_asset["company_id"])
    second_plant = Plant(company_id=company_id, name="Second Plant", code="SECOND")
    database.add(second_plant)
    database.flush()
    database.add(
        Asset(
            company_id=company_id,
            plant_id=second_plant.id,
            code="A-SECOND",
            name="Second Machine",
            status=AssetStatus.ACTIVE,
            criticality=Criticality.MEDIUM,
        )
    )
    database.commit()

    full_dashboard = client.get("/api/v1/dashboard", headers=headers)
    scoped_dashboard = client.get(
        f"/api/v1/dashboard?plant_id={second_plant.id}", headers=headers
    )
    assert full_dashboard.status_code == 200
    assert scoped_dashboard.status_code == 200
    assert full_dashboard.json()["active_assets"] == 2
    assert scoped_dashboard.json()["active_assets"] == 1
    scoped_assets = client.get(f"/api/v1/assets?plant_id={second_plant.id}", headers=headers)
    assert len(scoped_assets.json()) == 1


def test_user_lifecycle_protects_last_admin_and_revokes_sessions(client, database):
    headers = login(client, "admin@alpha.local", "Admin123!")
    current = client.get("/api/v1/auth/me", headers=headers).json()

    last_admin = client.patch(
        f"/api/v1/users/{current['id']}",
        headers=headers,
        json={"role": "MAINTENANCE_MANAGER"},
    )
    assert last_admin.status_code == 409

    created = client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "full_name": "Commercial Admin",
            "email": "commercial@alpha.local",
            "password": "Commercial123!",
            "role": "ADMIN",
            "job_title": "Plant Manager",
        },
    )
    assert created.status_code == 201
    user_id = created.json()["id"]

    login(client, "commercial@alpha.local", "Commercial123!")
    user_uuid = database.scalar(select(User.id).where(User.email == "commercial@alpha.local"))
    assert database.scalar(
        select(func.count(RefreshSession.id)).where(
            RefreshSession.user_id == user_uuid,
            RefreshSession.revoked_at.is_(None),
        )
    ) == 1

    reset = client.post(
        f"/api/v1/users/{user_id}/password",
        headers=headers,
        json={"password": "Replacement123!"},
    )
    assert reset.status_code == 200
    assert database.scalar(
        select(func.count(RefreshSession.id)).where(
            RefreshSession.user_id == user_uuid,
            RefreshSession.revoked_at.is_(None),
        )
    ) == 0

    old_login = client.post(
        "/api/v1/auth/login",
        json={"email": "commercial@alpha.local", "password": "Commercial123!"},
    )
    new_login = client.post(
        "/api/v1/auth/login",
        json={"email": "commercial@alpha.local", "password": "Replacement123!"},
    )
    assert old_login.status_code == 401
    assert new_login.status_code == 200


def test_viewer_cannot_manage_users_or_read_audit(client):
    headers = login(client, "viewer@alpha.local", "Viewer123!")
    options = client.get("/api/v1/users/options", headers=headers)
    detailed = client.get("/api/v1/users", headers=headers)
    denied_user = client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "full_name": "Forbidden User",
            "email": "forbidden@alpha.local",
            "password": "Forbidden123!",
            "role": "VIEWER",
        },
    )
    denied_audit = client.get("/api/v1/audit-events", headers=headers)
    assert options.status_code == 200
    assert "last_login_at" not in options.json()[0]
    assert detailed.status_code == 403
    assert denied_user.status_code == 403
    assert denied_audit.status_code == 403
