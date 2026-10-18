from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class JDMatchRequest(BaseModel):
    resume_id: str
    job_id: str


class ResumeTextMatchRequest(BaseModel):
    resume_id: str
    job_description: str = Field(min_length=30, max_length=30000)


class MatchFeatures(BaseModel):
    skill_overlap: float
    required_skill_coverage: float
    keyword_overlap: float
    experience_similarity: float
    education_match: float
    project_relevance: float


class JDMatchOut(BaseModel):
    id: str
    student_id: str
    resume_id: str
    job_id: str
    model_version: str
    overall_score: float
    display_score: int
    features: MatchFeatures
    matched_skills: list[str] = []
    partial_skills: list[str] = []
    missing_skills: list[str] = []
    recommendations: list[str] = []
    created_at: Optional[datetime] = None
