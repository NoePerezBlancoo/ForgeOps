import uuid
from datetime import UTC, datetime
from pathlib import Path

from fastapi import HTTPException, status

from app.core.config import settings

ALLOWED_EXTENSIONS = {
    ".doc",
    ".docx",
    ".jpeg",
    ".jpg",
    ".pdf",
    ".png",
    ".txt",
    ".webp",
    ".xls",
    ".xlsx",
}


class LocalDocumentStorage:
    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root or settings.upload_directory).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def store(self, company_id: uuid.UUID, original_name: str, content: bytes) -> str:
        extension = Path(original_name).suffix.lower()
        if extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Formato de archivo no permitido",
            )

        now = datetime.now(UTC)
        key = Path(str(company_id), str(now.year), f"{now.month:02d}", f"{uuid.uuid4()}{extension}")
        destination = self._resolve(key)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        return key.as_posix()

    def path_for(self, storage_key: str) -> Path:
        path = self._resolve(Path(storage_key))
        if not path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Archivo no encontrado"
            )
        return path

    def delete(self, storage_key: str) -> None:
        path = self._resolve(Path(storage_key))
        if path.is_file():
            path.unlink()

    def _resolve(self, relative_path: Path) -> Path:
        if relative_path.is_absolute():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ruta no valida")
        resolved = (self.root / relative_path).resolve()
        if not resolved.is_relative_to(self.root):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ruta no valida")
        return resolved


def get_document_storage() -> LocalDocumentStorage:
    return LocalDocumentStorage()
