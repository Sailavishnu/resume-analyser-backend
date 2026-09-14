from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# ─── Real interviews (HR-scheduled) ──────────────────────────────────────────

class InterviewCreateRequest(BaseModel):
    application_id: str
    student_id: str
    job_id: str
    scheduled_at: datetime
    duration_minutes: int = 60
    type: str = "technical"         # technical | hr | final
    meeting_url: Optional[str] = None
    notes: Optional[str] = None


class InterviewUpdateRequest(BaseModel):
    scheduled_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    type: Optional[str] = None
    status: Optional[str] = None
    meeting_url: Optional[str] = None
    notes: Optional[str] = None


class InterviewOut(BaseModel):
    id: str
    application_id: str
    student_id: str
    job_id: str
    scheduled_by: str
    scheduled_at: Optional[datetime] = None
    duration_minutes: int
    type: str
    status: str = "scheduled"       # scheduled | completed | cancelled
    meeting_url: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ─── Mock interviews (student practice) ──────────────────────────────────────

class MockInterviewCreateRequest(BaseModel):
    target_role: str
    type: str = "general"           # general | technical | behavioral
    difficulty: str = "medium"      # easy | medium | hard


class MockAnswerSubmitRequest(BaseModel):
    question_id: str
    answer_text: str


class MockInterviewCompleteRequest(BaseModel):
    pass  # Triggers evaluation of all submitted answers


class MockQuestionOut(BaseModel):
    id: str
    question_text: str
    category: str
    difficulty: str


class MockAnswerOut(BaseModel):
    id: str
    interview_id: str
    question_id: str
    answer_text: str
    score: Optional[int] = None
    feedback: Optional[str] = None
    key_points_missed: list[str] = []
    strengths: list[str] = []
    created_at: Optional[datetime] = None


class MockInterviewOut(BaseModel):
    id: str
    student_id: str
    target_role: str
    type: str
    difficulty: str
    status: str = "in_progress"     # in_progress | completed
    overall_score: Optional[int] = None
    questions: list[MockQuestionOut] = []
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class MockInterviewReportOut(BaseModel):
    interview_id: str
    overall_score: int
    communication_score: int
    technical_depth: int
    confidence_level: int
    average_answer_quality: float
    general_feedback: str
    improvement_suggestions: list[str] = []
    question_results: list[MockAnswerOut] = []
    completed_at: Optional[datetime] = None
