"""
Authentication and user management service.
"""
from bson import ObjectId
from pymongo.database import Database

from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.utils.dates import utc_now
from app.db import collections as C


class AuthService:
    def __init__(self, db: Database):
        self.db = db
    
    async def register_user(self, full_name: str, email: str, password: str, role: str) -> dict:
        """
        Register a new user and create their profile.
        Returns the created user document.
        """
        # Check if user already exists
        existing = self.db[C.USERS].find_one({"email": email})
        if existing:
            raise ConflictError("Email already registered")
        
        # Create user
        user_doc = {
            "email": email,
            "password_hash": hash_password(password),
            "full_name": full_name,
            "role": role,
            "is_active": True,
            "is_verified": True,  # Auto-verify for demo
            "created_at": utc_now(),
            "last_login_at": None,
        }
        
        result = self.db[C.USERS].insert_one(user_doc)
        user_id = result.inserted_id
        
        # Create role-specific profile
        if role == "student":
            self._create_student_profile(user_id)
        elif role == "hr":
            self._create_recruiter_profile(user_id)
        
        # Return user without password hash
        user_doc["_id"] = user_id
        user_doc.pop("password_hash")
        return user_doc
    
    async def authenticate_user(self, email: str, password: str) -> dict:
        """
        Authenticate user and update last login.
        Returns user document on success.
        """
        user = self.db[C.USERS].find_one({"email": email})
        if not user:
            raise NotFoundError("Invalid email or password")
        
        if not verify_password(password, user["password_hash"]):
            raise ValidationError("Invalid email or password")
        
        if not user.get("is_active", True):
            raise ValidationError("Account is disabled")
        
        # Update last login
        self.db[C.USERS].update_one(
            {"_id": user["_id"]},
            {"$set": {"last_login_at": utc_now()}}
        )
        
        # Return without password hash
        user.pop("password_hash", None)
        return user
    
    def create_tokens(self, user: dict) -> dict:
        """Create access and refresh tokens for authenticated user."""
        user_id = str(user["_id"])
        role = user["role"]
        
        access_token = create_access_token(user_id, role)
        refresh_token = create_refresh_token(user_id, role)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user_id": user_id,
            "role": role,
            "full_name": user["full_name"]
        }
    
    def get_user_by_id(self, user_id: str) -> dict | None:
        """Get user by ID, excluding password hash."""
        user = self.db[C.USERS].find_one({"_id": ObjectId(user_id)})
        if user:
            user.pop("password_hash", None)
            user["id"] = str(user["_id"])
        return user
    
    def _create_student_profile(self, user_id: ObjectId) -> None:
        """Create default student profile."""
        profile = {
            "user_id": user_id,
            "target_role": None,
            "bio": None,
            "phone": None,
            "location": None,
            "preferred_work_mode": None,
            "preferred_locations": [],
            "profile_completion": 20,  # Base score for having account
            "career_readiness_score": 25,
            "current_streak": 0,
            "longest_streak": 0,
            "resume_visibility": "recruiters",
            "created_at": utc_now(),
            "updated_at": utc_now(),
        }
        self.db[C.STUDENT_PROFILES].insert_one(profile)
    
    def _create_recruiter_profile(self, user_id: ObjectId) -> None:
        """Create default recruiter profile."""
        profile = {
            "user_id": user_id,
            "company_id": None,
            "job_title": None,
            "phone": None,
            "is_verified": False,
            "verification_status": "pending",
            "created_at": utc_now(),
            "updated_at": utc_now(),
        }
        self.db[C.RECRUITER_PROFILES].insert_one(profile)