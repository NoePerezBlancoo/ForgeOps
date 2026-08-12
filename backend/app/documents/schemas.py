from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.enums import DocumentIndexStatus, DocumentType
from app.core.schemas import AssetSummary, ORMModel, UserSummary


class TechnicalDocumentRead(ORMModel):
    id: UUID
    company_id: UUID
    asset_id: UUID
    uploaded_by: UUID
    name: str
    type: DocumentType
    original_name: str
    mime_type: str
    file_size: int
    description: str | None
    uploaded_at: datetime
    index_status: DocumentIndexStatus
    indexed_at: datetime | None
    index_error: str | None
    chunk_count: int
    embedded_chunk_count: int
    embedding_model: str | None
    asset: AssetSummary
    uploader: UserSummary


class TechnicalDocumentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=3, max_length=180)
    type: DocumentType | None = None
    description: str | None = Field(default=None, max_length=3000)
