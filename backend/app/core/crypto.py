import base64
import hashlib
import json

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def encrypt_json(payload: dict) -> str:
    serialized = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return _fernet().encrypt(serialized).decode("ascii")


def decrypt_json(encrypted: str) -> dict:
    try:
        value = _fernet().decrypt(encrypted.encode("ascii"))
        payload = json.loads(value)
    except (InvalidToken, ValueError, TypeError) as exc:
        raise ValueError("No se pudo descifrar el payload") from exc
    if not isinstance(payload, dict):
        raise ValueError("El payload cifrado no es un objeto")
    return payload


def _fernet() -> Fernet:
    digest = hashlib.sha256(settings.secret_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))
