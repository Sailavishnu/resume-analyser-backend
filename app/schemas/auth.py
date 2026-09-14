from pydantic import BaseModel, EmailStr, field_validator
import re


class SignUpRequest(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    role: str = "student"  # student | hr

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        if v not in ("student", "hr"):
            raise ValueError("Role must be 'student' or 'hr'")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    @field_validator("full_name")
    @classmethod
    def validate_name(cls, v):
        if len(v.strip()) < 2:
            raise ValueError("Full name must be at least 2 characters")
        return v.strip()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: str
    role: str
    full_name: str


class RefreshRequest(BaseModel):
    refresh_token: str


class MeResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    is_verified: bool
