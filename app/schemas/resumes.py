from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ResumeOut(BaseModel):
    id: str
    student_id: str
    name: str
    file_name: str
    file_type: str
    file_size: int
    cloudinary_public_id: Optional[str] = None
    cloudinary_secure_url: Optional[str] = None
    version: int = 1
    is_current: bool = True
    status: str = "uploaded"          # uploaded | processing | analyzed | failed
    analysis_status: Optional[str] = None
    analysis_progress: Optional[int] = None
    analysis_stage: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ResumeUpdateRequest(BaseModel):
    name: Optional[str] = None
    is_current: Optional[bool] = None


class AnalysisStatusOut(BaseModel):
    resume_id: str
    status: str
    analysis_progress: Optional[int] = None
    analysis_stage: Optional[str] = None


class ParsedSkills(BaseModel):
    languages: list[str] = []
    frameworks: list[str] = []
    databases: list[str] = []
    tools: list[str] = []
    concepts: list[str] = []
    others: list[str] = []


class ParsedProject(BaseModel):
    project_name: str
    period: Optional[str] = None
    tech_stack: list[str] = []
    description: Optional[str] = None
    key_points: list[str] = []
    impact: Optional[str] = None


class ParsedExperience(BaseModel):
    company: str
    position: str
    type: str = "Internship"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    duration: Optional[str] = None
    is_current: bool = False
    location: Optional[str] = None
    description: Optional[str] = None
    key_points: list[str] = []
    skills: list[str] = []


class ParsedEducation(BaseModel):
    degree: str
    field: Optional[str] = None
    institution: str
    graduation_year: Optional[int] = None
    gpa: Optional[float] = None
    additional_info: Optional[str] = None


class ParsedCertification(BaseModel):
    cert_name: str
    issuer: Optional[str] = None
    issue_date: Optional[str] = None
    expiry_date: Optional[str] = None
    credential_url: Optional[str] = None


class ParsedResumeData(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    summary: Optional[str] = None
    skills: Optional[ParsedSkills] = None
    projects: list[ParsedProject] = []
    experience: list[ParsedExperience] = []
    education: list[ParsedEducation] = []
    certifications: list[ParsedCertification] = []
    raw_text: Optional[str] = None


class SectionScore(BaseModel):
    skills: int = 0
    experience: int = 0
    projects: int = 0
    education: int = 0
    formatting: int = 0
    keywords: int = 0
    impact: int = 0
    completeness: int = 0


class ImprovementSuggestion(BaseModel):
    category: str
    priority: str  # high | medium | low
    suggestion: str
    example: Optional[str] = None


class ResumeAnalysisOut(BaseModel):
    id: str
    resume_id: str
    overall_score: int
    ats_score: int
    section_scores: SectionScore
    strengths: list[str] = []
    warnings: list[str] = []
    critical_issues: list[str] = []
    matched_keywords: list[str] = []
    missing_keywords: list[str] = []
    recommendations: list[ImprovementSuggestion] = []
    analysis_version: str = "1.0"
    created_at: Optional[datetime] = None


class ImprovementOut(BaseModel):
    id: str
    resume_id: str
    student_id: str
    section: str
    original_text: str
    suggested_text: str
    reason: str
    improvement_type: str   # impact | concise | ats | technical | professional | quantified
    status: str = "pending" # pending | accepted | rejected
    created_at: Optional[datetime] = None


class ImprovementUpdateRequest(BaseModel):
    status: str  # accepted | rejected


class ResumeVersionOut(BaseModel):
    id: str
    resume_id: str
    version_number: int
    target_role: Optional[str] = None
    ats_score: Optional[int] = None
    resume_health_score: Optional[int] = None
    content: Optional[dict] = None
    created_at: Optional[datetime] = None
