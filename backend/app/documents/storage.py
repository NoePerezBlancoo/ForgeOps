import uuid
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Protocol

import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import HTTPException, status

from app.core.config import settings

ALLOWED_MIME_TYPES = {
    ".doc": {"application/msword", "application/octet-stream"},
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/zip",
        "application/octet-stream",
    },
    ".jpeg": {"image/jpeg", "application/octet-stream"},
    ".jpg": {"image/jpeg", "application/octet-stream"},
    ".pdf": {"application/pdf", "application/octet-stream"},
    ".png": {"image/png", "application/octet-stream"},
    ".txt": {"text/plain", "application/octet-stream"},
    ".webp": {"image/webp", "application/octet-stream"},
    ".xls": {"application/vnd.ms-excel", "application/octet-stream"},
    ".xlsx": {
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/zip",
        "application/octet-stream",
    },
}

CANONICAL_MIME_TYPES = {
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".jpeg": "image/jpeg",
    ".jpg": "image/jpeg",
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".txt": "text/plain",
    ".webp": "image/webp",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


@dataclass(frozen=True)
class StoredFile:
    key: str
    original_name: str
    mime_type: str
    size: int


@dataclass(frozen=True)
class DownloadTarget:
    local_path: Path | None = None
    signed_url: str | None = None


class StorageService(Protocol):
    def store(
        self,
        company_id: uuid.UUID,
        asset_id: uuid.UUID,
        original_name: str,
        content: bytes,
        declared_mime: str | None,
    ) -> StoredFile: ...

    def read(self, company_id: uuid.UUID, storage_key: str) -> bytes: ...

    def download(self, company_id: uuid.UUID, storage_key: str) -> DownloadTarget: ...

    def delete(self, company_id: uuid.UUID, storage_key: str) -> None: ...


class LocalStorageService:
    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root or settings.upload_directory).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def store(
        self,
        company_id: uuid.UUID,
        asset_id: uuid.UUID,
        original_name: str,
        content: bytes,
        declared_mime: str | None,
    ) -> StoredFile:
        stored = validate_upload(company_id, asset_id, original_name, content, declared_mime)
        destination = self._resolve(stored.key)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        return stored

    def read(self, company_id: uuid.UUID, storage_key: str) -> bytes:
        return self._existing(company_id, storage_key).read_bytes()

    def download(self, company_id: uuid.UUID, storage_key: str) -> DownloadTarget:
        return DownloadTarget(local_path=self._existing(company_id, storage_key))

    def delete(self, company_id: uuid.UUID, storage_key: str) -> None:
        path = self._resolve(_tenant_key(company_id, storage_key))
        if path.is_file():
            path.unlink()

    def _existing(self, company_id: uuid.UUID, storage_key: str) -> Path:
        path = self._resolve(_tenant_key(company_id, storage_key))
        if not path.is_file():
            raise HTTPException(status_code=404, detail="Archivo no encontrado")
        return path

    def _resolve(self, storage_key: str) -> Path:
        relative = Path(storage_key)
        if relative.is_absolute():
            raise HTTPException(status_code=400, detail="Ruta de archivo no valida")
        resolved = (self.root / relative).resolve()
        if not resolved.is_relative_to(self.root):
            raise HTTPException(status_code=400, detail="Ruta de archivo no valida")
        return resolved


class S3StorageService:
    def __init__(self) -> None:
        self.bucket = settings.s3_bucket or ""
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": "path" if settings.s3_force_path_style else "virtual"},
            ),
        )

    def store(
        self,
        company_id: uuid.UUID,
        asset_id: uuid.UUID,
        original_name: str,
        content: bytes,
        declared_mime: str | None,
    ) -> StoredFile:
        stored = validate_upload(company_id, asset_id, original_name, content, declared_mime)
        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=stored.key,
                Body=content,
                ContentType=stored.mime_type,
                Metadata={"company-id": str(company_id), "asset-id": str(asset_id)},
            )
        except (BotoCoreError, ClientError) as exc:
            raise HTTPException(
                status_code=503, detail="El almacenamiento no esta disponible"
            ) from exc
        return stored

    def read(self, company_id: uuid.UUID, storage_key: str) -> bytes:
        key = _tenant_key(company_id, storage_key)
        try:
            return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()
        except self.client.exceptions.NoSuchKey as exc:
            raise HTTPException(status_code=404, detail="Archivo no encontrado") from exc
        except (BotoCoreError, ClientError) as exc:
            raise HTTPException(
                status_code=503, detail="El almacenamiento no esta disponible"
            ) from exc

    def download(self, company_id: uuid.UUID, storage_key: str) -> DownloadTarget:
        key = _tenant_key(company_id, storage_key)
        try:
            url = self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=settings.storage_signed_url_seconds,
            )
        except (BotoCoreError, ClientError) as exc:
            raise HTTPException(status_code=503, detail="No se pudo preparar la descarga") from exc
        return DownloadTarget(signed_url=url)

    def delete(self, company_id: uuid.UUID, storage_key: str) -> None:
        key = _tenant_key(company_id, storage_key)
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
        except (BotoCoreError, ClientError) as exc:
            raise HTTPException(
                status_code=503, detail="El almacenamiento no esta disponible"
            ) from exc


def validate_upload(
    company_id: uuid.UUID,
    asset_id: uuid.UUID,
    original_name: str,
    content: bytes,
    declared_mime: str | None,
) -> StoredFile:
    clean_name = Path(original_name.replace("\\", "/")).name.strip() or "documento"
    extension = Path(clean_name).suffix.lower()
    if extension not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=422, detail="Formato de archivo no permitido")
    normalized_mime = (declared_mime or "application/octet-stream").split(";", 1)[0].lower()
    if normalized_mime not in ALLOWED_MIME_TYPES[extension]:
        raise HTTPException(status_code=422, detail="El tipo MIME no coincide con la extension")
    if not _signature_matches(extension, content):
        raise HTTPException(
            status_code=422,
            detail="El contenido no coincide con el formato indicado",
        )
    key = (
        PurePosixPath("companies")
        / str(company_id)
        / "assets"
        / str(asset_id)
        / "documents"
        / f"{uuid.uuid4()}{extension}"
    )
    return StoredFile(
        key=str(key),
        original_name=clean_name[:255],
        mime_type=CANONICAL_MIME_TYPES[extension],
        size=len(content),
    )


def _signature_matches(extension: str, content: bytes) -> bool:
    if extension == ".pdf":
        return content.startswith(b"%PDF-")
    if extension == ".png":
        return content.startswith(b"\x89PNG\r\n\x1a\n")
    if extension in {".jpg", ".jpeg"}:
        return content.startswith(b"\xff\xd8\xff")
    if extension == ".webp":
        return len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP"
    if extension in {".docx", ".xlsx"}:
        return content.startswith(b"PK\x03\x04")
    if extension in {".doc", ".xls"}:
        return content.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1")
    if extension == ".txt":
        return b"\x00" not in content[:8192]
    return False


def _tenant_key(company_id: uuid.UUID, storage_key: str) -> str:
    key = PurePosixPath(storage_key)
    expected = ("companies", str(company_id))
    if key.is_absolute() or ".." in key.parts or key.parts[:2] != expected:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archivo no encontrado")
    return str(key)


def get_document_storage() -> StorageService:
    if settings.storage_backend == "s3":
        return S3StorageService()
    return LocalStorageService()


LocalDocumentStorage = LocalStorageService
