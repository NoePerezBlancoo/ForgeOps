import re
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.assets.models import Asset
from app.companies.models import Company
from app.core.crypto import decrypt_json
from app.core.enums import NotificationType, UserRole
from app.invitations.models import UserInvitation
from app.invitations.schemas import UserInvitationRead
from app.jobs.models import BackgroundJob
from app.notifications.models import Notification
from app.users.models import User
from tests.conftest import login


def test_invitation_models_expose_safe_contracts_and_constraints():
    now = datetime.now(UTC)
    invitation = UserInvitation(
        id=uuid.uuid4(),
        company_id=uuid.uuid4(),
        email=" New.Tech@Example.COM ",
        full_name="New Technician",
        role=UserRole.TECHNICIAN,
        token_hash="a" * 64,
        expires_at=now + timedelta(hours=1),
        created_at=now,
        updated_at=now,
    )
    assert invitation.email == "new.tech@example.com"
    assert invitation.status == "PENDING"
    invitation.expires_at = now - timedelta(seconds=1)
    assert invitation.status == "EXPIRED"
    invitation.accepted_at = now
    assert invitation.status == "ACCEPTED"
    invitation.revoked_at = now
    assert invitation.status == "REVOKED"

    serialized = UserInvitationRead.model_validate(invitation).model_dump()
    assert "token_hash" not in serialized
    assert serialized["role"] == UserRole.TECHNICIAN

    invitation_constraints = {
        constraint.name for constraint in UserInvitation.__table__.constraints
    }
    notification_constraints = {
        constraint.name for constraint in Notification.__table__.constraints
    }
    assert "uq_user_invitations_token_hash" in invitation_constraints
    assert "uq_notifications_recipient_dedupe" in notification_constraints
    dedupe = next(
        constraint
        for constraint in Notification.__table__.constraints
        if constraint.name == "uq_notifications_recipient_dedupe"
    )
    assert [column.name for column in dedupe.columns] == [
        "company_id",
        "recipient_id",
        "dedupe_key",
    ]


def test_employee_invitation_is_single_use_and_never_persists_plain_token(
    client,
    database,
):
    admin_headers = login(client, "admin@alpha.local", "Admin123!")
    created = client.post(
        "/api/v1/invitations",
        headers=admin_headers,
        json={
            "email": " invited.tech@alpha.local ",
            "full_name": "Invited Technician",
            "job_title": "Electromechanical Technician",
            "phone": "+34 600 100 200",
            "role": "TECHNICIAN",
        },
    )
    assert created.status_code == 201
    assert created.json()["email"] == "invited.tech@alpha.local"
    assert created.json()["status"] == "PENDING"
    assert "token" not in created.json()

    invitation = database.scalar(
        select(UserInvitation).where(UserInvitation.email == "invited.tech@alpha.local")
    )
    job = database.scalar(
        select(BackgroundJob).where(BackgroundJob.job_type == "EMAIL_SEND")
    )
    payload = decrypt_json(job.payload_encrypted)
    raw_token = re.search(r"token=([^\s.]+)", payload["text_body"]).group(1)
    assert raw_token not in invitation.token_hash
    assert raw_token not in job.payload_encrypted
    assert payload["template"] == "user_invitation"

    preview = client.post("/api/v1/invitations/preview", json={"token": raw_token})
    assert preview.status_code == 200
    assert preview.json()["company_name"] == "Alpha Factory"
    assert preview.json()["email"] == "invited.tech@alpha.local"

    accepted = client.post(
        "/api/v1/invitations/accept",
        json={"token": raw_token, "password": "InvitedSecure123!"},
    )
    assert accepted.status_code == 200
    assert client.post(
        "/api/v1/invitations/accept",
        json={"token": raw_token, "password": "AnotherSecure123!"},
    ).status_code == 422
    assert client.post(
        "/api/v1/auth/login",
        json={"email": "invited.tech@alpha.local", "password": "InvitedSecure123!"},
    ).status_code == 200

    database.refresh(invitation)
    assert invitation.accepted_at is not None
    user = database.scalar(
        select(User).where(User.email == "invited.tech@alpha.local")
    )
    assert invitation.accepted_user_id == user.id
    assert user.job_title == "Electromechanical Technician"


def test_invitation_permissions_revocation_and_pending_seat_limit(client, database):
    admin_headers = login(client, "admin@alpha.local", "Admin123!")
    viewer_headers = login(client, "viewer@alpha.local", "Viewer123!")
    assert client.post(
        "/api/v1/invitations",
        headers=viewer_headers,
        json={
            "email": "forbidden@alpha.local",
            "full_name": "Forbidden User",
            "role": "VIEWER",
        },
    ).status_code == 403

    company = database.scalar(select(Company).where(Company.name == "Alpha Factory"))
    company.limit_overrides = {"users": 4}
    database.commit()
    first = client.post(
        "/api/v1/invitations",
        headers=admin_headers,
        json={
            "email": "reserved@alpha.local",
            "full_name": "Reserved Seat",
            "role": "VIEWER",
        },
    )
    assert first.status_code == 201
    resent = client.post(
        f"/api/v1/invitations/{first.json()['id']}/resend",
        headers=admin_headers,
    )
    assert resent.status_code == 200
    assert resent.json()["id"] != first.json()["id"]
    assert client.post(
        "/api/v1/invitations",
        headers=admin_headers,
        json={
            "email": "over-limit@alpha.local",
            "full_name": "Over Limit",
            "role": "VIEWER",
        },
    ).status_code == 409

    revoked = client.post(
        f"/api/v1/invitations/{resent.json()['id']}/revoke",
        headers=admin_headers,
    )
    assert revoked.status_code == 200
    assert revoked.json()["status"] == "REVOKED"
    replacement = client.post(
        "/api/v1/invitations",
        headers=admin_headers,
        json={
            "email": "over-limit@alpha.local",
            "full_name": "Available Seat",
            "role": "VIEWER",
        },
    )
    assert replacement.status_code == 201
    assert client.post(
        f"/api/v1/invitations/{first.json()['id']}/resend",
        headers=admin_headers,
    ).status_code == 409


def test_domain_notifications_are_recipient_scoped_and_acknowledgeable(client, database):
    admin_headers = login(client, "admin@alpha.local", "Admin123!")
    technician = database.scalar(select(User).where(User.email == "tech@alpha.local"))
    asset = database.scalar(select(Asset).where(Asset.code == "A-001"))
    order = client.post(
        "/api/v1/work-orders",
        headers=admin_headers,
        json={
            "plant_id": str(asset.plant_id),
            "asset_id": str(asset.id),
            "assigned_to": str(technician.id),
            "title": "Inspect critical drive bearing",
            "description": "Inspect vibration and temperature before restarting production.",
            "type": "CORRECTIVE",
            "priority": "HIGH",
        },
    )
    assert order.status_code == 201

    technician_headers = login(client, "tech@alpha.local", "Tech123!")
    inbox = client.get("/api/v1/notifications", headers=technician_headers)
    assert inbox.status_code == 200
    assert inbox.json()["unread"] == 1
    assignment = inbox.json()["items"][0]
    assert assignment["type"] == NotificationType.WORK_ORDER_ASSIGNED
    assert order.json()["number"] in assignment["title"]

    beta_headers = login(client, "admin@beta.local", "Admin123!")
    assert client.patch(
        f"/api/v1/notifications/{assignment['id']}/read",
        headers=beta_headers,
    ).status_code == 404
    marked = client.patch(
        f"/api/v1/notifications/{assignment['id']}/read",
        headers=technician_headers,
    )
    assert marked.status_code == 200
    assert marked.json()["read_at"] is not None

    critical = client.post(
        "/api/v1/incidents",
        headers=admin_headers,
        json={
            "plant_id": str(asset.plant_id),
            "asset_id": str(asset.id),
            "title": "Production line stopped",
            "description": "The main drive stopped unexpectedly during the production cycle.",
            "priority": "CRITICAL",
        },
    )
    assert critical.status_code == 201
    admin_inbox = client.get("/api/v1/notifications", headers=admin_headers)
    assert admin_inbox.status_code == 200
    assert admin_inbox.json()["items"][0]["type"] == NotificationType.CRITICAL_INCIDENT
    assert client.post(
        "/api/v1/notifications/read-all",
        headers=admin_headers,
    ).json()["updated"] == 1
