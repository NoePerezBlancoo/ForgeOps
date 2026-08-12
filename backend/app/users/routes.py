import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_roles
from app.core.database import get_db
from app.core.enums import UserRole
from app.users.models import User
from app.users.schemas import UserCreate, UserOption, UserPasswordReset, UserRead, UserUpdate
from app.users.service import create_user, get_user, list_users, reset_user_password, update_user

router = APIRouter(prefix="/users", tags=["Usuarios"])
administrators = require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)


@router.get("/options", response_model=list[UserOption])
def options(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list:
    return list_users(db, current_user.company_id, True)


@router.get("", response_model=list[UserRead])
def index(
    active_only: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(administrators),
) -> list:
    return list_users(db, current_user.company_id, active_only)


@router.get("/{user_id}", response_model=UserRead)
def show(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(administrators),
):
    return get_user(db, current_user.company_id, user_id)


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def store(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(administrators),
):
    return create_user(db, current_user, payload)


@router.patch("/{user_id}", response_model=UserRead)
def update(
    user_id: uuid.UUID,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(administrators),
):
    return update_user(db, current_user, user_id, payload)


@router.post("/{user_id}/password", response_model=UserRead)
def reset_password(
    user_id: uuid.UUID,
    payload: UserPasswordReset,
    db: Session = Depends(get_db),
    current_user: User = Depends(administrators),
):
    return reset_user_password(db, current_user, user_id, payload)
