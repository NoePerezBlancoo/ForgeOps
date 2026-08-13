from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.documents.storage import LocalDocumentStorage, get_document_storage
from app.users.models import User
from tests.conftest import login


def _first_asset(client, headers):
    response = client.get("/api/v1/assets", headers=headers)
    assert response.status_code == 200
    return response.json()[0]


def test_preventive_plan_generates_only_one_pending_order(client, database):
    headers = login(client, "admin@alpha.local", "Admin123!")
    beta_headers = login(client, "admin@beta.local", "Admin123!")
    asset = _first_asset(client, headers)
    admin = database.scalar(select(User).where(User.email == "admin@alpha.local"))
    template_response = client.post(
        "/api/v1/preventive-maintenance/checklists/templates",
        headers=headers,
        json={
            "name": "Revision mensual de compresor",
            "description": "Comprobaciones de seguridad y operacion.",
            "items": [
                {
                    "title": "Comprobar nivel de aceite",
                    "instructions": "Registrar fugas antes de rellenar.",
                    "position": 1,
                    "required": True,
                },
                {
                    "title": "Registrar temperatura",
                    "position": 2,
                    "required": False,
                },
            ],
        },
    )
    assert template_response.status_code == 201
    template = template_response.json()
    assert client.get(
        f"/api/v1/preventive-maintenance/checklists/templates/{template['id']}",
        headers=beta_headers,
    ).status_code == 404
    response = client.post(
        "/api/v1/preventive-maintenance",
        headers=headers,
        json={
            "asset_id": asset["id"],
            "assigned_to": str(admin.id),
            "checklist_template_id": template["id"],
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
    order_id = generated.json()["id"]
    detail = client.get(f"/api/v1/work-orders/{order_id}", headers=headers)
    assert detail.status_code == 200
    assert [item["title"] for item in detail.json()["checklist_items"]] == [
        "Comprobar nivel de aceite",
        "Registrar temperatura",
    ]

    updated_template = client.patch(
        f"/api/v1/preventive-maintenance/checklists/templates/{template['id']}",
        headers=headers,
        json={
            "items": [
                {
                    "title": "Nuevo paso para futuras ordenes",
                    "position": 1,
                    "required": True,
                }
            ]
        },
    )
    assert updated_template.status_code == 200
    assert client.get(
        f"/api/v1/work-orders/{order_id}", headers=headers
    ).json()["checklist_items"][0]["title"] == "Comprobar nivel de aceite"

    assert client.post(
        f"/api/v1/work-orders/{order_id}/start", headers=headers, json={}
    ).status_code == 200
    blocked_completion = client.post(
        f"/api/v1/work-orders/{order_id}/complete",
        headers=headers,
        json={"work_performed": "Revision preventiva realizada segun procedimiento."},
    )
    assert blocked_completion.status_code == 409
    required_item = detail.json()["checklist_items"][0]
    checked = client.patch(
        f"/api/v1/work-orders/{order_id}/checklist/{required_item['id']}",
        headers=headers,
        json={"completed": True, "notes": "Nivel correcto", "version": 1},
    )
    assert checked.status_code == 200
    checked_item = checked.json()["checklist_items"][0]
    assert checked_item["completed_by"] == str(admin.id)
    assert checked_item["version"] == 2
    assert client.patch(
        f"/api/v1/work-orders/{order_id}/checklist/{required_item['id']}",
        headers=headers,
        json={"completed": False, "version": 1},
    ).status_code == 409
    completed = client.post(
        f"/api/v1/work-orders/{order_id}/complete",
        headers=headers,
        json={"work_performed": "Revision preventiva realizada segun procedimiento."},
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "PENDING_VALIDATION"

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

    updated = client.patch(
        f"/api/v1/inventory/{item['id']}",
        headers=headers,
        json={"location": "A-01-01", "expected_version": item["version"]},
    )
    assert updated.status_code == 200
    assert updated.json()["version"] == item["version"] + 1
    stale_update = client.patch(
        f"/api/v1/inventory/{item['id']}",
        headers=headers,
        json={"location": "A-01-02", "expected_version": item["version"]},
    )
    assert stale_update.status_code == 409

    consumed = client.post(
        f"/api/v1/inventory/{item['id']}/movements",
        headers=headers,
        json={
            "movement_type": "CONSUMPTION",
            "quantity": 4,
            "reason": "Orden de prueba",
            "expected_version": updated.json()["version"],
        },
    )
    assert consumed.status_code == 200
    assert float(consumed.json()["resulting_stock"]) == 1

    refreshed = client.get(f"/api/v1/inventory/{item['id']}", headers=headers)
    assert refreshed.json()["low_stock"] is True

    rejected = client.post(
        f"/api/v1/inventory/{item['id']}/movements",
        headers=headers,
        json={
            "movement_type": "CONSUMPTION",
            "quantity": 2,
            "reason": "Consumo excesivo",
            "expected_version": refreshed.json()["version"],
        },
    )
    assert rejected.status_code == 409

    movements = client.get(f"/api/v1/inventory/{item['id']}/movements", headers=headers)
    assert movements.status_code == 200
    assert len(movements.json()) == 2


def test_work_order_materials_update_stock_cost_timeline_and_notifications(client, database):
    headers = login(client, "admin@alpha.local", "Admin123!")
    beta_headers = login(client, "admin@beta.local", "Admin123!")
    asset = _first_asset(client, headers)
    admin = database.scalar(select(User).where(User.email == "admin@alpha.local"))

    item_response = client.post(
        "/api/v1/inventory",
        headers=headers,
        json={
            "code": "MAT-OT-001",
            "name": "Material para orden",
            "stock": 5,
            "minimum_stock": 4,
            "unit": "ud",
            "cost": 10,
            "active": True,
        },
    )
    assert item_response.status_code == 201
    item = item_response.json()
    order_response = client.post(
        "/api/v1/work-orders",
        headers=headers,
        json={
            "plant_id": asset["plant_id"],
            "asset_id": asset["id"],
            "assigned_to": str(admin.id),
            "title": "Sustituir material de prueba",
            "description": "Intervencion para validar consumos trazables de inventario.",
            "type": "CORRECTIVE",
            "priority": "HIGH",
        },
    )
    assert order_response.status_code == 201
    order = order_response.json()

    consumed = client.post(
        f"/api/v1/work-orders/{order['id']}/materials",
        headers=headers,
        json={
            "item_id": item["id"],
            "quantity": 2,
            "expected_version": item["version"],
            "reason": "Sustitucion durante la intervencion",
        },
    )
    assert consumed.status_code == 200
    consumed_order = consumed.json()
    assert float(consumed_order["material_cost"]) == 20
    assert len(consumed_order["inventory_movements"]) == 1
    movement = consumed_order["inventory_movements"][0]
    assert movement["movement_type"] == "CONSUMPTION"
    assert float(movement["quantity"]) == -2
    assert movement["item"]["code"] == "MAT-OT-001"
    assert any(event["event_type"] == "MATERIAL_CONSUMED" for event in consumed_order["events"])

    cross_tenant = client.post(
        f"/api/v1/work-orders/{order['id']}/materials",
        headers=beta_headers,
        json={"item_id": item["id"], "quantity": 1, "expected_version": 2},
    )
    assert cross_tenant.status_code == 404

    stale = client.post(
        f"/api/v1/work-orders/{order['id']}/materials",
        headers=headers,
        json={"item_id": item["id"], "quantity": 1, "expected_version": 1},
    )
    assert stale.status_code == 409

    refreshed_item = client.get(f"/api/v1/inventory/{item['id']}", headers=headers).json()
    returned = client.post(
        f"/api/v1/work-orders/{order['id']}/materials/{movement['id']}/return",
        headers=headers,
        json={
            "quantity": 0.5,
            "expected_version": refreshed_item["version"],
            "reason": "Material finalmente no utilizado",
        },
    )
    assert returned.status_code == 200
    returned_order = returned.json()
    assert float(returned_order["material_cost"]) == 15
    assert returned_order["inventory_movements"][-1]["reversal_of_id"] == movement["id"]
    assert any(event["event_type"] == "MATERIAL_RETURNED" for event in returned_order["events"])

    current_item = client.get(f"/api/v1/inventory/{item['id']}", headers=headers).json()
    excessive_return = client.post(
        f"/api/v1/work-orders/{order['id']}/materials/{movement['id']}/return",
        headers=headers,
        json={"quantity": 2, "expected_version": current_item["version"]},
    )
    assert excessive_return.status_code == 409

    notifications = client.get("/api/v1/notifications", headers=headers)
    assert notifications.status_code == 200
    assert any(item["type"] == "LOW_STOCK" for item in notifications.json()["items"])


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
