from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID


@dataclass(frozen=True)
class IntegrationEvent:
    company_id: UUID
    source: str
    occurred_at: datetime
    payload: dict[str, Any]


class IntegrationAdapter(Protocol):
    name: str

    async def healthcheck(self) -> bool: ...

    async def collect(self, company_id: UUID) -> list[IntegrationEvent]: ...
