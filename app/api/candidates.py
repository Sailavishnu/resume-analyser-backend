"""
Candidate management API routes for HR users.
"""
from fastapi import APIRouter, Depends, Query
from pymongo.database import Database
from typing import Optional

from app.core.dependencies import require_hr
from app.db.mongodb import get_database
from app.schemas.common import DataResponse, PaginatedResponse
from app.schemas.candidates import CandidateOut
from app.services.candidate_service import CandidateService

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


@router.get("/{application_id}", response_model=DataResponse[dict])
async def get_candidate_details(
    application_id: str,
    current_user: dict = Depends(require_hr),
    db: Database = Depends(get_database)
):
    """Get detailed candidate information."""
    candidate_service = CandidateService(db)
    
    candidate = await candidate_service.get_candidate_details(
        application_id=application_id,
        hr_user_id=current_user["id"]
    )
    
    return DataResponse(data=candidate)