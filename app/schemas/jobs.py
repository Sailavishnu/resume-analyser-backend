from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime


class MatchingConfig(BaseModel):
    skills: int = 40
    experience: int = 30
    education: int = 15
    projects: int = 15

    @field_validator("skills", "experience", "education", "projects", mode="before")
    @classmethod
    def non_negative(cls, v):
        if v < 0:
            raise ValueError("Weights must be non-negative")
        return v

    def validate_total(self):
        if self.skills + self.experience + self.education + self.projects != 100:
            raise ValueError("Matching config weights must sum to 100")


class JobCreateRequest(BaseModel):
    title: str
    description: str
    location: str
    work_mode: str = "On-site"      # Remote | On-site | Hybrid
    experience_min: int = 0
    experience_max: int = 2
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    required_skills: list[str] = []
    preferred_skills: list[str] = []
    matching_config: Optional[MatchingConfig] = None
    expires_at: Optional[datetime] = None


class JobUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    work_mode: Optional[str] = None
    experience_min: Optional[int] = None
    experience_max: Optional[int] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    required_skills: Optional[list[str]] = None
    preferred_skills: Optional[list[str]] = None
    matching_config: Optional[MatchingConfig] = None
    status: Optional[str] = None
    expires_at: Optional[datetime] = None


class JobOut(BaseModel):
    id: str
    company_id: str
    created_by: str
    title: str
    description: str
    location: str
    work_mode: str
    experience_min: int
    experience_max: int
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    status: str = "draft"           # draft | active | paused | closed
    required_skills: list[str] = []
    preferred_skills: list[str] = []
    matching_config: MatchingConfig = MatchingConfig()
    applicant_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    # Company info (denormalised for list views)
    company_name: Optional[str] = None
    company_logo: Optional[str] = None
