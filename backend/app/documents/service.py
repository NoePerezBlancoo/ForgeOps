import uuid

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.assets.models import Asset
from app.core.config import settings
from app.core.enums import DocumentType
from app.documents.models import TechnicalDocument
from app.documents.schemas import TechnicalDocumentUpdate
from app.documents.storage import LocalDocumentStorage
from app.users.models import User


def list_documents(
    db: Session,
    company_id: uuid.UUID,
    search: str | None = None,
    asset_id: uuid.UUID | None = None,
    document_type: DocumentType | None = None,
) -> list[TechnicalDocument]:
    query = (
        select(TechnicalDocument)
        .options(joinedload(TechnicalDocument.asset), joinedload(TechnicalDocument.uploader))
        .where(TechnicalDocument.company_id == company_id)
        .order_by(TechnicalDocument.uploaded_at.desc())
    )
    if search:
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                TechnicalDocument.name.ilike(term),
                TechnicalDocument.original_name.ilike(term),
                TechnicalDocument.description.ilike(term),
            )
        )
    if asset_id:
        query = query.where(TechnicalDocument.asset_id == asset_id)
    if document_type:
        query = query.where(TechnicalDocument.type == document_type)
    return list(db.scalars(query).unique())


def get_document(db: Session, company_id: uuid.UUID, document_id: uuid.UUID) -> TechnicalDocument:
    document = db.scalar(
        select(TechnicalDocument)
        .options(joinedload(TechnicalDocument.asset), joinedload(TechnicalDocument.uploader))
        .where(
            TechnicalDocument.id == document_id,
            TechnicalDocument.company_id == company_id,
        )
    )
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento no encontrado")
    return document


async def create_document(
    db: Session,
    current_user: User,
    storage: LocalDocumentStorage,
    asset_id: uuid.UUID,
    name: str,
    document_type: DocumentType,
    description: str | None,
    upload: UploadFile,
) -> TechnicalDocument:
    asset = db.scalar(
        select(Asset).where(Asset.id == asset_id, Asset.company_id == current_user.company_id)
    )
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Activo no valido"
        )

    content = await upload.read(settings.max_upload_bytes + 1)
    await upload.close()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Archivo vacio"
        )
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="El archivo supera el limite permitido",
        )

    original_name = upload.filename or "documento"
    storage_key = storage.store(current_user.company_id, original_name, content)
    document = TechnicalDocument(
        company_id=current_user.company_id,
        asset_id=asset_id,
        uploaded_by=current_user.id,
        name=name.strip(),
        type=document_type,
        storage_key=storage_key,
        original_name=original_name[:255],
        mime_type=(upload.content_type or "application/octet-stream")[:120],
        file_size=len(content),
        description=description.strip() if description else None,
    )
    db.add(document)
    try:
        db.commit()
    except Exception:
        db.rollback()
        storage.delete(storage_key)
        raise
    return get_document(db, current_user.company_id, document.id)


def update_document(
    db: Session,
    company_id: uuid.UUID,
    document_id: uuid.UUID,
    payload: TechnicalDocumentUpdate,
) -> TechnicalDocument:
    document = get_document(db, company_id, document_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(document, field, value.strip() if isinstance(value, str) else value)
    db.commit()
    return get_document(db, company_id, document.id)


def delete_document(
    db: Session,
    company_id: uuid.UUID,
    document_id: uuid.UUID,
    storage: LocalDocumentStorage,
) -> None:
    document = get_document(db, company_id, document_id)
    storage_key = document.storage_key
    db.delete(document)
    db.commit()
    storage.delete(storage_key)
