from datetime import UTC, datetime

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.models import RefreshSession
from app.auth.schemas import (
    LoginRequest,
    RefreshRequest,
    SessionRead,
    SessionsRevokedRead,
    TokenResponse,
    TrialRegistration,
    UserPasswordChange,
)
from app.auth.security import token_digest
from app.auth.service import (
    authenticate,
    issue_session,
    revoke_session,
    rotate_session,
    token_expires_in,
)
from app.companies.trial_service import register_trial
from app.core.config import settings
from app.core.database import get_db
from app.core.schemas import MessageResponse
from app.users.models import User
from app.users.schemas import UserRead
from app.users.service import change_password, revoke_other_sessions

router = APIRouter(prefix="/auth", tags=["Autenticacion"])
REFRESH_COOKIE = "forgeops_refresh"


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        REFRESH_COOKIE,
        token,
        max_age=settings.refresh_token_days * 86400,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/api/v1/auth",
    )


@router.post("/register-trial", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def create_trial(
    payload: TrialRegistration,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> TokenResponse:
    user = register_trial(db, payload)
    access_token, refresh_token = issue_session(
        db, user, request.client.host if request.client else None
    )
    _set_refresh_cookie(response, refresh_token)
    return TokenResponse(
        access_token=access_token,
        expires_in=token_expires_in(),
        user=UserRead.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> TokenResponse:
    user = authenticate(db, payload.email, payload.password)
    access_token, refresh_token = issue_session(
        db, user, request.client.host if request.client else None
    )
    _set_refresh_cookie(response, refresh_token)
    return TokenResponse(
        access_token=access_token,
        expires_in=token_expires_in(),
        user=UserRead.model_validate(user),
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    payload: RefreshRequest | None,
    response: Response,
    cookie_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE),
    db: Session = Depends(get_db),
) -> TokenResponse:
    refresh_token = cookie_token or (payload.refresh_token if payload else None)
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No existe una sesion renovable",
        )
    user, access_token, new_refresh_token = rotate_session(db, refresh_token)
    _set_refresh_cookie(response, new_refresh_token)
    return TokenResponse(
        access_token=access_token,
        expires_in=token_expires_in(),
        user=UserRead.model_validate(user),
    )


@router.post("/logout", response_model=MessageResponse)
def logout(
    response: Response,
    payload: RefreshRequest | None = None,
    cookie_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE),
    db: Session = Depends(get_db),
) -> MessageResponse:
    revoke_session(db, cookie_token or (payload.refresh_token if payload else None))
    response.delete_cookie(REFRESH_COOKIE, path="/api/v1/auth")
    return MessageResponse(message="Sesion cerrada")


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.post("/password", status_code=status.HTTP_204_NO_CONTENT)
def update_password(
    payload: UserPasswordChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    change_password(db, current_user, payload)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/sessions", response_model=list[SessionRead])
def sessions(
    cookie_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SessionRead]:
    current_hash = token_digest(cookie_token) if cookie_token else None
    rows = db.scalars(
        select(RefreshSession)
        .where(
            RefreshSession.user_id == current_user.id,
            RefreshSession.revoked_at.is_(None),
            RefreshSession.expires_at > datetime.now(UTC),
        )
        .order_by(RefreshSession.created_at.desc())
    )
    return [
        SessionRead(
            id=session.id,
            created_at=session.created_at,
            expires_at=session.expires_at,
            current=session.token_hash == current_hash,
        )
        for session in rows
    ]


@router.post("/sessions/revoke-others", response_model=SessionsRevokedRead)
def close_other_sessions(
    cookie_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SessionsRevokedRead:
    current_hash = token_digest(cookie_token) if cookie_token else None
    return SessionsRevokedRead(
        revoked=revoke_other_sessions(db, current_user, current_hash)
    )
