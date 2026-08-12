import base64
import hashlib
import hmac
from datetime import UTC, datetime

import pyotp
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def generate_mfa_secret() -> str:
    return pyotp.random_base32()


def encrypt_mfa_secret(secret: str) -> str:
    return _fernet().encrypt(secret.encode("ascii")).decode("ascii")


def decrypt_mfa_secret(encrypted: str) -> str:
    try:
        return _fernet().decrypt(encrypted.encode("ascii")).decode("ascii")
    except InvalidToken as exc:
        raise ValueError("No se pudo descifrar la configuracion MFA") from exc


def verify_mfa_code(encrypted: str, code: str) -> int | None:
    secret = decrypt_mfa_secret(encrypted)
    totp = pyotp.TOTP(secret)
    current_counter = int(datetime.now(UTC).timestamp()) // totp.interval
    for counter in range(current_counter - 1, current_counter + 2):
        if hmac.compare_digest(totp.at(counter * totp.interval), code):
            return counter
    return None


def provisioning_uri(secret: str, email: str) -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name="ForgeOps Control")


def _fernet() -> Fernet:
    digest = hashlib.sha256(settings.secret_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))
