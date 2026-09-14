"""
Authentication API routes.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.database import Database

from app.core.dependencies import get_current_user
from app.db.mongodb import get_database
from app.schemas.auth import SignUpRequest, LoginRequest, TokenResponse, RefreshRequest, MeResponse
from app.schemas.common import DataResponse, MessageResponse
from app.services.auth_service import AuthService

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