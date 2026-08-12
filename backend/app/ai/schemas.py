from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.enums import DocumentIndexStatus


class KnowledgeStatusRead(BaseModel):
    configured_provider: str
    effective_provider: str
    generation_available: bool
    semantic_search_available: bool
    chat_model: str | None
    embedding_model: str | None
    indexed_documents: int
    pending_documents: int
    failed_documents: int
    unsupported_documents: int
    chunks: int
    embedded_chunks: int
    configuration_warning: str | None


class DocumentIndexRead(BaseModel):
    document_id: UUID
    status: DocumentIndexStatus
    chunks: int
    embedded_chunks: int
    embedding_model: str | None
    message: str


class BulkIndexRead(BaseModel):
    indexed: int
    failed: int
    unsupported: int


class KnowledgeQueryCreate(BaseModel):
    question: str = Field(min_length=5, max_length=1000)
    asset_id: UUID | None = None
    top_k: int = Field(default=5, ge=1, le=8)


class KnowledgeSourceRead(BaseModel):
    chunk_id: UUID
    document_id: UUID
    document_name: str
    original_name: str
    asset_id: UUID
    asset_code: str
    asset_name: str
    page_number: int | None
    excerpt: str
    score: float


class KnowledgeAnswerRead(BaseModel):
    query_id: UUID
    answer: str
    mode: str
    provider: str
    model: str | None
    confidence: float
    duration_ms: int
    sources: list[KnowledgeSourceRead]


class KnowledgeHistoryRead(BaseModel):
    id: UUID
    question: str
    answer: str
    mode: str
    provider: str
    model: str | None
    confidence: float
    source_count: int
    duration_ms: int
    created_at: datetime
