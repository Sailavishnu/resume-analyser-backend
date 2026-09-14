"""
ATS scoring and resume analysis API routes.
"""
from fastapi import APIRouter, Depends
from pymongo.database import Database

from app.core.dependencies import get_current_user, require_student
from app.db.mongodb import get_database
from app.schemas.common import DataResponse
from app.schemas.ats import ATSAnalysisOut
from app.services.resume_service import ResumeService

router = APIRouter(prefix="/ats", tags=["ATS Analysis"])


@router.get("/{resume_id}", response_model=DataResponse[ATSAnalysisOut])
async def get_ats_analysis(
    resume_id: str,
    current_user: dict = Depends(require_student),
    db: Database = Depends(get_database)
):
    """Get ATS compatibility analysis for resume."""
    resume_service = ResumeService(db)
    
    # Get resume analysis (which includes ATS scoring)
    analysis = await resume_service.get_resume_analysis(resume_id, current_user["id"])
    
    # Convert to ATS-specific response
    ats_analysis = ATSAnalysisOut(
        id=analysis["id"],
        resume_id=resume_id,
        overall_score=analysis.get("ats_score", 0),
        section_detection_score=85,  # Would calculate from analysis
        keyword_coverage_score=analysis.get("ats_score", 0),
        formatting_score=analysis.get("section_scores", {}).get("formatting", 0),
        readability_score=80,  # Would calculate
        contact_info_score=90,  # Would calculate
        checks=[],  # Would populate from detailed checks
        matched_keywords=analysis.get("matched_keywords", []),
        missing_keywords=analysis.get("missing_keywords", []),
        formatting_warnings=[],
        recommendations=[r.get("suggestion", "") for r in analysis.get("recommendations", [])],
        created_at=analysis.get("created_at")
    )
    
    return DataResponse(data=ats_analysis)


@router.post("/{resume_id}/analyze", response_model=DataResponse[ATSAnalysisOut])
async def trigger_ats_analysis(
    resume_id: str,
    current_user: dict = Depends(require_student),
    db: Database = Depends(get_database)
):
    """Trigger fresh ATS analysis of resume."""
    # This would re-run ATS analysis specifically
    # For now, just return existing analysis
    return await get_ats_analysis(resume_id, current_user, db)
