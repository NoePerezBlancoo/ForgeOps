from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class KnowledgeQuery:
    company_id: UUID
    question: str
    asset_id: UUID | None = None


@dataclass(frozen=True)
class KnowledgeResult:
    answer: str
    source_ids: tuple[UUID, ...]


class AIKnowledgeService(Protocol):
    async def query(self, request: KnowledgeQuery) -> KnowledgeResult: ...
