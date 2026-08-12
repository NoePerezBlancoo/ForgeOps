import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.ai.providers import get_openai_provider
from app.ai.schemas import (
    BulkIndexRead,
    DocumentIndexRead,
    KnowledgeAnswerRead,
    KnowledgeHistoryRead,
    KnowledgeQueryCreate,
    KnowledgeStatusRead,
)
from app.ai.service import (
    index_document,
    index_documents,
    knowledge_status,
    query_history,
    query_knowledge,
)
from app.auth.dependencies import get_current_user, require_module, require_roles
from app.core.database import get_db
from app.core.enums import CompanyModule, UserRole
from app.documents.storage import LocalDocumentStorage, get_document_storage
from app.users.models import User

router = APIRouter(
    prefix="/ai",
    tags=["Asistente documental"],
    dependencies=[Depends(require_module(CompanyModule.KNOWLEDGE))],
)
managers = require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.MAINTENANCE_MANAGER)


@router.get("/status", response_model=KnowledgeStatusRead)
def status_read(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return knowledge_status(db, current_user.company_id)


@router.post("/query", response_model=KnowledgeAnswerRead)
def query(
    payload: KnowledgeQueryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return query_knowledge(db, current_user, payload.question, payload.asset_id, payload.top_k)


@router.get("/history", response_model=list[KnowledgeHistoryRead])
def history(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return query_history(db, current_user, limit)


@router.post("/documents/index", response_model=BulkIndexRead)
def index_pending(
    force: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(managers),
    storage: LocalDocumentStorage = Depends(get_document_storage),
):
    return index_documents(
        db,
        current_user.company_id,
        storage,
        force=force,
        provider=get_openai_provider(),
    )


@router.post("/documents/{document_id}/index", response_model=DocumentIndexRead)
def index_one(
    document_id: uuid.UUID,
    force: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(managers),
    storage: LocalDocumentStorage = Depends(get_document_storage),
):
    return index_document(
        db,
        current_user.company_id,
        document_id,
        storage,
        force=force,
        provider=get_openai_provider(),
    )
