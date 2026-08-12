from sqlalchemy import select

from app.assets.models import Asset
from app.plants.models import Plant
from app.users.models import User
from tests.conftest import login


def test_create_asset(client, database):
    headers = login(client, "admin@alpha.local", "Admin123!")
    plant = database.scalar(select(Plant).where(Plant.code == "ALPHA"))
    response = client.post(
        "/api/v1/assets",
        headers=headers,
        json={
            "plant_id": str(plant.id),
            "code": "A-002",
            "name": "Hydraulic Press",
            "status": "ACTIVE",
            "criticality": "CRITICAL",
        },
    )
    assert response.status_code == 201
    assert response.json()["code"] == "A-002"


def test_create_incident(client, database):
    headers = login(client, "admin@alpha.local", "Admin123!")
    asset = database.scalar(select(Asset).where(Asset.code == "A-001"))
    technician = database.scalar(select(User).where(User.email == "tech@alpha.local"))
    response = client.post(
        "/api/v1/incidents",
        headers=headers,
        json={
            "plant_id": str(asset.plant_id),
            "asset_id": str(asset.id),
            "assigned_to": str(technician.id),
            "title": "Abnormal spindle vibration",
            "description": "The operator detected excessive vibration during production.",
            "priority": "HIGH",
        },
    )
    assert response.status_code == 201
    assert response.json()["status"] == "ASSIGNED"


def test_create_work_order(client, database):
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
            "title": "Inspect spindle bearings",
            "description": "Measure vibration and inspect the front spindle bearing.",
            "type": "CORRECTIVE",
            "priority": "HIGH",
            "estimated_duration": 90,
        },
    )
    assert response.status_code == 201
    assert response.json()["number"].startswith("OT-")
    assert response.json()["status"] == "ASSIGNED"


def test_paginated_operational_lists_are_filtered_and_tenant_scoped(client, database):
    headers = login(client, "admin@alpha.local", "Admin123!")
    asset = database.scalar(select(Asset).where(Asset.code == "A-001"))
    technician = database.scalar(select(User).where(User.email == "tech@alpha.local"))

    incident = client.post(
        "/api/v1/incidents",
        headers=headers,
        json={
            "plant_id": str(asset.plant_id),
            "asset_id": str(asset.id),
            "assigned_to": str(technician.id),
            "title": "Hydraulic pressure deviation",
            "description": "Pressure dropped below the validated operating threshold.",
            "priority": "CRITICAL",
        },
    )
    assert incident.status_code == 201

    order = client.post(
        "/api/v1/work-orders",
        headers=headers,
        json={
            "plant_id": str(asset.plant_id),
            "asset_id": str(asset.id),
            "assigned_to": str(technician.id),
            "title": "Inspect hydraulic circuit",
            "description": "Check pressure, seals and pump condition before restart.",
            "type": "CORRECTIVE",
            "priority": "CRITICAL",
        },
    )
    assert order.status_code == 201

    assets = client.get(
        "/api/v1/assets/page?page=1&page_size=10&search=A-001",
        headers=headers,
    )
    assert assets.status_code == 200
    assert assets.json()["total"] == 1
    assert assets.json()["pages"] == 1
    assert [item["code"] for item in assets.json()["items"]] == ["A-001"]

    incidents = client.get(
        "/api/v1/incidents/page?page=1&page_size=10&status=ASSIGNED&priority=CRITICAL",
        headers=headers,
    )
    assert incidents.status_code == 200
    assert incidents.json()["total"] == 1
    assert incidents.json()["items"][0]["title"] == "Hydraulic pressure deviation"
    assert incidents.json()["filters"]["status"] == "ASSIGNED"

    orders = client.get(
        "/api/v1/work-orders/page?page=1&page_size=10&search=hydraulic",
        headers=headers,
    )
    assert orders.status_code == 200
    assert orders.json()["total"] == 1
    assert orders.json()["items"][0]["title"] == "Inspect hydraulic circuit"

    assert client.get(
        "/api/v1/assets/page?page=1&page_size=101",
        headers=headers,
    ).status_code == 422
