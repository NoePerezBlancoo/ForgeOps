from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.assets.models import Asset
from app.companies.models import Company
from app.documents.models import TechnicalDocument
from app.documents.storage import LocalStorageService
from app.users.models import User
from scripts import seed_demo


def test_demo_documents_are_tenant_scoped_and_idempotent(
    database: Session, tmp_path: Path, monkeypatch
) -> None:
    company = database.scalar(select(Company).where(Company.name == "Alpha Factory"))
    user = database.scalar(select(User).where(User.email == "admin@alpha.local"))
    asset = database.scalar(select(Asset).where(Asset.code == "A-001"))
    assert company and user and asset

    monkeypatch.setattr(
        seed_demo,
        "LocalDocumentStorage",
        lambda: LocalStorageService(tmp_path),
    )
    assets = [asset] * 6
    users = {"manager": user}

    seed_demo.get_or_create_documents(database, company, assets, users)
    database.flush()
    seed_demo.get_or_create_documents(database, company, assets, users)
    database.flush()

    documents = list(
        database.scalars(
            select(TechnicalDocument).where(TechnicalDocument.company_id == company.id)
        )
    )
    assert len(documents) == 3
    expected_prefix = f"companies/{company.id}/assets/{asset.id}/documents/"
    for document in documents:
        assert document.asset_id == asset.id
        assert document.mime_type == "text/plain"
        assert document.file_size > 0
        assert document.storage_key.startswith(expected_prefix)
        stored_path = tmp_path / Path(document.storage_key)
        assert stored_path.is_file()
        assert stored_path.read_text(encoding="utf-8").strip()
