"""
Resume management API routes.
"""
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Query
from pymongo.database import Database
from typing import List, Optional

from app.core.dependencies import get_current_user, require_student
from app.core.config import settings
from app.db.mongodb import get_database
from app.schemas.common import DataResponse, PaginatedResponse, MessageResponse
from app.schemas.resumes import (
    ResumeOut, AnalysisStatusOut, ResumeAnalysisOut, 
    ImprovementOut, ImprovementUpdateRequest, ResumeVersionOut
)
from app.services.resume_service import ResumeService

router = APIRouter(prefix="/resumes", tags=["Resumes"])


@router.post("/upload", response_model=DataResponse[ResumeOut])
async def upload_resume(
    file: UploadFile = File(...),
    current_user: dict = Depends(require_student),
    db: Database = Depends(get_database)
):
    """Upload and analyze a new resume."""
    resume_service = ResumeService(db)
    
    # Read file content
    file_content = await file.read()
    
    # Upload and process
    resume = await resume_service.upload_resume(
        student_id=current_user["id"],
        file_content=file_content,
        filename=file.filename,
        content_type=file.content_type,
        max_size_bytes=settings.max_upload_bytes
    )
    
    return DataResponse(data=ResumeOut(**resume))


@router.get("", response_model=DataResponse[List[ResumeOut]])
async def get_my_resumes(
    current_user: dict = Depends(require_student),
    db: Database = Depends(get_database)
):
    """Get all resumes for authenticated student."""
    resume_service = ResumeService(db)
    
    resumes = await resume_service.get_student_resumes(current_user["id"])
    
    return DataResponse(data=[ResumeOut(**r) for r in resumes])


@router.get("/{resume_id}", response_model=DataResponse[ResumeOut])
async def get_resume(
    resume_id: str,
    current_user: dict = Depends(require_student),
    db: Database = Depends(get_database)
):
    """Get specific resume by ID."""
    resume_service = ResumeService(db)
    
    resume = await resume_service.get_resume_by_id(resume_id, current_user["id"])
    
    return DataResponse(data=ResumeOut(**resume))


@router.delete("/{resume_id}", response_model=MessageResponse)
async def delete_resume(
    resume_id: str,
    current_user: dict = Depends(require_student),
    db: Database = Depends(get_database)
):
    """Delete resume and all associated data."""
    resume_service = ResumeService(db)
    
    await resume_service.delete_resume(resume_id, current_user["id"])
    
    return MessageResponse(message="Resume deleted successfully")


@router.get("/{resume_id}/analysis-status", response_model=DataResponse[AnalysisStatusOut])
async def get_analysis_status(
    resume_id: str,
    current_user: dict = Depends(require_student),
    db: Database = Depends(get_database)
):
    """Get resume analysis status for polling."""
    resume_service = ResumeService(db)
    
    resume = await resume_service.get_resume_by_id(resume_id, current_user["id"])
    
    status_data = AnalysisStatusOut(
        resume_id=resume_id,
        status=resume.get("status", "uploaded"),
        analysis_progress=resume.get("analysis_progress"),
        analysis_stage=resume.get("analysis_stage")
    )
    
    return DataResponse(data=status_data)


@router.get("/{resume_id}/analysis", response_model=DataResponse[ResumeAnalysisOut])
async def get_resume_analysis(
    resume_id: str,
    current_user: dict = Depends(require_student),
    db: Database = Depends(get_database)
):
    """Get detailed resume analysis results."""
    resume_service = ResumeService(db)
    
    analysis = await resume_service.get_resume_analysis(resume_id, current_user["id"])
    
    return DataResponse(data=ResumeAnalysisOut(**analysis))


@router.post("/{resume_id}/analyze", response_model=MessageResponse)
async def trigger_reanalysis(
    resume_id: str,
    current_user: dict = Depends(require_student),
    db: Database = Depends(get_database)
):
    """Trigger re-analysis of resume (if needed)."""
    # This would re-run the analysis pipeline
    # For now, just return success
    return MessageResponse(message="Analysis triggered successfully")


@router.get("/{resume_id}/improvements", response_model=DataResponse[List[ImprovementOut]])
async def get_resume_improvements(
    resume_id: str,
    current_user: dict = Depends(require_student),
    db: Database = Depends(get_database)
):
    """Get improvement suggestions for resume."""
    resume_service = ResumeService(db)
    
    improvements = await resume_service.get_resume_improvements(resume_id, current_user["id"])
    
    return DataResponse(data=[ImprovementOut(**imp) for imp in improvements])


@router.patch("/improvements/{improvement_id}", response_model=DataResponse[ImprovementOut])
async def update_improvement_status(
    improvement_id: str,
    request: ImprovementUpdateRequest,
    current_user: dict = Depends(require_student),
    db: Database = Depends(get_database)
):
    """Accept or reject improvement suggestion."""
    resume_service = ResumeService(db)
    
    improvement = await resume_service.update_improvement_status(
        improvement_id, request.status, current_user["id"]
    )
    
    return DataResponse(data=ImprovementOut(**improvement))


@router.get("/{resume_id}/versions", response_model=DataResponse[List[ResumeVersionOut]])
async def get_resume_versions(
    resume_id: str,
    current_user: dict = Depends(require_student),
    db: Database = Depends(get_database)
):
    """Get all versions of resume."""
    # This would fetch resume versions from database
    # Simplified implementation for now
    return DataResponse(data=[])


@router.get("/{resume_id}/download")
async def download_resume(
    resume_id: str,
    current_user: dict = Depends(require_student),
    db: Database = Depends(get_database)
):
    """Generate download URL for resume file."""
    resume_service = ResumeService(db)
    
    resume = await resume_service.get_resume_by_id(resume_id, current_user["id"])
    
    if not resume.get("cloudinary_secure_url"):
        raise HTTPException(status_code=404, detail="Resume file not found")
    
    # Return redirect to Cloudinary URL
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=resume["cloudinary_secure_url"])