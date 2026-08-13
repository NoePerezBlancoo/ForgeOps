import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_roles
from app.core.database import get_db
from app.core.enums import UserRole
from app.core.rate_limit import rate_limit
from app.core.schemas import MessageResponse
from app.invitations.models import UserInvitation
from app.invitations.schemas import (
    UserInvitationAccept,
    UserInvitationCreate,
    UserInvitationList,
    UserInvitationPreview,
    UserInvitationRead,
    UserInvitationToken,
)
from app.invitations.service import (
    accept_invitation,
    create_invitation,
    list_invitations,
    preview_invitation,
    resend_invitation,
    revoke_invitation,
)
from app.users.models import User

router = APIRouter(prefix="/invitations", tags=["Invitaciones"])
administrators = require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)


@router.post(
    "/preview",
    response_model=UserInvitationPreview,
    dependencies=[Depends(rate_limit("invitation_preview", "rate_limit_invitation"))],
)
def preview(
    payload: UserInvitationToken,
    db: Session = Depends(get_db),
) -> UserInvitationPreview:
    invitation, company = preview_invitation(db, payload.token)
    return UserInvitationPreview(
        company_name=company.name,
        email=invitation.email,
        full_name=invitation.full_name,
        role=invitation.role,
        expires_at=invitation.expires_at,
    )


@router.post(
    "/accept",
    response_model=MessageResponse,
    dependencies=[Depends(rate_limit("invitation_accept", "rate_limit_invitation"))],
)
def accept(
    payload: UserInvitationAccept,
    db: Session = Depends(get_db),
) -> MessageResponse:
    accept_invitation(db, payload)
    return MessageResponse(message="Cuenta activada. Ya puedes iniciar sesion")


@router.get("", response_model=UserInvitationList)
def index(
    db: Session = Depends(get_db),
    current_user: User = Depends(administrators),
) -> UserInvitationList:
    items, pending = list_invitations(db, current_user)
    return UserInvitationList(
        items=[UserInvitationRead.model_validate(item) for item in items],
        pending=pending,
    )


@router.post("", response_model=UserInvitationRead, status_code=status.HTTP_201_CREATED)
def store(
    payload: UserInvitationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(administrators),
) -> UserInvitation:
    return create_invitation(db, current_user, payload)


@router.post("/{invitation_id}/resend", response_model=UserInvitationRead)
def resend(
    invitation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(administrators),
) -> UserInvitation:
    return resend_invitation(db, current_user, invitation_id)


@router.post("/{invitation_id}/revoke", response_model=UserInvitationRead)
def revoke(
    invitation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(administrators),
) -> UserInvitation:
    return revoke_invitation(db, current_user, invitation_id)
