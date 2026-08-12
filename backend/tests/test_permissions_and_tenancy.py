from sqlalchemy import select

from app.plants.models import Plant
from tests.conftest import login


def test_viewer_cannot_create_asset(client, database):
    headers = login(client, "viewer@alpha.local", "Viewer123!")
    plant = database.scalar(select(Plant).where(Plant.code == "ALPHA"))
    response = client.post(
        "/api/v1/assets",
        headers=headers,
        json={"plant_id": str(plant.id), "code": "A-002", "name": "Protected Asset"},
    )
    assert response.status_code == 403


def test_assets_are_isolated_between_companies(client):
    alpha_headers = login(client, "admin@alpha.local", "Admin123!")
    beta_headers = login(client, "admin@beta.local", "Admin123!")
    alpha_assets = client.get("/api/v1/assets", headers=alpha_headers).json()
    beta_assets = client.get("/api/v1/assets", headers=beta_headers).json()
    assert [asset["code"] for asset in alpha_assets] == ["A-001"]
    assert [asset["code"] for asset in beta_assets] == ["B-001"]
