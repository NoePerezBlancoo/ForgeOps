import uuid

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_module, require_roles
from app.core.database import get_db
from app.core.enums import CompanyModule, DocumentType, UserRole
from app.documents.schemas import TechnicalDocumentRead, TechnicalDocumentUpdate
from app.documents.service import (
    create_document,
    delete_document,
    get_document,
    list_documents,
    update_document,
)
from app.documents.storage import LocalDocumentStorage, get_document_storage
from app.users.models import User

router = APIRouter(
    prefix="/documents",
    tags=["Documentos tecnicos"],
    dependencies=[Depends(require_module(CompanyModule.DOCUMENTS))],
)
managers = require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.MAINTENANCE_MANAGER)


@router.get("", response_model=list[TechnicalDocumentRead])
def index(
    search: str | None = Query(default=None, max_length=100),
    asset_id: uuid.UUID | None = None,
    document_type: DocumentType | None = Query(default=None, alias="type"),
    plant_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_documents(
        db, current_user.company_id, search, asset_id, document_type, plant_id
    )


@router.post("", response_model=TechnicalDocumentRead, status_code=status.HTTP_201_CREATED)
async def store(
    asset_id: uuid.UUID = Form(),
    name: str = Form(min_length=3, max_length=180),
    document_type: DocumentType = Form(alias="type"),
    description: str | None = Form(default=None, max_length=3000),
    file: UploadFile = File(),
    db: Session = Depends(get_db),
    current_user: User = Depends(managers),
    storage: LocalDocumentStorage = Depends(get_document_storage),
):
    return await create_document(
        db, current_user, storage, asset_id, name, document_type, description, file
    )


@router.get("/{document_id}", response_model=TechnicalDocumentRead)
def show(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_document(db, current_user.company_id, document_id)


@router.patch("/{document_id}", response_model=TechnicalDocumentRead)
def update(
    document_id: uuid.UUID,
    payload: TechnicalDocumentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(managers),
):
    return update_document(db, current_user.company_id, document_id, payload)


@router.get("/{document_id}/download")
def download(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage: LocalDocumentStorage = Depends(get_document_storage),
):
    document = get_document(db, current_user.company_id, document_id)
    return FileResponse(
        path=storage.path_for(document.storage_key),
        filename=document.original_name,
        media_type=document.mime_type,
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def destroy(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(managers),
    storage: LocalDocumentStorage = Depends(get_document_storage),
):
    delete_document(db, current_user.company_id, document_id, storage)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
