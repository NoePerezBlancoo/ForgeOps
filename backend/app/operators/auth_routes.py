from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import rate_limit
from app.core.schemas import MessageResponse
from app.operators.auth_service import (
    authenticate_operator,
    change_operator_password,
    issue_operator_session,
    revoke_operator_session,
    rotate_operator_session,
)
from app.operators.dependencies import get_current_operator
from app.operators.models import PlatformOperator
from app.operators.schemas import (
    OperatorLoginRequest,
    OperatorPasswordChange,
    OperatorRead,
    OperatorTokenResponse,
    RefreshRequest,
)

router = APIRouter(prefix="/operator-auth", tags=["Control de plataforma"])
OPERATOR_REFRESH_COOKIE = "forgeops_operator_refresh"


def _set_operator_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        OPERATOR_REFRESH_COOKIE,
        token,
        max_age=settings.operator_refresh_token_hours * 3600,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        domain=settings.cookie_domain,
        path="/api/v1/operator-auth",
    )


@router.post(
    "/login",
    response_model=OperatorTokenResponse,
    dependencies=[Depends(rate_limit("operator_login", "rate_limit_login"))],
)
def login(
    payload: OperatorLoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> OperatorTokenResponse:
    ip_address = request.client.host if request.client else None
    operator = authenticate_operator(
        db, payload.email, payload.password, payload.totp_code, ip_address
    )
    access_token, refresh_token = issue_operator_session(db, operator, ip_address)
    _set_operator_cookie(response, refresh_token)
    return OperatorTokenResponse(
        access_token=access_token,
        expires_in=settings.operator_access_token_minutes * 60,
        operator=OperatorRead.model_validate(operator),
    )


@router.post("/refresh", response_model=OperatorTokenResponse)
def refresh(
    request: Request,
    response: Response,
    payload: RefreshRequest | None = None,
    cookie_token: str | None = Cookie(default=None, alias=OPERATOR_REFRESH_COOKIE),
    db: Session = Depends(get_db),
) -> OperatorTokenResponse:
    refresh_token = cookie_token or (payload.refresh_token if payload else None)
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No existe una sesion de operador renovable")
    operator, access_token, new_refresh_token = rotate_operator_session(
        db,
        refresh_token,
        request.client.host if request.client else None,
    )
    _set_operator_cookie(response, new_refresh_token)
    return OperatorTokenResponse(
        access_token=access_token,
        expires_in=settings.operator_access_token_minutes * 60,
        operator=OperatorRead.model_validate(operator),
    )


@router.post("/logout", response_model=MessageResponse)
def logout(
    response: Response,
    payload: RefreshRequest | None = None,
    cookie_token: str | None = Cookie(default=None, alias=OPERATOR_REFRESH_COOKIE),
    db: Session = Depends(get_db),
) -> MessageResponse:
    revoke_operator_session(db, cookie_token or (payload.refresh_token if payload else None))
    response.delete_cookie(
        OPERATOR_REFRESH_COOKIE,
        path="/api/v1/operator-auth",
        domain=settings.cookie_domain,
        secure=settings.cookie_secure,
        samesite="strict",
    )
    return MessageResponse(message="Sesion de operador cerrada")


@router.get("/me", response_model=OperatorRead)
def me(operator: PlatformOperator = Depends(get_current_operator)) -> PlatformOperator:
    return operator


@router.post("/password", status_code=status.HTTP_204_NO_CONTENT)
def update_password(
    payload: OperatorPasswordChange,
    db: Session = Depends(get_db),
    operator: PlatformOperator = Depends(get_current_operator),
) -> Response:
    change_operator_password(db, operator, payload)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
