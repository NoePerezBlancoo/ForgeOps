from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.users.models import User
from app.users.schemas import UserOption

router = APIRouter(prefix="/users", tags=["Usuarios"])


@router.get("", response_model=list[UserOption])
def list_users(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> list[User]:
    return list(
        db.scalars(
            select(User)
            .where(User.company_id == current_user.company_id, User.active.is_(True))
            .order_by(User.full_name)
        )
    )
