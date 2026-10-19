"""Authenticated practice challenges and personal attempt history."""

from typing import Literal

from fastapi import APIRouter, Depends, Query
from pymongo.database import Database

from app.cloud.mongodb import get_database
from app.core.dependencies import require_student
from app.schemas.common import DataResponse
from app.schemas.practice import PracticeAttemptRequest
from app.services.practice_service import PracticeService


router = APIRouter(prefix="/practice", tags=["Practice"])


@router.get("/challenges", response_model=DataResponse[list[dict]])
async def list_challenges(
    challenge_type: Literal["resume", "job-readiness"] | None = Query(default=None, alias="type"),
    difficulty: Literal["beginner", "intermediate", "advanced"] | None = None,
    target_role: Literal["Backend Developer", "Frontend Developer", "Full Stack Developer", "Software Engineer"] | None = Query(default=None, alias="targetRole"),
    current_user: dict = Depends(require_student),
    db: Database = Depends(get_database),
):
    return DataResponse(data=PracticeService(db).list_challenges(challenge_type, difficulty, target_role))


@router.get("/challenges/{challenge_id}", response_model=DataResponse[dict])
async def get_challenge(
    challenge_id: str,
    target_role: Literal["Backend Developer", "Frontend Developer", "Full Stack Developer", "Software Engineer"] | None = Query(default=None, alias="targetRole"),
    current_user: dict = Depends(require_student),
    db: Database = Depends(get_database),
):
    return DataResponse(data=PracticeService(db).get_challenge(challenge_id, target_role))


@router.post("/attempts", response_model=DataResponse[dict], status_code=201)
async def submit_attempt(
    payload: PracticeAttemptRequest,
    current_user: dict = Depends(require_student),
    db: Database = Depends(get_database),
):
    attempt = await PracticeService(db).submit_attempt(
        current_user["id"], payload.challengeId, payload.answer,
        payload.targetRole, payload.submissionId,
    )
    return DataResponse(data=attempt)


@router.get("/attempts", response_model=DataResponse[dict])
async def list_attempts(
    challenge_type: Literal["resume", "job-readiness"] | None = Query(default=None, alias="type"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: dict = Depends(require_student),
    db: Database = Depends(get_database),
):
    result = PracticeService(db).list_attempts(current_user["id"], challenge_type, limit, offset)
    return DataResponse(data=result)


@router.get("/attempts/{attempt_id}", response_model=DataResponse[dict])
async def get_attempt(
    attempt_id: str,
    current_user: dict = Depends(require_student),
    db: Database = Depends(get_database),
):
    return DataResponse(data=PracticeService(db).get_attempt(current_user["id"], attempt_id))


@router.get("/stats", response_model=DataResponse[dict])
async def get_practice_stats(
    challenge_type: Literal["all", "resume", "job-readiness"] = Query(default="all", alias="type"),
    current_user: dict = Depends(require_student),
    db: Database = Depends(get_database),
):
    selected_type = None if challenge_type == "all" else challenge_type
    return DataResponse(data=PracticeService(db).get_stats(current_user["id"], selected_type))
