from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AssessmentOut(BaseModel):
    id: str
    title: str
    skill_id: Optional[str] = None
    skill_name: Optional[str] = None
    category: str
    difficulty: str = "medium"
    total_questions: int
    time_limit_minutes: int = 15
    passing_score: int = 60
    description: Optional[str] = None


class AssessmentQuestionOut(BaseModel):
    id: str
    question_text: str
    options: list[str]
    # correct_answer intentionally omitted — never sent before submission


class AttemptCreateRequest(BaseModel):
    assessment_id: str


class AttemptSubmitRequest(BaseModel):
    answers: dict[str, str]    # {question_id: selected_option}


class AttemptOut(BaseModel):
    id: str
    student_id: str
    assessment_id: str
    score: Optional[int] = None
    total_questions: int
    correct_answers: Optional[int] = None
    passed: Optional[bool] = None
    time_taken_seconds: Optional[int] = None
    status: str = "in_progress"    # in_progress | submitted | evaluated
    created_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
