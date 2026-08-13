import uuid

from sqlalchemy import select

from app.assets.models import Asset
from app.auth.security import hash_password
from app.core.enums import UserRole
from app.users.models import User
from app.work_orders.models import WorkOrderEvent
from tests.conftest import login


def create_assigned_order(client, database):
    headers = login(client, "admin@alpha.local", "Admin123!")
    asset = database.scalar(select(Asset).where(Asset.code == "A-001"))
    technician = database.scalar(select(User).where(User.email == "tech@alpha.local"))
    response = client.post(
        "/api/v1/work-orders",
        headers=headers,
        json={
            "plant_id": str(asset.plant_id),
            "asset_id": str(asset.id),
            "assigned_to": str(technician.id),
            "title": "Replace spindle bearing",
            "description": "Replace the damaged spindle bearing and verify vibration levels.",
            "type": "CORRECTIVE",
            "priority": "CRITICAL",
            "estimated_duration": 120,
        },
    )
    assert response.status_code == 201
    return response.json(), headers, technician


def test_multi_technician_intervention_lifecycle(client, database):
    order, admin_headers, lead = create_assigned_order(client, database)
    company_id = lead.company_id
    second = User(
        company_id=company_id,
        full_name="Second Alpha Tech",
        email="tech2@alpha.local",
        password_hash=hash_password("TechTwo123!"),
        role=UserRole.TECHNICIAN,
        active=True,
    )
    database.add(second)
    database.commit()

    assert order["status"] == "ASSIGNED"
    assert [event["event_type"] for event in order["events"]] == ["CREATED", "ASSIGNED"]
    assert order["participants"][0]["user_id"] == str(lead.id)
    assert order["participants"][0]["role"] == "LEAD"

    added = client.post(
        f"/api/v1/work-orders/{order['id']}/participants",
        headers=admin_headers,
        json={"user_id": str(second.id), "role": "TECHNICIAN"},
    )
    assert added.status_code == 200
    assert len(added.json()["participants"]) == 2

    lead_headers = login(client, "tech@alpha.local", "Tech123!")
    second_headers = login(client, "tech2@alpha.local", "TechTwo123!")
    started = client.post(f"/api/v1/work-orders/{order['id']}/start", headers=lead_headers, json={})
    assert started.status_code == 200
    assert started.json()["status"] == "IN_PROGRESS"

    duplicate = client.post(
        f"/api/v1/work-orders/{order['id']}/start", headers=lead_headers, json={}
    )
    assert duplicate.status_code == 409

    second_started = client.post(
        f"/api/v1/work-orders/{order['id']}/start", headers=second_headers, json={}
    )
    assert second_started.status_code == 200
    reassigned = client.patch(
        f"/api/v1/work-orders/{order['id']}",
        headers=admin_headers,
        json={"assigned_to": str(second.id)},
    )
    assert reassigned.status_code == 200
    assert reassigned.json()["status"] == "IN_PROGRESS"
    restored_lead = client.patch(
        f"/api/v1/work-orders/{order['id']}",
        headers=admin_headers,
        json={"assigned_to": str(lead.id)},
    )
    assert restored_lead.status_code == 200
    assert restored_lead.json()["status"] == "IN_PROGRESS"
    paused = client.post(
        f"/api/v1/work-orders/{order['id']}/pause",
        headers=lead_headers,
        json={"note": "Bearing removed; checking the shaft seat."},
    )
    assert paused.status_code == 200
    assert paused.json()["status"] == "IN_PROGRESS"
    resumed = client.post(
        f"/api/v1/work-orders/{order['id']}/resume", headers=lead_headers, json={}
    )
    assert resumed.status_code == 200

    missing_cause = client.post(
        f"/api/v1/work-orders/{order['id']}/complete",
        headers=lead_headers,
        json={"work_performed": "Bearing replaced and machine tested."},
    )
    assert missing_cause.status_code == 422

    empty_work = client.post(
        f"/api/v1/work-orders/{order['id']}/complete",
        headers=lead_headers,
        json={
            "work_performed": "          ",
            "failure_cause": "Bearing race wear",
            "resolution": "Installed a new bearing.",
        },
    )
    assert empty_work.status_code == 422

    completed = client.post(
        f"/api/v1/work-orders/{order['id']}/complete",
        headers=lead_headers,
        json={
            "work_performed": "Bearing replaced, spindle aligned and vibration measured.",
            "failure_cause": "Bearing race wear",
            "root_cause": "Lubrication interval was too long for the operating load.",
            "resolution": "Installed a new bearing and adjusted the lubrication interval.",
        },
    )
    assert completed.status_code == 200
    body = completed.json()
    assert body["status"] == "PENDING_VALIDATION"
    assert body["real_duration"] >= 1
    assert len(body["sessions"]) == 3
    assert all(session["ended_at"] for session in body["sessions"])
    completion_event = next(event for event in body["events"] if event["event_type"] == "COMPLETED")
    assert completion_event["details"]["work_performed"].startswith("Bearing replaced")
    assert completion_event["details"]["participants"] == 2

    validated = client.post(
        f"/api/v1/work-orders/{order['id']}/validate",
        headers=admin_headers,
        json={"note": "Machine tested with production."},
    )
    assert validated.status_code == 200
    assert validated.json()["status"] == "COMPLETED"
    closed = client.post(f"/api/v1/work-orders/{order['id']}/close", headers=admin_headers, json={})
    assert closed.status_code == 200
    closed_body = closed.json()
    assert closed_body["status"] == "CLOSED"
    sequence = [event["sequence_no"] for event in closed_body["events"]]
    assert sequence == list(range(1, len(sequence) + 1))
    assert {"STARTED", "PAUSED", "RESUMED", "COMPLETED", "VALIDATED", "CLOSED"}.issubset(
        {event["event_type"] for event in closed_body["events"]}
    )
    dashboard = client.get("/api/v1/dashboard", headers=admin_headers)
    assert dashboard.status_code == 200
    assert dashboard.json()["completed_work_orders"] >= 1
    assert order["id"] not in {item["id"] for item in dashboard.json()["upcoming_work_orders"]}


def test_work_order_traceability_permissions_and_immutability(client, database):
    order, admin_headers, _ = create_assigned_order(client, database)
    beta_headers = login(client, "admin@beta.local", "Admin123!")
    viewer_headers = login(client, "viewer@alpha.local", "Viewer123!")

    unassigned = client.patch(
        f"/api/v1/work-orders/{order['id']}",
        headers=admin_headers,
        json={"assigned_to": None},
    )
    assert unassigned.status_code == 200
    assert unassigned.json()["status"] == "OPEN"
    assert unassigned.json()["participants"][0]["role"] == "TECHNICIAN"

    assert client.get(f"/api/v1/work-orders/{order['id']}", headers=beta_headers).status_code == 404
    assert (
        client.post(
            f"/api/v1/work-orders/{order['id']}/notes",
            headers=viewer_headers,
            json={"body": "Viewer must not write"},
        ).status_code
        == 403
    )

    event = database.scalar(
        select(WorkOrderEvent).where(WorkOrderEvent.work_order_id == uuid.UUID(order["id"]))
    )
    event.summary = "Attempted history rewrite"
    try:
        database.commit()
        raise AssertionError("Historical event update unexpectedly succeeded")
    except ValueError as exc:
        assert "inmutable" in str(exc)
        database.rollback()

    detail = client.get(f"/api/v1/work-orders/{order['id']}", headers=admin_headers)
    assert detail.status_code == 200
    assert detail.json()["events"][0]["summary"] == "Orden de trabajo creada"
