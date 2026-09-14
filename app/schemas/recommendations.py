from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class JobRecommendationOut(BaseModel):
    job_id: str
    job_title: str
    company_name: str
    company_logo: Optional[str] = None
    location: str
    work_mode: str
    match_score: int
    matched_skills: list[str] = []
    missing_skills: list[str] = []
    experience_match: str
    salary_range: Optional[str] = None
    posted_at: Optional[datetime] = None


class RecommendationFilters(BaseModel):
    target_role: Optional[str] = None
    location: Optional[str] = None
    work_mode: Optional[str] = None
    min_match_score: Optional[int] = None
    max_experience: Optional[int] = None