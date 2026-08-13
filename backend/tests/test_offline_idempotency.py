import uuid

from sqlalchemy import func, inspect, select

from app.incidents.models import Incident
from app.notifications.models import Notification
from app.users.models import User
from app.work_orders.models import WorkOrderNote
from tests.conftest import login


def _first_asset(client, headers):
    response = client.get("/api/v1/assets", headers=headers)
    assert response.status_code == 200
    return response.json()[0]


def test_incident_creation_is_idempotent_per_reporter(client, database):
    headers = login(client, "admin@alpha.local", "Admin123!")
    asset = _first_asset(client, headers)
    request_id = str(uuid.uuid4())
    payload = {
        "client_request_id": request_id,
        "plant_id": asset["plant_id"],
        "asset_id": asset["id"],
        "title": "Parada detectada sin cobertura",
        "description": "Incidencia registrada desde el dispositivo movil del tecnico.",
        "priority": "CRITICAL",
        "downtime_minutes": 5,
    }

    first = client.post("/api/v1/incidents", headers=headers, json=payload)
    duplicate = client.post(
        "/api/v1/incidents",
        headers=headers,
        json={**payload, "title": "Este cambio no debe crear otra incidencia"},
    )

    assert first.status_code == 201
    assert duplicate.status_code == 201
    assert duplicate.json()["id"] == first.json()["id"]
    assert duplicate.json()["title"] == payload["title"]
    assert duplicate.json()["client_request_id"] == request_id
    assert database.scalar(
        select(func.count(Incident.id)).where(Incident.client_request_id == uuid.UUID(request_id))
    ) == 1
    assert database.scalar(
        select(func.count(Notification.id)).where(
            Notification.dedupe_key == f"critical-incident:{first.json()['id']}"
        )
    ) == 1


def test_work_order_note_retry_does_not_duplicate_history(client, database):
    headers = login(client, "admin@alpha.local", "Admin123!")
    asset = _first_asset(client, headers)
    admin = database.scalar(select(User).where(User.email == "admin@alpha.local"))
    created = client.post(
        "/api/v1/work-orders",
        headers=headers,
        json={
            "plant_id": asset["plant_id"],
            "asset_id": asset["id"],
            "assigned_to": str(admin.id),
            "title": "Diagnostico desde PWA",
            "description": "Orden utilizada para validar notas sincronizadas sin duplicados.",
            "type": "CORRECTIVE",
            "priority": "HIGH",
        },
    )
    assert created.status_code == 201
    order = created.json()
    request_id = str(uuid.uuid4())
    payload = {
        "client_request_id": request_id,
        "note_type": "WORK_LOG",
        "body": "Mediciones tomadas durante una perdida temporal de conexion.",
    }

    first = client.post(
        f"/api/v1/work-orders/{order['id']}/notes", headers=headers, json=payload
    )
    duplicate = client.post(
        f"/api/v1/work-orders/{order['id']}/notes", headers=headers, json=payload
    )

    assert first.status_code == 200
    assert duplicate.status_code == 200
    matching_notes = [
        note
        for note in duplicate.json()["notes"]
        if note["client_request_id"] == request_id
    ]
    assert len(matching_notes) == 1
    assert len(
        [event for event in duplicate.json()["events"] if event["event_type"] == "NOTE_ADDED"]
    ) == 1


def test_offline_idempotency_constraints_are_declared():
    incident_constraints = {item.name for item in Incident.__table__.constraints}
    note_constraints = {item.name for item in WorkOrderNote.__table__.constraints}
    assert "uq_incident_client_request" in incident_constraints
    assert "uq_work_order_note_client_request" in note_constraints
    assert inspect(Incident).columns.client_request_id.nullable
    assert inspect(WorkOrderNote).columns.client_request_id.nullable
