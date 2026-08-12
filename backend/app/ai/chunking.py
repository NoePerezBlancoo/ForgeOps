import re
from dataclasses import dataclass

from app.ai.extractors import ExtractedSection


@dataclass(frozen=True)
class TextChunk:
    content: str
    page_number: int | None
    token_count: int


def chunk_sections(
    sections: list[ExtractedSection], target_chars: int, overlap_chars: int
) -> list[TextChunk]:
    chunks: list[TextChunk] = []
    for section in sections:
        chunks.extend(_chunk_text(section.text, section.page_number, target_chars, overlap_chars))
    return chunks


def _chunk_text(
    text: str, page_number: int | None, target_chars: int, overlap_chars: int
) -> list[TextChunk]:
    if target_chars < 300 or overlap_chars < 0 or overlap_chars >= target_chars:
        raise ValueError("Configuracion de fragmentacion no valida")
    result: list[TextChunk] = []
    start = 0
    while start < len(text):
        end = min(start + target_chars, len(text))
        if end < len(text):
            boundary = max(
                text.rfind("\n", start + target_chars // 2, end),
                text.rfind(". ", start + target_chars // 2, end),
                text.rfind(" ", start + target_chars // 2, end),
            )
            if boundary > start:
                end = boundary + 1
        content = text[start:end].strip()
        if content:
            result.append(
                TextChunk(
                    content=content,
                    page_number=page_number,
                    token_count=len(re.findall(r"\w+", content, flags=re.UNICODE)),
                )
            )
        if end >= len(text):
            break
        start = max(end - overlap_chars, start + 1)
    return result
