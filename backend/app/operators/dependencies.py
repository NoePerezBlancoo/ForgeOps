import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import decode_token
from app.core.database import get_db
from app.operators.models import PlatformOperator

operator_oauth2 = OAuth2PasswordBearer(tokenUrl="/api/v1/operator-auth/login")


def get_current_operator(
    token: str = Depends(operator_oauth2),
    db: Session = Depends(get_db),
) -> PlatformOperator:
    error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar la sesion de operador",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token, "access")
        if payload.get("actor") != "operator":
            raise ValueError("Tipo de sesion invalido")
        operator_id = uuid.UUID(payload["sub"])
    except (ValueError, TypeError):
        raise error from None
    operator = db.scalar(
        select(PlatformOperator).where(
            PlatformOperator.id == operator_id,
            PlatformOperator.active.is_(True),
        )
    )
    if not operator:
        raise error
    return operator
