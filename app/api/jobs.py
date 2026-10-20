"""
Job management API routes.
"""
from fastapi import APIRouter, Depends, Query
from pymongo.database import Database
from typing import List, Optional

from app.core.dependencies import get_current_user, require_hr, require_student_or_admin
from app.core.exceptions import ForbiddenError
from app.cloud.mongodb import get_database
from app.schemas.common import DataResponse, PaginatedResponse, MessageResponse
from app.schemas.jobs import JobCreateRequest, JobUpdateRequest, JobOut
from app.services.job_service import JobService
from app.utils.pagination import parse_pagination_params
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

router = APIRouter(prefix="/jobs", tags=["Jobs"])


class GenerateJdRequest(BaseModel):
    role_title: str = Field(min_length=2, max_length=120)
    department: str = Field(min_length=2, max_length=120)
    experience_level: str = Field(min_length=2, max_length=80)


@router.post("/hr/generate-description", response_model=DataResponse[dict])
async def generate_job_description(request: GenerateJdRequest, current_user: dict = Depends(require_hr)):
    """Generate a role-specific job description using the configured Gemini key."""
    from app.ml.gemini_service import gemini_interview_service
    prompt = f'''Create a realistic, specific job posting using these details.
Role: {request.role_title}\nDepartment: {request.department}\nExperience: {request.experience_level}
Return only valid JSON with keys: description (string), required_skills (array of strings), preferred_skills (array of strings), target_keywords (array of strings), interview_questions (array of strings).
Use role-appropriate skills and responsibilities. Do not invent salary or company facts. Avoid generic filler. Keep description 3-5 paragraphs.'''
    raw = await run_in_threadpool(gemini_interview_service._call_gemini, prompt, 0.35, 1400, 30)
    if not raw:
        from app.core.exceptions import ProcessingError
        raise ProcessingError("Gemini JD generation is unavailable. Check GEMINI_API_KEY and retry.")
    import json
    try:
        result = json.loads(raw.replace("```json", "").replace("```", "").strip())
        if not isinstance(result.get("description"), str) or not result["description"].strip():
            raise ValueError("Missing description")
        for key in ("required_skills", "preferred_skills", "target_keywords", "interview_questions"):
            if not isinstance(result.get(key), list):
                raise ValueError(f"Missing {key}")
        result.update({"title": request.role_title.strip(), "department": request.department.strip(), "experience_level": request.experience_level.strip()})
    except (ValueError, TypeError, KeyError) as exc:
        from app.core.exceptions import ProcessingError
        raise ProcessingError("Gemini returned an invalid job description. Please try again.") from exc
    return DataResponse(data=result)


# ─── Public job routes ─────────────────────────────────────────────────────

@router.get("", response_model=PaginatedResponse[JobOut])
async def get_public_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    location: Optional[str] = Query(None),
    work_mode: Optional[str] = Query(None),
    experience_max: Optional[int] = Query(None),
    db: Database = Depends(get_database)
):
    """Get active job listings (public access)."""
    job_service = JobService(db)
    
    filters = {}
    if location:
        filters["location"] = location
    if work_mode:
        filters["work_mode"] = work_mode
    if experience_max:
        filters["experience_max"] = experience_max
    
    jobs, pagination = await job_service.get_public_jobs(
        page=page,
        page_size=page_size,
        filters=filters if filters else None
    )
    
    return PaginatedResponse(
        data=[JobOut(**job) for job in jobs],
        pagination=pagination
    )


@router.get("/{job_id}", response_model=DataResponse[JobOut])
async def get_job_details(
    job_id: str,
    db: Database = Depends(get_database)
):
    """Get detailed job information (public access)."""
    job_service = JobService(db)
    
    job = await job_service.get_job_by_id(job_id, include_company=True)
    
    return DataResponse(data=JobOut(**job))


# ─── HR job management routes ──────────────────────────────────────────────

@router.post("/hr/jobs", response_model=DataResponse[JobOut])
async def create_job(
    request: JobCreateRequest,
    current_user: dict = Depends(require_hr),
    db: Database = Depends(get_database)
):
    """Create a new job posting (HR only)."""
    job_service = JobService(db)
    
    job = await job_service.create_job(
        job_data=request.dict(),
        hr_user_id=current_user["id"]
    )
    
    return DataResponse(data=JobOut(**job))


@router.get("/hr/jobs", response_model=PaginatedResponse[JobOut])
async def get_company_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    current_user: dict = Depends(require_hr),
    db: Database = Depends(get_database)
):
    """Get jobs for HR user's company."""
    job_service = JobService(db)
    
    jobs, pagination = await job_service.get_company_jobs(
        hr_user_id=current_user["id"],
        page=page,
        page_size=page_size,
        status_filter=status
    )
    
    return PaginatedResponse(
        data=[JobOut(**job) for job in jobs],
        pagination=pagination
    )


@router.get("/hr/jobs/{job_id}", response_model=DataResponse[JobOut])
async def get_hr_job_details(
    job_id: str,
    current_user: dict = Depends(require_hr),
    db: Database = Depends(get_database)
):
    """Get detailed job information for HR user."""
    job_service = JobService(db)
    
    job = await job_service.get_job_by_id(job_id, include_company=True)
    if job.get("created_by") != current_user["id"]:
        raise ForbiddenError("Not authorized to view this job")
    
    return DataResponse(data=JobOut(**job))


@router.patch("/hr/jobs/{job_id}", response_model=DataResponse[JobOut])
async def update_job(
    job_id: str,
    request: JobUpdateRequest,
    current_user: dict = Depends(require_hr),
    db: Database = Depends(get_database)
):
    """Update job details (HR only)."""
    job_service = JobService(db)
    
    # Only include non-None fields in update
    update_data = {k: v for k, v in request.dict().items() if v is not None}
    
    job = await job_service.update_job(job_id, update_data, current_user["id"])
    
    return DataResponse(data=JobOut(**job))


@router.delete("/hr/jobs/{job_id}", response_model=MessageResponse)
async def delete_job(
    job_id: str,
    current_user: dict = Depends(require_hr),
    db: Database = Depends(get_database)
):
    """Delete job posting (HR only)."""
    job_service = JobService(db)
    
    await job_service.delete_job(job_id, current_user["id"])
    
    return MessageResponse(message="Job deleted successfully")


@router.post("/hr/jobs/{job_id}/publish", response_model=DataResponse[JobOut])
async def publish_job(
    job_id: str,
    current_user: dict = Depends(require_hr),
    db: Database = Depends(get_database)
):
    """Publish a draft job (make it active)."""
    job_service = JobService(db)
    
    job = await job_service.publish_job(job_id, current_user["id"])
    
    return DataResponse(data=JobOut(**job))


@router.post("/hr/jobs/{job_id}/close", response_model=DataResponse[JobOut])
async def close_job(
    job_id: str,
    current_user: dict = Depends(require_hr),
    db: Database = Depends(get_database)
):
    """Close an active job."""
    job_service = JobService(db)
    
    job = await job_service.close_job(job_id, current_user["id"])
    
    return DataResponse(data=JobOut(**job))
