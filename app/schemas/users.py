from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class UserOut(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    is_verified: bool
    created_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None


class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = None


class StudentProfileOut(BaseModel):
    id: str
    user_id: str
    target_role: Optional[str] = None
    bio: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    preferred_work_mode: Optional[str] = None
    preferred_locations: list[str] = []
    profile_completion: int = 0
    career_readiness_score: int = 0
    current_streak: int = 0
    longest_streak: int = 0
    resume_visibility: str = "recruiters"
    updated_at: Optional[datetime] = None


class UpdateStudentProfileRequest(BaseModel):
    target_role: Optional[str] = None
    bio: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    preferred_work_mode: Optional[str] = None
    preferred_locations: Optional[list[str]] = None
    resume_visibility: Optional[str] = None


class RecruiterProfileOut(BaseModel):
    id: str
    user_id: str
    company_id: Optional[str] = None
    job_title: Optional[str] = None
    phone: Optional[str] = None
    is_verified: bool = False
    verification_status: str = "pending"
    updated_at: Optional[datetime] = None


class AdminUserListItem(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    is_verified: bool
    created_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
