"""Validated request and response types for platform APIs."""
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: str
    full_name: str
    role: str
    created_at: datetime


class UserUpdate(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)


class ProfileUpdate(BaseModel):
    headline: str | None = Field(default=None, max_length=160)
    target_role: str | None = Field(default=None, max_length=120)
    experience_years: int | None = Field(default=None, ge=0, le=60)
    skills: list[str] | None = Field(default=None, max_length=50)
    preferences: dict[str, Any] | None = None


class InterviewCreate(BaseModel):
    role: str = Field(min_length=2, max_length=120)
    interview_type: Literal["behavioral", "technical", "system_design", "mixed"] = "behavioral"
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    title: str | None = Field(default=None, max_length=160)


class InterviewAnswer(BaseModel):
    content: str = Field(min_length=1, max_length=12000)


class InterviewTurnResponse(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime


class InterviewSummary(BaseModel):
    id: str
    status: str
    title: str
    role: str
    interview_type: str
    difficulty: str
    created_at: datetime
    updated_at: datetime
    turns: list[InterviewTurnResponse] = Field(default_factory=list)


class EvaluationResponse(BaseModel):
    id: str
    session_id: str
    total_score: int
    rubric: dict[str, int]
    summary: str
    created_at: datetime


class SettingsResponse(BaseModel):
    data: dict[str, Any]
    updated_at: datetime | None = None
