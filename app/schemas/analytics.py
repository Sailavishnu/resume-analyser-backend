from pydantic import BaseModel
from typing import Optional


# ─── Student analytics ────────────────────────────────────────────────────────

class CareerReadinessHistory(BaseModel):
    date: str
    score: int


class ApplicationBreakdown(BaseModel):
    applied: int = 0
    under_review: int = 0
    shortlisted: int = 0
    interview: int = 0
    offer: int = 0
    hired: int = 0
    rejected: int = 0
    withdrawn: int = 0


class StudentAnalyticsOut(BaseModel):
    student_id: str
    career_readiness_score: int
    resume_health_score: Optional[int] = None
    ats_score: Optional[int] = None
    current_streak: int = 0
    longest_streak: int = 0
    total_applications: int = 0
    total_interviews: int = 0
    total_assessments: int = 0
    roadmap_progress: int = 0
    career_history: list[CareerReadinessHistory] = []
    application_breakdown: ApplicationBreakdown = ApplicationBreakdown()


# ─── HR analytics ─────────────────────────────────────────────────────────────

class JobMetrics(BaseModel):
    job_id: str
    job_title: str
    total_applicants: int = 0
    shortlisted: int = 0
    interviewed: int = 0
    offered: int = 0
    hired: int = 0
    avg_match_score: Optional[float] = None
    conversion_rate: Optional[float] = None


class PipelineMetrics(BaseModel):
    applied_to_shortlisted: float = 0.0
    shortlisted_to_interviewed: float = 0.0
    interviewed_to_offered: float = 0.0
    offered_to_hired: float = 0.0


class HRAnalyticsOut(BaseModel):
    recruiter_id: str
    company_id: str
    active_jobs: int = 0
    total_applicants: int = 0
    total_shortlisted: int = 0
    total_interviewed: int = 0
    total_hired: int = 0
    avg_match_score: Optional[float] = None
    pipeline_metrics: PipelineMetrics = PipelineMetrics()
    job_metrics: list[JobMetrics] = []
    top_skills: list[str] = []


class JobAnalyticsOut(BaseModel):
    job_id: str
    job_title: str
    company_name: str
    total_applicants: int = 0
    shortlisted: int = 0
    interviewed: int = 0
    offered: int = 0
    hired: int = 0
    rejected: int = 0
    avg_match_score: Optional[float] = None
    conversion_rates: PipelineMetrics = PipelineMetrics()
    top_applicant_skills: list[str] = []
    skill_gap_analysis: dict[str, int] = {}


# ─── Admin analytics ──────────────────────────────────────────────────────────

class UserGrowth(BaseModel):
    date: str
    students: int
    recruiters: int
    total: int


class FeatureUsage(BaseModel):
    feature: str
    usage_count: int


class AdminAnalyticsOut(BaseModel):
    total_users: int = 0
    total_students: int = 0
    total_recruiters: int = 0
    total_companies: int = 0
    total_jobs: int = 0
    total_applications: int = 0
    total_resumes: int = 0
    total_analyses: int = 0
    active_jobs: int = 0
    user_growth: list[UserGrowth] = []
    feature_usage: list[FeatureUsage] = []


class MLAnalyticsOut(BaseModel):
    model_version: str
    total_predictions: int = 0
    avg_confidence: Optional[float] = None
    prediction_distribution: dict[str, int] = {}  # score ranges
    feature_importance: dict[str, float] = {}