import html
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit.service import add_audit_event
from app.auth.security import hash_password, token_digest
from app.companies.entitlements import effective_limits
from app.companies.models import Company
from app.core.config import settings
from app.core.database import set_database_context
from app.core.enums import UserRole
from app.email.service import EmailMessage, message_to_payload
from app.invitations.models import UserInvitation
from app.invitations.schemas import UserInvitationAccept, UserInvitationCreate
from app.jobs.service import enqueue_job
from app.users.models import User

ADMIN_ROLES = (UserRole.SUPER_ADMIN, UserRole.ADMIN)


def list_invitations(db: Session, current_user: User) -> tuple[list[UserInvitation], int]:
    invitations = list(
        db.scalars(
            select(UserInvitation)
            .where(UserInvitation.company_id == current_user.company_id)
            .order_by(UserInvitation.created_at.desc())
            .limit(250)
        )
    )
    return invitations, sum(invitation.status == "PENDING" for invitation in invitations)


def create_invitation(
    db: Session,
    current_user: User,
    payload: UserInvitationCreate,
) -> UserInvitation:
    _validate_role(current_user, payload.role)
    company = _locked_company(db, current_user.company_id)
    _ensure_email_available(db, company.id, payload.email)
    _ensure_seat_available(db, company)
    invitation, raw_token = _new_invitation(db, current_user, payload)
    add_audit_event(
        db,
        company.id,
        current_user.id,
        "INVITE",
        "USER_INVITATION",
        f"Invitacion enviada a {invitation.email}",
        invitation.id,
        {"role": invitation.role.value},
    )
    _queue_invitation_email(db, company, invitation, raw_token)
    return invitation


def resend_invitation(
    db: Session,
    current_user: User,
    invitation_id: uuid.UUID,
) -> UserInvitation:
    invitation = _get_for_update(db, current_user.company_id, invitation_id)
    if invitation.accepted_at:
        raise HTTPException(status_code=409, detail="La invitacion ya fue aceptada")
    company = _locked_company(db, current_user.company_id)
    invitation.revoked_at = datetime.now(UTC)
    db.flush()
    _ensure_email_available(db, current_user.company_id, invitation.email)
    _ensure_seat_available(db, company)
    payload = UserInvitationCreate(
        email=invitation.email,
        full_name=invitation.full_name,
        job_title=invitation.job_title,
        phone=invitation.phone,
        role=invitation.role,
    )
    replacement, raw_token = _new_invitation(db, current_user, payload)
    add_audit_event(
        db,
        current_user.company_id,
        current_user.id,
        "RESEND",
        "USER_INVITATION",
        f"Invitacion reenviada a {replacement.email}",
        replacement.id,
        {"replaces": str(invitation.id)},
    )
    _queue_invitation_email(db, company, replacement, raw_token)
    return replacement


def revoke_invitation(
    db: Session,
    current_user: User,
    invitation_id: uuid.UUID,
) -> UserInvitation:
    invitation = _get_for_update(db, current_user.company_id, invitation_id)
    if invitation.accepted_at:
        raise HTTPException(status_code=409, detail="La invitacion ya fue aceptada")
    if not invitation.revoked_at:
        invitation.revoked_at = datetime.now(UTC)
        add_audit_event(
            db,
            current_user.company_id,
            current_user.id,
            "REVOKE",
            "USER_INVITATION",
            f"Invitacion revocada para {invitation.email}",
            invitation.id,
        )
        db.commit()
    return invitation


def preview_invitation(db: Session, raw_token: str) -> tuple[UserInvitation, Company]:
    invitation = _valid_invitation_for_token(db, raw_token, lock=False)
    company = db.scalar(select(Company).where(Company.id == invitation.company_id))
    if not company or not company.write_enabled:
        raise _invalid_invitation()
    return invitation, company


def accept_invitation(db: Session, payload: UserInvitationAccept) -> User:
    invitation = _valid_invitation_for_token(db, payload.token, lock=True)
    set_database_context(db, "tenant", invitation.company_id)
    company = db.scalar(
        select(Company).where(Company.id == invitation.company_id).with_for_update()
    )
    if not company or not company.write_enabled:
        raise _invalid_invitation()
    _ensure_email_available(db, company.id, invitation.email, exclude=invitation.id)
    active_users = db.scalar(
        select(func.count(User.id)).where(
            User.company_id == company.id,
            User.active.is_(True),
        )
    ) or 0
    limit = effective_limits(company).get("users")
    if limit is not None and active_users >= limit:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La empresa ha alcanzado el limite de usuarios de su plan",
        )
    now = datetime.now(UTC)
    user = User(
        id=uuid.uuid4(),
        company_id=company.id,
        full_name=invitation.full_name,
        email=invitation.email,
        job_title=invitation.job_title,
        phone=invitation.phone,
        role=invitation.role,
        password_hash=hash_password(payload.password),
        password_changed_at=now,
        active=True,
    )
    db.add(user)
    db.flush()
    invitation.accepted_at = now
    invitation.accepted_user_id = user.id
    add_audit_event(
        db,
        company.id,
        user.id,
        "ACCEPT",
        "USER_INVITATION",
        f"Invitacion aceptada por {user.email}",
        invitation.id,
        {"user_id": str(user.id)},
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Ese correo ya tiene acceso a ForgeOps",
        ) from exc
    return user


def _new_invitation(
    db: Session,
    current_user: User,
    payload: UserInvitationCreate,
) -> tuple[UserInvitation, str]:
    raw_token = secrets.token_urlsafe(48)
    invitation = UserInvitation(
        id=uuid.uuid4(),
        company_id=current_user.company_id,
        email=payload.email,
        full_name=payload.full_name,
        job_title=payload.job_title,
        phone=payload.phone,
        role=payload.role,
        token_hash=token_digest(raw_token),
        inviter_id=current_user.id,
        expires_at=datetime.now(UTC) + timedelta(hours=settings.invitation_expiry_hours),
    )
    db.add(invitation)
    db.flush()
    return invitation, raw_token


def _queue_invitation_email(
    db: Session,
    company: Company,
    invitation: UserInvitation,
    raw_token: str,
) -> None:
    frontend_url = settings.frontend_url.split(",")[0].rstrip("/")
    invitation_url = f"{frontend_url}/accept-invitation?token={raw_token}"
    company_name = html.escape(company.name)
    recipient_name = html.escape(invitation.full_name)
    message = EmailMessage(
        recipient=invitation.email,
        subject=f"{company.name} te invita a ForgeOps",
        text_body=(
            f"{invitation.full_name}, {company.name} te ha invitado a ForgeOps. "
            f"Crea tu contrasena desde este enlace: {invitation_url}. "
            f"El enlace caduca en {settings.invitation_expiry_hours} horas."
        ),
        html_body=(
            f"<p>Hola {recipient_name},</p>"
            f"<p><strong>{company_name}</strong> te ha invitado a su espacio de ForgeOps.</p>"
            f'<p><a href="{invitation_url}">Activar mi cuenta</a></p>'
            f"<p>El enlace caduca en {settings.invitation_expiry_hours} horas.</p>"
        ),
        template="user_invitation",
    )
    enqueue_job(
        db,
        "EMAIL_SEND",
        message_to_payload(message),
        idempotency_key=f"user-invitation:{invitation.id}",
        company_id=invitation.company_id,
    )


def _valid_invitation_for_token(
    db: Session,
    raw_token: str,
    *,
    lock: bool,
) -> UserInvitation:
    set_database_context(db, "auth")
    query = select(UserInvitation).where(
        UserInvitation.token_hash == token_digest(raw_token)
    )
    if lock:
        query = query.with_for_update()
    invitation = db.scalar(query)
    if not invitation or invitation.status != "PENDING":
        raise _invalid_invitation()
    return invitation


def _get_for_update(
    db: Session,
    company_id: uuid.UUID,
    invitation_id: uuid.UUID,
) -> UserInvitation:
    invitation = db.scalar(
        select(UserInvitation)
        .where(
            UserInvitation.id == invitation_id,
            UserInvitation.company_id == company_id,
        )
        .with_for_update()
    )
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitacion no encontrada")
    return invitation


def _locked_company(db: Session, company_id: uuid.UUID) -> Company:
    company = db.scalar(select(Company).where(Company.id == company_id).with_for_update())
    if not company:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return company


def _ensure_email_available(
    db: Session,
    company_id: uuid.UUID,
    email: str,
    *,
    exclude: uuid.UUID | None = None,
) -> None:
    set_database_context(db, "auth")
    try:
        existing_user = db.scalar(select(User.id).where(User.email == email))
    finally:
        set_database_context(db, "tenant", company_id)
    if existing_user:
        raise HTTPException(status_code=409, detail="Ese correo ya tiene acceso a ForgeOps")
    pending_query = select(UserInvitation.id).where(
        UserInvitation.company_id == company_id,
        UserInvitation.email == email,
        UserInvitation.accepted_at.is_(None),
        UserInvitation.revoked_at.is_(None),
        UserInvitation.expires_at > datetime.now(UTC),
    )
    if exclude:
        pending_query = pending_query.where(UserInvitation.id != exclude)
    pending = db.scalar(pending_query)
    if pending:
        raise HTTPException(status_code=409, detail="Ya existe una invitacion pendiente")


def _ensure_seat_available(db: Session, company: Company) -> None:
    limit = effective_limits(company).get("users")
    if limit is None:
        return
    active_users = db.scalar(
        select(func.count(User.id)).where(
            User.company_id == company.id,
            User.active.is_(True),
        )
    ) or 0
    pending = db.scalar(
        select(func.count(UserInvitation.id)).where(
            UserInvitation.company_id == company.id,
            UserInvitation.accepted_at.is_(None),
            UserInvitation.revoked_at.is_(None),
            UserInvitation.expires_at > datetime.now(UTC),
        )
    ) or 0
    if active_users + pending >= limit:
        raise HTTPException(
            status_code=409,
            detail="La empresa ha alcanzado el limite de usuarios de su plan",
        )


def _validate_role(current_user: User, role: UserRole) -> None:
    if role == UserRole.SUPER_ADMIN and current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="No puedes invitar un superadministrador")


def _invalid_invitation() -> HTTPException:
    return HTTPException(status_code=422, detail="La invitacion no es valida o ha caducado")
