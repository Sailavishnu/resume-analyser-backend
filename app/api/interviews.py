"""
AI Mock Interview API Routes

Provides endpoints for resume-driven question generation, NLP response grading,
and adaptive follow-up interactions.
"""
from fastapi import APIRouter, Depends, Body
from pymongo.database import Database
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

from app.core.dependencies import get_optional_current_user
from app.db.mongodb import get_database
from app.db import collections as C
from app.schemas.common import DataResponse
from app.services.interview_service import AIInterviewService

router = APIRouter(prefix="/interviews", tags=["AI Mock Interviews"])


class StartInterviewRequest(BaseModel):
    target_role: Optional[str] = "Software Engineer"
    interview_type: Optional[str] = "technical"
    resume_id: Optional[str] = None
    student_id: Optional[str] = None


class SubmitAnswerRequest(BaseModel):
    answer_text: str
    student_id: Optional[str] = None


async def _resolve_student_id(user: Optional[dict], custom_id: Optional[str], db: Database) -> str:
    """Resolve student ID from user token, custom param, or default demo student."""
    if user and user.get("id"):
        return user["id"]
    if custom_id:
        return custom_id
    # Fallback to first student in MongoDB or demo ObjectId
    first_student = db[C.USERS].find_one({"role": "student"})
    if first_student:
        return str(first_student["_id"])
    return "65ce00000000000000000001"


@router.post("/start", response_model=DataResponse[Dict[str, Any]])
async def start_interview_session(
    request: StartInterviewRequest,
    current_user: Optional[dict] = Depends(get_optional_current_user),
    db: Database = Depends(get_database)
):
    """
    Start a new AI Mock Interview tailored to the student's uploaded resume.
    """
    student_id = await _resolve_student_id(current_user, request.student_id, db)
    service = AIInterviewService(db)
    result = await service.start_interview(
        student_id=student_id,
        target_role=request.target_role or "Software Engineer",
        interview_type=request.interview_type or "technical",
        resume_id=request.resume_id
    )
    return DataResponse(
        data=result,
        message="AI Mock Interview session started successfully."
    )


@router.post("/{session_id}/answer", response_model=DataResponse[Dict[str, Any]])
async def submit_interview_answer(
    session_id: str,
    request: SubmitAnswerRequest,
    current_user: Optional[dict] = Depends(get_optional_current_user),
    db: Database = Depends(get_database)
):
    """
    Submit an answer to the current interview question.
    Runs local NLP analysis and generates the next adaptive question.
    """
    student_id = await _resolve_student_id(current_user, request.student_id, db)
    service = AIInterviewService(db)
    result = await service.submit_answer(
        session_id=session_id,
        student_id=student_id,
        answer_text=request.answer_text
    )
    return DataResponse(
        data=result,
        message="Answer evaluated successfully."
    )


@router.get("/{session_id}", response_model=DataResponse[Dict[str, Any]])
async def get_interview_session(
    session_id: str,
    current_user: Optional[dict] = Depends(get_optional_current_user),
    db: Database = Depends(get_database)
):
    """Get status and report for an interview session."""
    student_id = await _resolve_student_id(current_user, None, db)
    service = AIInterviewService(db)
    result = await service.get_interview(session_id, student_id)
    return DataResponse(data=result)


@router.get("", response_model=DataResponse[List[Dict[str, Any]]])
async def get_my_interviews(
    current_user: Optional[dict] = Depends(get_optional_current_user),
    db: Database = Depends(get_database)
):
    """Get all past mock interview sessions for current student."""
    student_id = await _resolve_student_id(current_user, None, db)
    service = AIInterviewService(db)
    results = await service.get_student_interviews(student_id)
    return DataResponse(data=results)
