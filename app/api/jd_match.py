"""
Job Description matching API routes.

Includes both traditional ML matching and semantic search.
"""
from fastapi import APIRouter, Depends, Query
from pymongo.database import Database
from typing import List, Optional

from app.core.dependencies import get_current_user, require_student
from app.db.mongodb import get_database
from app.schemas.common import DataResponse
from app.schemas.matching import JDMatchRequest, JDMatchOut
from app.services.jd_match_service import JDMatchService
from app.services.semantic_match_service import get_semantic_match_service

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


# ─── Semantic Search Endpoints ────────────────────────────────────────────

@router.post("/semantic/search")
async def semantic_job_search(
    resume_id: str,
    top_k: int = Query(default=10, ge=1, le=50),
    location: Optional[str] = None,
    job_type: Optional[str] = None,
    current_user: dict = Depends(require_student)
):
    """
    Find matching jobs using semantic search (AI-powered).
    
    Uses Sentence-BERT embeddings and FAISS vector search
    to find semantically similar jobs based on resume content.
    """
    semantic_service = get_semantic_match_service()
    
    filters = {}
    if location:
        filters["location"] = location
    if job_type:
        filters["job_type"] = job_type
    
    results = semantic_service.find_matching_jobs_semantic(
        resume_id=resume_id,
        top_k=top_k,
        filters=filters
    )
    
    return DataResponse(
        data=results,
        message=f"Found {len(results)} semantically matching jobs"
    )


@router.post("/semantic/score")
async def calculate_semantic_match(
    resume_id: str,
    job_id: str,
    current_user: dict = Depends(require_student)
):
    """
    Calculate detailed semantic match score between resume and job.
    
    Returns:
    - Semantic similarity score (Sentence-BERT)
    - ML model prediction score (if available)
    - Hybrid combined score
    - Detailed match explanation
    """
    semantic_service = get_semantic_match_service()
    
    result = semantic_service.calculate_semantic_match_score(
        resume_id=resume_id,
        job_id=job_id
    )
    
    return DataResponse(
        data=result,
        message="Semantic match calculated successfully"
    )


@router.post("/semantic/skills-search")
async def search_by_skills(
    skills: List[str],
    top_k: int = Query(default=10, ge=1, le=50),
    current_user: dict = Depends(require_student)
):
    """
    Search jobs by skill list (without uploading resume).
    
    Quick way to explore jobs matching specific skills.
    """
    if not skills:
        return DataResponse(
            data=[],
            message="No skills provided"
        )
    
    semantic_service = get_semantic_match_service()
    
    results = semantic_service.search_jobs_by_skills(
        skills=skills,
        top_k=top_k
    )
    
    return DataResponse(
        data=results,
        message=f"Found {len(results)} jobs matching provided skills"
    )