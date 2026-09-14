from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ATSCheckResult(BaseModel):
    check_name: str
    passed: bool
    score: int
    message: str
    details: Optional[str] = None


class ATSAnalysisOut(BaseModel):
    id: str
    resume_id: str
    overall_score: int
    section_detection_score: int
    keyword_coverage_score: int
    formatting_score: int
    readability_score: int
    contact_info_score: int
    checks: list[ATSCheckResult] = []
    matched_keywords: list[str] = []
    missing_keywords: list[str] = []
    formatting_warnings: list[str] = []
    recommendations: list[str] = []
    created_at: Optional[datetime] = None