from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class CandidateOut(BaseModel):
    """HR-facing candidate view: student + application + match rolled into one."""
    application_id: str
    student_id: str
    full_name: str
    email: str
    location: Optional[str] = None
    target_role: Optional[str] = None
    resume_id: Optional[str] = None
    resume_url: Optional[str] = None
    status: str
    applied_at: Optional[datetime] = None
    overall_score: Optional[int] = None
    ats_score: Optional[int] = None
    skills_score: Optional[int] = None
    matched_skills: list[str] = []
    missing_skills: list[str] = []
    job_id: str
    job_title: str


class CandidateStageUpdateRequest(BaseModel):
    status: str
    reason: Optional[str] = None


class ScreeningCreateRequest(BaseModel):
    application_id: str
    status: str   # shortlist | reject | review
    score: Optional[int] = None
    notes: Optional[str] = None


class ScreeningUpdateRequest(BaseModel):
    status: Optional[str] = None
    score: Optional[int] = None
    notes: Optional[str] = None


class ScreeningOut(BaseModel):
    id: str
    application_id: str
    reviewer_id: str
    status: str
    score: Optional[int] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
