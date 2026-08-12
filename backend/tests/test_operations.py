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
