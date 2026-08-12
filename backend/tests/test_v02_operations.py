from datetime import UTC, datetime, timedelta

from app.documents.storage import LocalDocumentStorage, get_document_storage
from tests.conftest import login


def _first_asset(client, headers):
    response = client.get("/api/v1/assets", headers=headers)
    assert response.status_code == 200
    return response.json()[0]


def test_preventive_plan_generates_only_one_pending_order(client):
    headers = login(client, "admin@alpha.local", "Admin123!")
    asset = _first_asset(client, headers)
    response = client.post(
        "/api/v1/preventive-maintenance",
        headers=headers,
        json={
            "asset_id": asset["id"],
            "assigned_to": None,
            "name": "Revision mensual de seguridad",
            "description": "Comprobar protecciones, enclavamientos y parada de emergencia.",
            "frequency_type": "MONTHS",
            "frequency_value": 1,
            "next_execution": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
            "estimated_duration": 60,
            "priority": "HIGH",
            "active": True,
        },
    )
    assert response.status_code == 201
    plan = response.json()

    generated = client.post(
        f"/api/v1/preventive-maintenance/{plan['id']}/generate-work-order",
        headers=headers,
    )
    assert generated.status_code == 200
    assert generated.json()["type"] == "PREVENTIVE"
    assert generated.json()["preventive_plan_id"] == plan["id"]

    duplicate = client.post(
        f"/api/v1/preventive-maintenance/{plan['id']}/generate-work-order",
        headers=headers,
    )
    assert duplicate.status_code == 409

    due_plan = client.post(
        "/api/v1/preventive-maintenance",
        headers=headers,
        json={
            "asset_id": asset["id"],
            "name": "Inspeccion preventiva vencida",
            "description": "Inspeccion periodica preparada para la generacion automatica.",
            "frequency_type": "WEEKS",
            "frequency_value": 2,
            "next_execution": (datetime.now(UTC) - timedelta(days=1)).isoformat(),
            "estimated_duration": 30,
            "priority": "MEDIUM",
            "active": True,
        },
    )
    assert due_plan.status_code == 201
    bulk = client.post("/api/v1/preventive-maintenance/actions/generate-due", headers=headers)
    assert bulk.status_code == 200
    assert bulk.json() == {"generated": 1, "skipped": 0}


def test_inventory_movements_are_traced_and_stock_cannot_be_negative(client):
    headers = login(client, "admin@alpha.local", "Admin123!")
    created = client.post(
        "/api/v1/inventory",
        headers=headers,
        json={
            "code": "TEST-001",
            "name": "Repuesto de prueba",
            "stock": 5,
            "minimum_stock": 2,
            "unit": "ud",
            "cost": 10.5,
            "active": True,
        },
    )
    assert created.status_code == 201
    item = created.json()
    assert item["low_stock"] is False

    consumed = client.post(
        f"/api/v1/inventory/{item['id']}/movements",
        headers=headers,
        json={"movement_type": "CONSUMPTION", "quantity": 4, "reason": "Orden de prueba"},
    )
    assert consumed.status_code == 200
    assert float(consumed.json()["resulting_stock"]) == 1

    refreshed = client.get(f"/api/v1/inventory/{item['id']}", headers=headers)
    assert refreshed.json()["low_stock"] is True

    rejected = client.post(
        f"/api/v1/inventory/{item['id']}/movements",
        headers=headers,
        json={"movement_type": "CONSUMPTION", "quantity": 2, "reason": "Consumo excesivo"},
    )
    assert rejected.status_code == 409

    movements = client.get(f"/api/v1/inventory/{item['id']}/movements", headers=headers)
    assert movements.status_code == 200
    assert len(movements.json()) == 2


def test_documents_are_private_and_downloadable(client, tmp_path):
    storage = LocalDocumentStorage(tmp_path)
    client.app.dependency_overrides[get_document_storage] = lambda: storage
    admin_headers = login(client, "admin@alpha.local", "Admin123!")
    asset = _first_asset(client, admin_headers)

    uploaded = client.post(
        "/api/v1/documents",
        headers=admin_headers,
        data={
            "asset_id": asset["id"],
            "name": "Procedimiento de prueba",
            "type": "PROCEDURE",
            "description": "Documento controlado para validar el almacenamiento.",
        },
        files={"file": ("procedimiento.txt", b"contenido tecnico", "text/plain")},
    )
    assert uploaded.status_code == 201
    document = uploaded.json()

    downloaded = client.get(f"/api/v1/documents/{document['id']}/download", headers=admin_headers)
    assert downloaded.status_code == 200
    assert downloaded.content == b"contenido tecnico"

    anonymous = client.get(f"/api/v1/documents/{document['id']}/download")
    assert anonymous.status_code == 401

    beta_headers = login(client, "admin@beta.local", "Admin123!")
    hidden = client.get(f"/api/v1/documents/{document['id']}", headers=beta_headers)
    assert hidden.status_code == 404
