"""
Job Description matching API routes.
"""
from fastapi import APIRouter, Depends
from pymongo.database import Database
from typing import List

from app.core.dependencies import get_current_user, require_student
from app.db.mongodb import get_database
from app.schemas.common import DataResponse
from app.schemas.matching import JDMatchRequest, JDMatchOut
from app.services.jd_match_service import JDMatchService

router = APIRouter(prefix="/jd-match", tags=["Job Matching"])


@router.post("", response_model=DataResponse[JDMatchOut])
async def calculate_job_match(
    request: JDMatchRequest,
    current_user: dict = Depends(require_student),
    db: Database = Depends(get_database)
):
    """Calculate resume-job match using ML model."""
    match_service = JDMatchService(db)
    
    match_result = await match_service.calculate_match_score(
        resume_id=request.resume_id,
        job_id=request.job_id,
        student_id=current_user["id"]
    )
    
    return DataResponse(data=JDMatchOut(**match_result))


@router.get("/{match_id}", response_model=DataResponse[JDMatchOut])
async def get_match_result(
    match_id: str,
    current_user: dict = Depends(require_student),
    db: Database = Depends(get_database)
):
    """Get existing job match result by ID."""
    match_service = JDMatchService(db)
    
    match_result = await match_service.get_match_by_id(match_id)
    
    return DataResponse(data=JDMatchOut(**match_result))


@router.get("", response_model=DataResponse[List[JDMatchOut]])
async def get_my_matches(
    current_user: dict = Depends(require_student),
    db: Database = Depends(get_database)
):
    """Get recent job matches for authenticated student."""
    match_service = JDMatchService(db)
    
    matches = await match_service.get_student_matches(current_user["id"])
    
    return DataResponse(data=[JDMatchOut(**match) for match in matches])