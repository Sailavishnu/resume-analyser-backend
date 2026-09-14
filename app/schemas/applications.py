from pydantic import BaseModel
from typing import Optional
from datetime import datetime

VALID_STATUSES = (
    "applied", "under_review", "shortlisted",
    "interview", "offer", "hired", "rejected", "withdrawn",
)


class ApplicationCreateRequest(BaseModel):
    job_id: str
    resume_id: str


class ApplicationUpdateRequest(BaseModel):
    status: str

    def validate_status(self):
        if self.status not in VALID_STATUSES:
            raise ValueError(f"Invalid status: {self.status}")


class ApplicationNoteRequest(BaseModel):
    content: str


class ApplicationOut(BaseModel):
    id: str
    student_id: str
    job_id: str
    resume_id: str
    status: str
    applied_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # Denormalised fields for frontend
    job_title: Optional[str] = None
    company_name: Optional[str] = None
    company_logo: Optional[str] = None
    match_score: Optional[int] = None


class ApplicationEventOut(BaseModel):
    id: str
    application_id: str
    event_type: str
    message: str
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None


class ApplicationNoteOut(BaseModel):
    id: str
    application_id: str
    student_id: str
    content: str
    created_at: Optional[datetime] = None
