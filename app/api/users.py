"""
User management and profile API routes.
"""
from fastapi import APIRouter, Depends
from pymongo.database import Database
from bson import ObjectId

from app.core.dependencies import get_current_user, require_student, require_hr, require_admin
from app.db.mongodb import get_database
from app.schemas.common import DataResponse, MessageResponse
from app.schemas.users import (
    UserOut, UpdateProfileRequest, StudentProfileOut, 
    UpdateStudentProfileRequest, RecruiterProfileOut, AdminUserListItem
)
from app.db import collections as C
from app.utils.dates import utc_now

router = APIRouter(prefix="/users", tags=["Users"])


# ─── User profile routes ───────────────────────────────────────────────────

@router.get("/me", response_model=DataResponse[UserOut])
async def get_my_profile(
    current_user: dict = Depends(get_current_user)
):
    """Get current user profile."""
    user_data = UserOut(
        id=current_user["id"],
        email=current_user["email"],
        full_name=current_user["full_name"],
        role=current_user["role"],
        is_active=current_user.get("is_active", True),
        is_verified=current_user.get("is_verified", False),
        created_at=current_user.get("created_at"),
        last_login_at=current_user.get("last_login_at")
    )
    
    return DataResponse(data=user_data)


@router.patch("/me", response_model=DataResponse[UserOut])
async def update_my_profile(
    request: UpdateProfileRequest,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_database)
):
    """Update current user profile."""
    updates = {}
    if request.full_name:
        updates["full_name"] = request.full_name
    
    if updates:
        updates["updated_at"] = utc_now()
        db[C.USERS].update_one(
            {"_id": ObjectId(current_user["id"])},
            {"$set": updates}
        )
    
    # Return updated user data
    updated_user = db[C.USERS].find_one({"_id": ObjectId(current_user["id"])})
    updated_user.pop("password_hash", None)
    updated_user["id"] = str(updated_user["_id"])
    
    return DataResponse(data=UserOut(**updated_user))


# ─── Student profile routes ────────────────────────────────────────────────

@router.get("/student/profile", response_model=DataResponse[StudentProfileOut])
async def get_student_profile(
    current_user: dict = Depends(require_student),
    db: Database = Depends(get_database)
):
    """Get student profile details."""
    profile = db[C.STUDENT_PROFILES].find_one({"user_id": ObjectId(current_user["id"])})
    
    if not profile:
        # Create default profile if not exists
        profile = {
            "user_id": ObjectId(current_user["id"]),
            "target_role": None,
            "bio": None,
            "phone": None,
            "location": None,
            "preferred_work_mode": None,
            "preferred_locations": [],
            "profile_completion": 20,
            "career_readiness_score": 25,
            "current_streak": 0,
            "longest_streak": 0,
            "resume_visibility": "recruiters",
            "created_at": utc_now(),
            "updated_at": utc_now(),
        }
        result = db[C.STUDENT_PROFILES].insert_one(profile)
        profile["_id"] = result.inserted_id
    
    profile["id"] = str(profile["_id"])
    
    return DataResponse(data=StudentProfileOut(**profile))


@router.patch("/student/profile", response_model=DataResponse[StudentProfileOut])
async def update_student_profile(
    request: UpdateStudentProfileRequest,
    current_user: dict = Depends(require_student),
    db: Database = Depends(get_database)
):
    """Update student profile details."""
    updates = {}
    
    # Only update provided fields
    if request.target_role is not None:
        updates["target_role"] = request.target_role
    if request.bio is not None:
        updates["bio"] = request.bio
    if request.phone is not None:
        updates["phone"] = request.phone
    if request.location is not None:
        updates["location"] = request.location
    if request.preferred_work_mode is not None:
        updates["preferred_work_mode"] = request.preferred_work_mode
    if request.preferred_locations is not None:
        updates["preferred_locations"] = request.preferred_locations
    if request.resume_visibility is not None:
        updates["resume_visibility"] = request.resume_visibility
    
    if updates:
        updates["updated_at"] = utc_now()
        
        # Calculate profile completion
        total_fields = 7  # target_role, bio, phone, location, etc.
        filled_fields = sum(1 for v in updates.values() if v)
        completion = min(100, 20 + (filled_fields * 10))  # 20 base + 10 per field
        updates["profile_completion"] = completion
        
        db[C.STUDENT_PROFILES].update_one(
            {"user_id": ObjectId(current_user["id"])},
            {"$set": updates}
        )
    
    # Return updated profile
    return await get_student_profile(current_user, db)


# ─── HR profile routes ──────────────────────────────────────────────────────

@router.get("/hr/profile", response_model=DataResponse[RecruiterProfileOut])
async def get_hr_profile(
    current_user: dict = Depends(require_hr),
    db: Database = Depends(get_database)
):
    """Get HR profile details."""
    profile = db[C.RECRUITER_PROFILES].find_one({"user_id": ObjectId(current_user["id"])})
    
    if not profile:
        # Create default profile if not exists
        profile = {
            "user_id": ObjectId(current_user["id"]),
            "company_id": None,
            "job_title": None,
            "phone": None,
            "is_verified": False,
            "verification_status": "pending",
            "created_at": utc_now(),
            "updated_at": utc_now(),
        }
        result = db[C.RECRUITER_PROFILES].insert_one(profile)
        profile["_id"] = result.inserted_id
    
    profile["id"] = str(profile["_id"])
    
    return DataResponse(data=RecruiterProfileOut(**profile))


# ─── Admin user management routes ──────────────────────────────────────────

@router.get("/admin/users", response_model=DataResponse[list[AdminUserListItem]])
async def get_all_users(
    current_user: dict = Depends(require_admin),
    db: Database = Depends(get_database)
):
    """Get all users for admin management."""
    cursor = db[C.USERS].find({}).sort("created_at", -1).limit(100)
    
    users = []
    for user in cursor:
        user.pop("password_hash", None)
        user["id"] = str(user["_id"])
        users.append(AdminUserListItem(**user))
    
    return DataResponse(data=users)