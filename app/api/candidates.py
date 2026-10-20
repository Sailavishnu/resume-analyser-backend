"""
Candidate management API routes for HR users.
"""
from fastapi import APIRouter, Depends, Query, Body
from pymongo.database import Database
from typing import Optional, List, Dict, Any

from app.core.dependencies import require_hr
from app.cloud.mongodb import get_database
from app.schemas.common import DataResponse, PaginatedResponse
from app.schemas.candidates import CandidateOut
from app.services.candidate_service import CandidateService
from app.services.application_service import ApplicationService

router = APIRouter(prefix="/hr/candidates", tags=["HR - Candidates"])


@router.get("/jobs/{job_id}", response_model=PaginatedResponse[CandidateOut])
async def get_job_candidates(
    job_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    min_match_score: Optional[int] = Query(None, ge=0, le=100),
    current_user: dict = Depends(require_hr),
    db: Database = Depends(get_database)
):
    """Get candidates who applied to a specific job."""
    candidate_service = CandidateService(db)
    
    candidates, pagination = await candidate_service.get_job_candidates(
        job_id=job_id,
        hr_user_id=current_user["id"],
        page=page,
        page_size=page_size,
        status_filter=status,
        min_match_score=min_match_score
    )
    
    return PaginatedResponse(
        data=[CandidateOut(**candidate) for candidate in candidates],
        pagination=pagination
    )


@router.get("/accepted", response_model=DataResponse[list])
async def get_accepted_students(current_user: dict = Depends(require_hr), db: Database = Depends(get_database)):
    return DataResponse(data=await CandidateService(db).get_accepted_students(current_user["id"]))


@router.patch("/{application_id}/status", response_model=DataResponse[dict])
async def update_candidate_status(
    application_id: str,
    payload: dict = Body(...),
    current_user: dict = Depends(require_hr),
    db: Database = Depends(get_database)
):
    """Update application stage status (shortlisted, interview_scheduled, rejected, etc.)."""
    new_status = payload.get("status", "shortlisted")
    res = await ApplicationService(db).update_application_status(
        app_id=application_id, new_status=new_status, hr_user_id=current_user["id"],
    )
    return DataResponse(data=res)
