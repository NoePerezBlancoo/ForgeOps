import uuid
from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.auth.security import decode_token
from app.core.database import get_db
from app.core.enums import UserRole
from app.users.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar la sesion",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token, "access")
        user_id = uuid.UUID(payload["sub"])
    except (ValueError, TypeError):
        raise credentials_error from None

    user = db.scalar(
        select(User)
        .options(joinedload(User.company))
        .where(User.id == user_id, User.active.is_(True))
    )
    if not user or not user.company.active:
        raise credentials_error
    return user


def require_roles(*roles: UserRole) -> Callable:
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para realizar esta accion",
            )
        return current_user

    return dependency


def tenant_company_id(
    current_user: User, requested_company_id: uuid.UUID | None = None
) -> uuid.UUID:
    if current_user.role == UserRole.SUPER_ADMIN and requested_company_id:
        return requested_company_id
    return current_user.company_id
