import uuid
from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.auth.security import decode_token
from app.companies.entitlements import module_enabled
from app.core.database import get_db, set_database_context
from app.core.enums import CompanyModule, UserRole
from app.users.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


WRITE_WHITELIST = {
    "/api/v1/auth/password",
    "/api/v1/auth/sessions/revoke-others",
    "/api/v1/notifications/read-all",
}


def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar la sesion",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token, "access")
        if payload.get("actor", "user") != "user":
            raise ValueError("Tipo de sesion invalido")
        user_id = uuid.UUID(payload["sub"])
    except (ValueError, TypeError):
        raise credentials_error from None

    set_database_context(db, "auth")
    user = db.scalar(
        select(User)
        .options(joinedload(User.company))
        .where(User.id == user_id, User.active.is_(True))
    )
    if not user or not user.company.active:
        raise credentials_error
    set_database_context(db, "tenant", user.company_id)
    if (
        request.method not in {"GET", "HEAD", "OPTIONS"}
        and request.url.path not in WRITE_WHITELIST
        and not (
            request.method == "PATCH"
            and request.url.path.startswith("/api/v1/notifications/")
            and request.url.path.endswith("/read")
        )
        and not user.company.write_enabled
    ):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="La prueba ha finalizado. Activa un plan para continuar operando.",
        )
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


def require_module(module: CompanyModule) -> Callable:
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if not module_enabled(current_user.company, module):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Este modulo no esta activo para la empresa",
            )
        return current_user

    return dependency


def tenant_company_id(
    current_user: User, requested_company_id: uuid.UUID | None = None
) -> uuid.UUID:
    if current_user.role == UserRole.SUPER_ADMIN and requested_company_id:
        return requested_company_id
    return current_user.company_id
