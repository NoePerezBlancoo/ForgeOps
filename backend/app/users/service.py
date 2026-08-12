import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.audit.service import add_audit_event
from app.auth.models import RefreshSession
from app.auth.security import hash_password, verify_password
from app.companies.entitlements import enforce_limit
from app.core.enums import UserRole
from app.users.models import User
from app.users.schemas import UserCreate, UserPasswordChange, UserPasswordReset, UserUpdate

ADMIN_ROLES = (UserRole.SUPER_ADMIN, UserRole.ADMIN)


def list_users(db: Session, company_id: uuid.UUID, active_only: bool) -> list[User]:
    query = (
        select(User)
        .options(joinedload(User.company))
        .where(User.company_id == company_id)
        .order_by(User.active.desc(), User.full_name)
    )
    if active_only:
        query = query.where(User.active.is_(True))
    return list(db.scalars(query).unique())


def get_user(db: Session, company_id: uuid.UUID, user_id: uuid.UUID) -> User:
    user = db.scalar(
        select(User)
        .options(joinedload(User.company))
        .where(User.id == user_id, User.company_id == company_id)
    )
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user


def create_user(db: Session, current_user: User, payload: UserCreate) -> User:
    _validate_managed_role(current_user, payload.role)
    enforce_limit(db, current_user.company, "users")
    user = User(
        id=uuid.uuid4(),
        company_id=current_user.company_id,
        full_name=payload.full_name.strip(),
        email=payload.email,
        job_title=payload.job_title.strip() if payload.job_title else None,
        phone=payload.phone.strip() if payload.phone else None,
        role=payload.role,
        password_hash=hash_password(payload.password),
        password_changed_at=datetime.now(UTC),
    )
    db.add(user)
    add_audit_event(
        db,
        current_user.company_id,
        current_user.id,
        "CREATE",
        "USER",
        f"Usuario {user.email} creado con rol {user.role.value}",
        user.id,
    )
    _commit_email(db)
    return get_user(db, current_user.company_id, user.id)


def update_user(
    db: Session, current_user: User, user_id: uuid.UUID, payload: UserUpdate
) -> User:
    user = get_user(db, current_user.company_id, user_id)
    changes = payload.model_dump(exclude_unset=True)
    if user.role == UserRole.SUPER_ADMIN and current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="No puedes modificar un superadministrador")
    if changes.get("role"):
        _validate_managed_role(current_user, changes["role"])
    if user.id == current_user.id and changes.get("active") is False:
        raise HTTPException(status_code=409, detail="No puedes desactivar tu propia cuenta")
    removing_admin = user.active and user.role in ADMIN_ROLES and (
        changes.get("active") is False
        or (changes.get("role") is not None and changes["role"] not in ADMIN_ROLES)
    )
    if removing_admin and _active_admin_count(db, current_user.company_id) <= 1:
        raise HTTPException(
            status_code=409, detail="La empresa debe conservar al menos un administrador activo"
        )
    for field, value in changes.items():
        if field in {"full_name", "job_title", "phone"} and isinstance(value, str):
            value = value.strip() or None
        setattr(user, field, value)
    if changes.get("active") is False:
        _revoke_user_sessions(db, user.id)
    action = "DEACTIVATE" if changes.get("active") is False else "UPDATE"
    if changes.get("active") is True:
        action = "ACTIVATE"
    add_audit_event(
        db,
        current_user.company_id,
        current_user.id,
        action,
        "USER",
        f"Usuario {user.email} actualizado",
        user.id,
        {"fields": sorted(changes)},
    )
    _commit_email(db)
    return get_user(db, current_user.company_id, user.id)


def reset_user_password(
    db: Session, current_user: User, user_id: uuid.UUID, payload: UserPasswordReset
) -> User:
    user = get_user(db, current_user.company_id, user_id)
    if user.role == UserRole.SUPER_ADMIN and current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="No puedes modificar un superadministrador")
    user.password_hash = hash_password(payload.password)
    user.password_changed_at = datetime.now(UTC)
    _revoke_user_sessions(db, user.id)
    add_audit_event(
        db,
        current_user.company_id,
        current_user.id,
        "PASSWORD_RESET",
        "USER",
        f"Contrasena restablecida para {user.email}",
        user.id,
    )
    db.commit()
    return get_user(db, current_user.company_id, user.id)


def change_password(db: Session, current_user: User, payload: UserPasswordChange) -> None:
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=422, detail="La contrasena actual no es correcta")
    if verify_password(payload.password, current_user.password_hash):
        raise HTTPException(status_code=422, detail="La nueva contrasena debe ser diferente")
    current_user.password_hash = hash_password(payload.password)
    current_user.password_changed_at = datetime.now(UTC)
    _revoke_user_sessions(db, current_user.id)
    add_audit_event(
        db,
        current_user.company_id,
        current_user.id,
        "PASSWORD_CHANGE",
        "USER",
        "Contrasena de acceso actualizada",
        current_user.id,
    )
    db.commit()


def revoke_other_sessions(db: Session, current_user: User, current_token_hash: str | None) -> int:
    now = datetime.now(UTC)
    query = (
        update(RefreshSession)
        .where(
            RefreshSession.user_id == current_user.id,
            RefreshSession.revoked_at.is_(None),
            RefreshSession.expires_at > now,
        )
        .values(revoked_at=now)
    )
    if current_token_hash:
        query = query.where(RefreshSession.token_hash != current_token_hash)
    result = db.execute(query)
    count = result.rowcount or 0
    add_audit_event(
        db,
        current_user.company_id,
        current_user.id,
        "SESSIONS_REVOKE",
        "USER",
        f"{count} sesiones adicionales cerradas",
        current_user.id,
        {"revoked": count},
    )
    db.commit()
    return count


def _validate_managed_role(current_user: User, role: UserRole) -> None:
    if role == UserRole.SUPER_ADMIN and current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="No puedes asignar el rol superadministrador")


def _active_admin_count(db: Session, company_id: uuid.UUID) -> int:
    return (
        db.scalar(
            select(func.count(User.id)).where(
                User.company_id == company_id,
                User.active.is_(True),
                User.role.in_(ADMIN_ROLES),
            )
        )
        or 0
    )


def _revoke_user_sessions(db: Session, user_id: uuid.UUID) -> None:
    db.execute(
        update(RefreshSession)
        .where(RefreshSession.user_id == user_id, RefreshSession.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )


def _commit_email(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un usuario con ese correo electronico",
        ) from exc
