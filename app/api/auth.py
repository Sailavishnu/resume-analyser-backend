"""
Authentication API routes.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.config import settings
from app.core.security import hash_password
from pymongo.database import Database

from app.core.dependencies import get_current_user
from app.cloud.mongodb import get_database
from app.schemas.auth import SignUpRequest, LoginRequest, AdminLoginRequest, TokenResponse, RefreshRequest, MeResponse
from app.schemas.common import DataResponse, MessageResponse
from app.services.auth_service import AuthService
from app.utils.dates import utc_now

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", response_model=DataResponse[TokenResponse])
async def sign_up(
    request: SignUpRequest,
    db: Database = Depends(get_database)
):
    """Register a new user account."""
    auth_service = AuthService(db)
    
    # Register user
    user = await auth_service.register_user(
        full_name=request.full_name,
        email=request.email,
        password=request.password,
        role=request.role
    )
    
    # Create tokens
    tokens = auth_service.create_tokens(user)
    
    return DataResponse(data=TokenResponse(**tokens))


@router.post("/login", response_model=DataResponse[TokenResponse])
async def login(
    request: LoginRequest,
    db: Database = Depends(get_database)
):
    """Authenticate user and return tokens."""
    auth_service = AuthService(db)
    
    # Authenticate
    user = await auth_service.authenticate_user(request.email, request.password)
    
    # Create tokens
    tokens = auth_service.create_tokens(user)
    
    return DataResponse(data=TokenResponse(**tokens))


@router.post("/admin-login", response_model=DataResponse[TokenResponse])
async def admin_login(request: AdminLoginRequest, db: Database = Depends(get_database)):
    """Authenticate the configured admin and issue a normal, database-backed JWT."""
    if not settings.ADMIN_ID or not settings.ADMIN_PASSWORD or not settings.SECRET_KEY:
        raise HTTPException(status_code=503, detail="Admin authentication is not configured")
    if request.admin_id != settings.ADMIN_ID or request.password != settings.ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid admin ID or password")

    admin_email = settings.ADMIN_EMAIL.lower()
    user = db["users"].find_one({"email": admin_email})
    if user is None:
        user_doc = {
            "email": admin_email,
            "password_hash": hash_password(settings.ADMIN_PASSWORD),
            "full_name": "Platform Administrator",
            "role": "admin",
            "is_active": True,
            "is_verified": True,
            "created_at": utc_now(),
            "last_login_at": utc_now(),
        }
        user_doc["_id"] = db["users"].insert_one(user_doc).inserted_id
        user = user_doc
    else:
        if user.get("role") != "admin" or not user.get("is_active", True):
            raise HTTPException(status_code=403, detail="Configured admin account is disabled or has an invalid role")
        if not user.get("full_name"):
            user["full_name"] = user.get("name") or "Platform Administrator"
            db["users"].update_one(
                {"_id": user["_id"]},
                {"$set": {"full_name": user["full_name"]}},
            )

    user["id"] = str(user["_id"])
    db["users"].update_one({"_id": user["_id"]}, {"$set": {"last_login_at": utc_now()}})
    tokens = AuthService(db).create_tokens(user)
    return DataResponse(data=TokenResponse(**tokens))


@router.post("/refresh", response_model=DataResponse[TokenResponse])
async def refresh_token(
    request: RefreshRequest,
    db: Database = Depends(get_database)
):
    """Refresh access token using refresh token."""
    # This would verify refresh token and issue new access token
    # Simplified implementation for now
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Refresh token endpoint not implemented yet"
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(current_user: dict = Depends(get_current_user)):
    """Logout user (invalidate tokens)."""
    # In a production system, you'd blacklist the token
    # For now, just return success (client should discard token)
    return MessageResponse(message="Logged out successfully")


@router.get("/me", response_model=DataResponse[MeResponse])
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current authenticated user information."""
    user_data = MeResponse(
        id=current_user["id"],
        email=current_user["email"],
        full_name=current_user["full_name"],
        role=current_user["role"],
        is_active=current_user.get("is_active", True),
        is_verified=current_user.get("is_verified", False)
    )
    
    return DataResponse(data=user_data)
