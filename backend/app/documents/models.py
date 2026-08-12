import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.enums import DocumentIndexStatus, DocumentType
from app.core.mixins import TenantMixin, UUIDPrimaryKeyMixin


class TechnicalDocument(UUIDPrimaryKeyMixin, TenantMixin, Base):
    __tablename__ = "technical_documents"
    __table_args__ = (Index("ix_documents_company_uploaded", "company_id", "uploaded_at"),)

    asset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    type: Mapped[DocumentType] = mapped_column(
        Enum(DocumentType, name="document_type", native_enum=False, length=32), nullable=False
    )
    storage_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    index_status: Mapped[DocumentIndexStatus] = mapped_column(
        Enum(
            DocumentIndexStatus,
            name="document_index_status",
            native_enum=False,
            length=24,
        ),
        default=DocumentIndexStatus.PENDING,
        nullable=False,
    )
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    index_error: Mapped[str | None] = mapped_column(String(500))
    content_hash: Mapped[str | None] = mapped_column(String(64))
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    embedded_chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    embedding_model: Mapped[str | None] = mapped_column(String(80))

    asset: Mapped["Asset"] = relationship()  # noqa: F821
    uploader: Mapped["User"] = relationship()  # noqa: F821
    knowledge_chunks: Mapped[list["KnowledgeChunk"]] = relationship(  # noqa: F821
        back_populates="document", cascade="all, delete-orphan"
    )
