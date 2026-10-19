"""
Resume management API routes.
"""
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Any
from pymongo.database import Database
from typing import List

from app.core.dependencies import require_student
from app.core.config import settings
from app.cloud.mongodb import get_database
from app.schemas.common import DataResponse, PaginatedResponse, MessageResponse
from app.schemas.resumes import (
    ResumeOut, AnalysisStatusOut, ResumeAnalysisOut, 
    ImprovementOut, ImprovementUpdateRequest, ResumeEnhancementRequest, ResumeVersionOut
)
from app.services.resume_service import ResumeService
from app.utils.serializers import serialize_mongo_doc

router = APIRouter(prefix="/resumes", tags=["Resumes"])


class BuilderExportRequest(BaseModel):
    resume: dict[str, Any]


@router.post("/builder/export-pdf")
async def export_builder_pdf(payload: BuilderExportRequest, current_user: dict = Depends(require_student)):
    """Render the current builder data to a real PDF download (no print dialog)."""
    import fitz
    import re
    from io import BytesIO

    data = payload.resume
    doc = fitz.open()
    page = doc.new_page()
    left, width, y = 58, 480, 48
    navy = (0.08, 0.16, 0.29)

    def ensure_space(height=20):
        nonlocal page, y
        if y + height > 770:
            page = doc.new_page()
            y = 48

    def text(value, size=10, bold=False, color=(0.16, 0.19, 0.24), gap=4):
        nonlocal page, y
        value = str(value or "").strip()
        if not value:
            return
        font = "hebo" if bold else "helv"
        for line in value.splitlines():
            # insert_textbox performs word wrapping and reports consumed height.
            ensure_space(size * 2 + gap)
            rect = fitz.Rect(left, y, left + width, 790)
            remaining = page.insert_textbox(rect, line, fontsize=size, fontname=font, color=color, lineheight=1.25)
            if remaining < 0:
                page = doc.new_page()
                y = 48
                page.insert_textbox(fitz.Rect(left, y, left + width, 790), line, fontsize=size, fontname=font, color=color, lineheight=1.25)
                y += size * 2
            else:
                y = 790 - remaining + gap

    def section(title):
        nonlocal y
        ensure_space(32)
        y += 9
        page.draw_line((left, y), (left + width, y), color=(0.82, 0.85, 0.89), width=0.7)
        y += 15
        text(title.upper(), 10, True, navy, 8)

    text(data.get("fullName") or current_user.get("full_name"), 22, True, navy, 3)
    text(" · ".join(filter(None, [data.get("title"), data.get("email"), data.get("phone"), data.get("address")])), 9, False, (0.3, 0.35, 0.42), 4)
    links = " · ".join(filter(None, [data.get("linkedin"), data.get("github")]))
    text(links, 9, False, (0.12, 0.36, 0.65), 10)
    if data.get("summary"):
        section("Professional Summary")
        text(data["summary"], 10, False, gap=3)
    for key, heading in (("experience", "Experience"), ("projects", "Projects"), ("education", "Education")):
        items = data.get(key) or []
        if not items:
            continue
        section(heading)
        for item in items:
            title = item.get("role") or item.get("title") or item.get("institution") or ""
            company = item.get("company") or item.get("degree") or ""
            text(" — ".join(filter(None, [title, company])), 10, True, navy, 2)
            text(" · ".join(filter(None, [item.get("duration"), item.get("year"), item.get("score"), item.get("techStack")])), 9, False, (0.35, 0.39, 0.45), 3)
            for bullet in item.get("bullets", []):
                text(f"•  {bullet}", 9, False, gap=2)
            y += 4
    skills = data.get("skills") or {}
    if skills:
        section("Skills")
        for category, value in skills.items():
            if value:
                text(f"{category.replace('_', ' ').title()}: {value}", 9, False, gap=3)
    pdf = BytesIO(doc.tobytes(garbage=4, deflate=True))
    doc.close()
    filename = re.sub(r"[^A-Za-z0-9_-]+", "_", data.get("fullName") or "Resume").strip("_") or "Resume"
    return Response(content=pdf.getvalue(), media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{filename}_Resume.pdf"', "Cache-Control": "no-store"})


@router.post("/upload", response_model=DataResponse[ResumeOut])
async def upload_resume(
    file: UploadFile = File(...),
    slot: str = Query(default="primary", pattern="^(primary|secondary)$"),
    current_user: dict = Depends(require_student),
    db: Database = Depends(get_database)
):
    """Upload and analyze a new resume to Cloudinary + MongoDB."""
    resume_service = ResumeService(db)
    
    file_content = await file.read()
    
    resume = await resume_service.upload_resume(
        student_id=current_user["id"],
        file_content=file_content,
        filename=file.filename,
        content_type=file.content_type,
        max_size_bytes=settings.max_upload_bytes,
        slot=slot
    )
    
    return DataResponse(data=ResumeOut(**serialize_mongo_doc(resume)))


@router.patch("/{resume_id}/slot", response_model=DataResponse[ResumeOut])
async def update_resume_slot(
    resume_id: str,
    slot: str = Query(..., pattern="^(primary|secondary)$"),
    current_user: dict = Depends(require_student),
    db: Database = Depends(get_database)
):
    """Set resume slot to 'primary' or 'secondary'."""
    resume_service = ResumeService(db)
    
    updated = await resume_service.set_resume_slot(resume_id, current_user["id"], slot)
    return DataResponse(data=ResumeOut(**serialize_mongo_doc(updated)))


@router.get("", response_model=DataResponse[List[ResumeOut]])
async def get_my_resumes(
    current_user: dict = Depends(require_student),
    db: Database = Depends(get_database)
):
    """Get all resumes for student."""
    resume_service = ResumeService(db)
    
    resumes = await resume_service.get_student_resumes(current_user["id"])
    return DataResponse(data=[ResumeOut(**serialize_mongo_doc(r)) for r in resumes])


@router.get("/{resume_id}", response_model=DataResponse[ResumeOut])
async def get_resume(
    resume_id: str,
    current_user: dict = Depends(require_student),
    db: Database = Depends(get_database)
):
    """Get specific resume by ID."""
    resume_service = ResumeService(db)
    
    resume = await resume_service.get_resume_by_id(resume_id, current_user["id"])
    return DataResponse(data=ResumeOut(**serialize_mongo_doc(resume)))


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


@router.post("/{resume_id}/enhancements", response_model=DataResponse[List[ImprovementOut]])
async def generate_resume_enhancements(
    resume_id: str,
    request: ResumeEnhancementRequest,
    current_user: dict = Depends(require_student),
    db: Database = Depends(get_database)
):
    """Generate Gemini rewrites grounded in the selected student's saved resume."""
    resume_service = ResumeService(db)
    improvements = await resume_service.generate_resume_improvements(
        resume_id, current_user["id"], request.target_role
    )
    return DataResponse(data=[ImprovementOut(**item) for item in improvements])


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
    """Download resume file — redirects to Cloudinary Storage URL."""
    resume_service = ResumeService(db)
    
    resume = await resume_service.get_resume_by_id(resume_id, current_user["id"])
    
    cloudinary_url = resume.get("cloudinary_url")
    if not cloudinary_url:
        raise HTTPException(status_code=404, detail="Resume file not found")
    
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=cloudinary_url)
