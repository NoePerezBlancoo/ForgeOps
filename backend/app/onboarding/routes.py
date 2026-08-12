from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.onboarding.schemas import OnboardingRead, OnboardingUpdate
from app.onboarding.service import get_onboarding, restart_onboarding, update_onboarding
from app.users.models import User

router = APIRouter(prefix="/onboarding", tags=["Primeros pasos"])


@router.get("", response_model=OnboardingRead)
def show(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OnboardingRead:
    return get_onboarding(db, current_user)


@router.patch("", response_model=OnboardingRead)
def update(
    payload: OnboardingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OnboardingRead:
    return update_onboarding(db, current_user, payload)


@router.post("/restart", response_model=OnboardingRead)
def restart(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OnboardingRead:
    return restart_onboarding(db, current_user)
