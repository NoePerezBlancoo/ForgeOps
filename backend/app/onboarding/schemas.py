from datetime import datetime

from pydantic import BaseModel, Field


class OnboardingStepRead(BaseModel):
    key: str
    title: str
    description: str
    href: str
    complete: bool
    automatic: bool


class OnboardingRead(BaseModel):
    completed: int
    total: int
    percent: int
    tour_completed: bool
    dismissed_at: datetime | None
    steps: list[OnboardingStepRead]


class OnboardingUpdate(BaseModel):
    completed_step: str | None = Field(default=None, max_length=40)
    tour_completed: bool | None = None
    dismissed: bool | None = None
