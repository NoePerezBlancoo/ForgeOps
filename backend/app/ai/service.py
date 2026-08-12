import hashlib
import math
import re
import time
import unicodedata
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, joinedload

from app.ai.chunking import chunk_sections
from app.ai.extractors import EmptyDocumentError, UnsupportedDocumentError, extract_sections
from app.ai.models import AIQueryLog, KnowledgeChunk
from app.ai.providers import OpenAIKnowledgeProvider, get_openai_provider
from app.ai.schemas import (
    BulkIndexRead,
    DocumentIndexRead,
    KnowledgeAnswerRead,
    KnowledgeHistoryRead,
    KnowledgeSourceRead,
    KnowledgeStatusRead,
)
from app.assets.models import Asset
from app.core.config import settings
from app.core.enums import DocumentIndexStatus
from app.documents.models import TechnicalDocument
from app.documents.storage import StorageService
from app.users.models import User

STOP_WORDS = {
    "a",
    "al",
    "antes",
    "con",
    "como",
    "cual",
    "cuales",
    "de",
    "del",
    "debe",
    "deben",
    "documentacion",
    "el",
    "en",
    "es",
    "la",
    "las",
    "los",
    "para",
    "por",
    "que",
    "realizar",
    "sobre",
    "se",
    "intervenir",
    "un",
    "una",
    "y",
}


@dataclass(frozen=True)
class ScoredChunk:
    chunk: KnowledgeChunk
    score: float


def knowledge_status(db: Session, company_id: uuid.UUID) -> KnowledgeStatusRead:
    status_counts = dict(
        db.execute(
            select(TechnicalDocument.index_status, func.count(TechnicalDocument.id))
            .where(TechnicalDocument.company_id == company_id)
            .group_by(TechnicalDocument.index_status)
        ).all()
    )
    chunks = db.scalar(
        select(func.count(KnowledgeChunk.id)).where(KnowledgeChunk.company_id == company_id)
    )
    embedded_chunks = db.scalar(
        select(func.count(KnowledgeChunk.id)).where(
            KnowledgeChunk.company_id == company_id, KnowledgeChunk.embedding.is_not(None)
        )
    )
    openai_ready = settings.ai_provider == "openai" and bool(settings.openai_api_key)
    warning = None
    if settings.ai_provider == "openai" and not settings.openai_api_key:
        warning = "OPENAI_API_KEY no configurada; se utiliza recuperacion local extractiva."
    return KnowledgeStatusRead(
        configured_provider=settings.ai_provider,
        effective_provider="openai" if openai_ready else "local",
        generation_available=openai_ready,
        semantic_search_available=openai_ready and bool(embedded_chunks),
        chat_model=settings.openai_chat_model if openai_ready else None,
        embedding_model=settings.openai_embedding_model if openai_ready else None,
        indexed_documents=status_counts.get(DocumentIndexStatus.READY, 0),
        pending_documents=status_counts.get(DocumentIndexStatus.PENDING, 0)
        + status_counts.get(DocumentIndexStatus.INDEXING, 0),
        failed_documents=status_counts.get(DocumentIndexStatus.FAILED, 0),
        unsupported_documents=status_counts.get(DocumentIndexStatus.UNSUPPORTED, 0),
        chunks=chunks or 0,
        embedded_chunks=embedded_chunks or 0,
        configuration_warning=warning,
    )


def index_document(
    db: Session,
    company_id: uuid.UUID,
    document_id: uuid.UUID,
    storage: StorageService,
    force: bool = False,
    provider: OpenAIKnowledgeProvider | None = None,
) -> DocumentIndexRead:
    document = db.scalar(
        select(TechnicalDocument).where(
            TechnicalDocument.id == document_id,
            TechnicalDocument.company_id == company_id,
        )
    )
    if not document:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    needs_embeddings = provider is not None and document.embedded_chunk_count < document.chunk_count
    if document.index_status == DocumentIndexStatus.READY and not force and not needs_embeddings:
        return _index_response(document, "El documento ya esta indexado")

    document.index_status = DocumentIndexStatus.INDEXING
    document.index_error = None
    db.commit()
    try:
        content = storage.read(company_id, document.storage_key)
        content_hash = hashlib.sha256(content).hexdigest()
        sections = extract_sections(
            content, document.original_name, settings.rag_max_document_chars
        )
        chunks = chunk_sections(sections, settings.rag_chunk_chars, settings.rag_chunk_overlap)
        if not chunks:
            raise EmptyDocumentError("No se generaron fragmentos indexables")
        embeddings = provider.embed([chunk.content for chunk in chunks]) if provider else []

        db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.document_id == document.id))
        for index, chunk in enumerate(chunks):
            db.add(
                KnowledgeChunk(
                    company_id=company_id,
                    document_id=document.id,
                    asset_id=document.asset_id,
                    chunk_index=index,
                    page_number=chunk.page_number,
                    content=chunk.content,
                    token_count=chunk.token_count,
                    embedding=embeddings[index] if embeddings else None,
                )
            )
        document.index_status = DocumentIndexStatus.READY
        document.indexed_at = datetime.now(UTC)
        document.index_error = None
        document.content_hash = content_hash
        document.chunk_count = len(chunks)
        document.embedded_chunk_count = len(embeddings)
        document.embedding_model = provider.embedding_model if provider else None
        db.commit()
        return _index_response(document, "Documento indexado correctamente")
    except UnsupportedDocumentError as exc:
        db.rollback()
        _set_index_error(db, document, DocumentIndexStatus.UNSUPPORTED, str(exc))
        return _index_response(document, str(exc))
    except (EmptyDocumentError, ValueError) as exc:
        db.rollback()
        _set_index_error(db, document, DocumentIndexStatus.FAILED, str(exc))
        return _index_response(document, str(exc))
    except Exception as exc:
        db.rollback()
        _set_index_error(
            db,
            document,
            DocumentIndexStatus.FAILED,
            "No se pudo completar la indexacion documental",
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="No se pudo completar la indexacion documental",
        ) from exc


def index_documents(
    db: Session,
    company_id: uuid.UUID,
    storage: StorageService,
    force: bool = False,
    provider: OpenAIKnowledgeProvider | None = None,
) -> BulkIndexRead:
    query = select(TechnicalDocument.id).where(TechnicalDocument.company_id == company_id)
    if not force:
        query = query.where(
            TechnicalDocument.index_status.in_(
                [DocumentIndexStatus.PENDING, DocumentIndexStatus.FAILED]
            )
        )
    document_ids = list(db.scalars(query.order_by(TechnicalDocument.uploaded_at)))
    indexed = failed = unsupported = 0
    for document_id in document_ids:
        try:
            result = index_document(db, company_id, document_id, storage, force, provider)
        except HTTPException:
            failed += 1
            continue
        if result.status == DocumentIndexStatus.READY:
            indexed += 1
        elif result.status == DocumentIndexStatus.UNSUPPORTED:
            unsupported += 1
        else:
            failed += 1
    return BulkIndexRead(indexed=indexed, failed=failed, unsupported=unsupported)


def query_knowledge(
    db: Session,
    current_user: User,
    question: str,
    asset_id: uuid.UUID | None,
    top_k: int,
) -> KnowledgeAnswerRead:
    started = time.perf_counter()
    clean_question = " ".join(question.split())
    if asset_id:
        asset = db.scalar(
            select(Asset).where(Asset.id == asset_id, Asset.company_id == current_user.company_id)
        )
        if not asset:
            raise HTTPException(status_code=422, detail="Activo no valido")

    provider = get_openai_provider()
    scored = _semantic_retrieve(
        db, current_user.company_id, clean_question, asset_id, top_k, provider
    )
    used_semantic = bool(scored) and provider is not None
    if not scored:
        scored = _local_retrieve(db, current_user.company_id, clean_question, asset_id, top_k)

    sources = [_source_read(item) for item in scored]
    if not scored:
        answer = (
            "No hay evidencia suficiente en la documentacion indexada para responder. "
            "Prueba con otra formulacion o revisa el estado de la base documental."
        )
        mode = "insufficient"
        provider_name = "local"
        model = None
        confidence = 0.0
    elif provider:
        try:
            answer = provider.answer(clean_question, [item.chunk.content for item in scored])
            mode = "generative"
            provider_name = provider.name
            model = provider.chat_model
            confidence = _confidence(scored, used_semantic)
        except Exception:
            answer = _extractive_answer(clean_question, scored)
            mode = "extractive"
            provider_name = "local-fallback"
            model = None
            confidence = _confidence(scored, False)
    else:
        answer = _extractive_answer(clean_question, scored)
        mode = "extractive"
        provider_name = "local"
        model = None
        confidence = _confidence(scored, False)

    duration_ms = round((time.perf_counter() - started) * 1000)
    query_log = AIQueryLog(
        company_id=current_user.company_id,
        user_id=current_user.id,
        asset_id=asset_id,
        question=clean_question,
        answer=answer,
        mode=mode,
        provider=provider_name,
        model=model,
        confidence=confidence,
        source_count=len(sources),
        duration_ms=duration_ms,
    )
    db.add(query_log)
    db.commit()
    return KnowledgeAnswerRead(
        query_id=query_log.id,
        answer=answer,
        mode=mode,
        provider=provider_name,
        model=model,
        confidence=confidence,
        duration_ms=duration_ms,
        sources=sources,
    )


def query_history(db: Session, current_user: User, limit: int) -> list[KnowledgeHistoryRead]:
    rows = db.scalars(
        select(AIQueryLog)
        .where(
            AIQueryLog.company_id == current_user.company_id,
            AIQueryLog.user_id == current_user.id,
        )
        .order_by(AIQueryLog.created_at.desc())
        .limit(limit)
    )
    return [KnowledgeHistoryRead.model_validate(row, from_attributes=True) for row in rows]


def _semantic_retrieve(
    db: Session,
    company_id: uuid.UUID,
    question: str,
    asset_id: uuid.UUID | None,
    top_k: int,
    provider: OpenAIKnowledgeProvider | None,
) -> list[ScoredChunk]:
    if not provider or db.bind is None or db.bind.dialect.name != "postgresql":
        return []
    try:
        query_embedding = provider.embed([question])[0]
        distance = KnowledgeChunk.embedding.cosine_distance(query_embedding)
        query = (
            select(KnowledgeChunk, distance.label("distance"))
            .options(
                joinedload(KnowledgeChunk.document).joinedload(TechnicalDocument.asset),
                joinedload(KnowledgeChunk.asset),
            )
            .where(
                KnowledgeChunk.company_id == company_id,
                KnowledgeChunk.embedding.is_not(None),
                KnowledgeChunk.document.has(
                    TechnicalDocument.index_status == DocumentIndexStatus.READY
                ),
            )
        )
        if asset_id:
            query = query.where(KnowledgeChunk.asset_id == asset_id)
        rows = db.execute(query.order_by(distance).limit(top_k * 2)).all()
        scored = [
            ScoredChunk(chunk=row[0], score=max(0.0, 1.0 - float(row[1]))) for row in rows
        ]
        if not scored or scored[0].score < settings.rag_min_semantic_score:
            return []
        minimum_score = max(
            settings.rag_min_semantic_score,
            scored[0].score * settings.rag_relative_score_floor,
        )
        return [item for item in scored if item.score >= minimum_score][:top_k]
    except Exception:
        return []


def _local_retrieve(
    db: Session,
    company_id: uuid.UUID,
    question: str,
    asset_id: uuid.UUID | None,
    top_k: int,
) -> list[ScoredChunk]:
    query = (
        select(KnowledgeChunk)
        .options(
            joinedload(KnowledgeChunk.document).joinedload(TechnicalDocument.asset),
            joinedload(KnowledgeChunk.asset),
        )
        .where(
            KnowledgeChunk.company_id == company_id,
            KnowledgeChunk.document.has(
                TechnicalDocument.index_status == DocumentIndexStatus.READY
            ),
        )
    )
    if asset_id:
        query = query.where(KnowledgeChunk.asset_id == asset_id)
    chunks = list(db.scalars(query.limit(5000)).unique())
    terms = _terms(question)
    if not terms:
        return []
    normalized_question = _normalize(question)
    scored: list[ScoredChunk] = []
    for chunk in chunks:
        searchable = " ".join(
            [
                chunk.document.name,
                chunk.document.original_name,
                chunk.asset.code,
                chunk.asset.name,
                chunk.content,
            ]
        )
        normalized_content = _normalize(searchable)
        counts = Counter(_terms(searchable))
        overlap = sum(math.log1p(counts[term]) for term in terms if counts[term])
        if overlap <= 0:
            continue
        phrase_boost = 1.5 if normalized_question in normalized_content else 0.0
        length_penalty = max(1.0, math.log10(max(len(normalized_content), 10)))
        score = (overlap + phrase_boost) / length_penalty
        scored.append(ScoredChunk(chunk=chunk, score=score))
    ordered = sorted(scored, key=lambda item: item.score, reverse=True)
    if not ordered:
        return []
    minimum_score = ordered[0].score * 0.45
    return [item for item in ordered if item.score >= minimum_score][:top_k]


def _extractive_answer(question: str, scored: list[ScoredChunk]) -> str:
    terms = _terms(question)
    candidates: list[tuple[float, str, int]] = []
    for source_index, item in enumerate(scored, start=1):
        sentences = re.split(r"(?<=[.!?])\s+|\n+", item.chunk.content)
        for sentence in sentences:
            clean = " ".join(sentence.split()).strip()
            if len(clean) < 20:
                continue
            sentence_terms = Counter(_terms(clean))
            score = sum(sentence_terms[term] for term in terms)
            if score:
                candidates.append((score + item.score, clean, source_index))
    candidates.sort(key=lambda value: value[0], reverse=True)
    selected: list[tuple[str, int]] = []
    seen: set[str] = set()
    for _, sentence, source_index in candidates:
        key = _normalize(sentence)
        if key in seen:
            continue
        seen.add(key)
        selected.append((sentence, source_index))
        if len(selected) == 4:
            break
    if not selected:
        selected = [
            (item.chunk.content[:400].strip(), index) for index, item in enumerate(scored[:2], 1)
        ]
    evidence = "\n".join(f"- {sentence} [{source_index}]" for sentence, source_index in selected)
    return f"La documentacion indexada aporta esta evidencia:\n\n{evidence}"


def _source_read(item: ScoredChunk) -> KnowledgeSourceRead:
    document = item.chunk.document
    return KnowledgeSourceRead(
        chunk_id=item.chunk.id,
        document_id=document.id,
        document_name=document.name,
        original_name=document.original_name,
        asset_id=document.asset_id,
        asset_code=document.asset.code,
        asset_name=document.asset.name,
        page_number=item.chunk.page_number,
        excerpt=item.chunk.content[:700],
        score=round(item.score, 4),
    )


def _confidence(scored: list[ScoredChunk], semantic: bool) -> float:
    if not scored:
        return 0.0
    if semantic:
        return round(min(0.95, max(0.2, scored[0].score)), 2)
    return round(min(0.85, 0.35 + scored[0].score / 4), 2)


def _index_response(document: TechnicalDocument, message: str) -> DocumentIndexRead:
    return DocumentIndexRead(
        document_id=document.id,
        status=document.index_status,
        chunks=document.chunk_count,
        embedded_chunks=document.embedded_chunk_count,
        embedding_model=document.embedding_model,
        message=message,
    )


def _set_index_error(
    db: Session,
    document: TechnicalDocument,
    index_status: DocumentIndexStatus,
    message: str,
) -> None:
    document.index_status = index_status
    document.index_error = message[:500]
    document.chunk_count = 0
    document.embedded_chunk_count = 0
    document.embedding_model = None
    db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.document_id == document.id))
    db.commit()


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.lower())
    return "".join(character for character in normalized if not unicodedata.combining(character))


def _terms(value: str) -> list[str]:
    return [
        token for token in re.findall(r"[a-z0-9]{2,}", _normalize(value)) if token not in STOP_WORDS
    ]
