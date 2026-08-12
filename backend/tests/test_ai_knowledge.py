from sqlalchemy import func, select

from app.ai.models import KnowledgeChunk
from app.documents.storage import LocalDocumentStorage, get_document_storage
from tests.conftest import login


def _first_asset(client, headers):
    response = client.get("/api/v1/assets", headers=headers)
    assert response.status_code == 200
    return response.json()[0]


def test_document_indexing_and_extractive_query_are_tenant_isolated(client, database, tmp_path):
    storage = LocalDocumentStorage(tmp_path)
    client.app.dependency_overrides[get_document_storage] = lambda: storage
    alpha_headers = login(client, "admin@alpha.local", "Admin123!")
    alpha_asset = _first_asset(client, alpha_headers)

    uploaded = client.post(
        "/api/v1/documents",
        headers=alpha_headers,
        data={
            "asset_id": alpha_asset["id"],
            "name": "Procedimiento de consignacion",
            "type": "SAFETY",
            "description": "Procedimiento controlado de seguridad.",
        },
        files={
            "file": (
                "consignacion.txt",
                b"Detener el equipo. Aislar todas las energias. Verificar ausencia de tension.",
                "text/plain",
            )
        },
    )
    assert uploaded.status_code == 201
    document = uploaded.json()
    assert document["index_status"] == "PENDING"

    indexed = client.post(f"/api/v1/ai/documents/{document['id']}/index", headers=alpha_headers)
    assert indexed.status_code == 200
    assert indexed.json()["status"] == "READY"
    assert indexed.json()["chunks"] == 1
    assert indexed.json()["embedded_chunks"] == 0

    repeated = client.post(f"/api/v1/ai/documents/{document['id']}/index", headers=alpha_headers)
    assert repeated.status_code == 200
    assert database.scalar(select(func.count(KnowledgeChunk.id))) == 1

    distractor = client.post(
        "/api/v1/documents",
        headers=alpha_headers,
        data={
            "asset_id": alpha_asset["id"],
            "name": "Referencia de diagnostico del robot",
            "type": "MANUAL",
        },
        files={
            "file": (
                "robot.txt",
                b"Comprobar alarmas, seguridades y referencias de ejes antes del rearme.",
                "text/plain",
            )
        },
    )
    assert distractor.status_code == 201
    indexed_distractor = client.post(
        f"/api/v1/ai/documents/{distractor.json()['id']}/index", headers=alpha_headers
    )
    assert indexed_distractor.status_code == 200

    answer = client.post(
        "/api/v1/ai/query",
        headers=alpha_headers,
        json={"question": "Como se debe realizar el bloqueo de energias antes de intervenir?"},
    )
    assert answer.status_code == 200
    payload = answer.json()
    assert payload["mode"] == "extractive"
    assert payload["provider"] == "local"
    assert len(payload["sources"]) == 1
    assert payload["sources"][0]["document_id"] == document["id"]
    assert "[1]" in payload["answer"]

    beta_headers = login(client, "admin@beta.local", "Admin123!")
    hidden = client.post(
        "/api/v1/ai/query",
        headers=beta_headers,
        json={"question": "Como se deben aislar las energias del equipo?"},
    )
    assert hidden.status_code == 200
    assert hidden.json()["mode"] == "insufficient"
    assert hidden.json()["sources"] == []


def test_unsupported_document_is_reported_and_viewer_cannot_index(client, tmp_path):
    storage = LocalDocumentStorage(tmp_path)
    client.app.dependency_overrides[get_document_storage] = lambda: storage
    admin_headers = login(client, "admin@alpha.local", "Admin123!")
    asset = _first_asset(client, admin_headers)
    uploaded = client.post(
        "/api/v1/documents",
        headers=admin_headers,
        data={
            "asset_id": asset["id"],
            "name": "Fotografia de placa",
            "type": "OTHER",
        },
        files={"file": ("placa.png", b"not-a-real-image", "image/png")},
    )
    assert uploaded.status_code == 201

    viewer_headers = login(client, "viewer@alpha.local", "Viewer123!")
    denied = client.post(
        f"/api/v1/ai/documents/{uploaded.json()['id']}/index", headers=viewer_headers
    )
    assert denied.status_code == 403

    indexed = client.post(
        f"/api/v1/ai/documents/{uploaded.json()['id']}/index", headers=admin_headers
    )
    assert indexed.status_code == 200
    assert indexed.json()["status"] == "UNSUPPORTED"

    status = client.get("/api/v1/ai/status", headers=admin_headers)
    assert status.status_code == 200
    assert status.json()["effective_provider"] == "local"
    assert status.json()["unsupported_documents"] == 1
