"""
Auth Schemas - Pydantic models for authentication
"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime


class SignupRequest(BaseModel):
    """User registration request — FRD v3.0 FR-1.2"""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    full_name: str = Field(..., min_length=2, max_length=100)
    company_name: Optional[str] = Field(None, max_length=200)
    store_url: Optional[str] = Field(None, max_length=500)  # FR-1.2.3
    
    @validator('password')
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class LoginRequest(BaseModel):
    """User login request"""
    email: EmailStr
    password: str
    remember_me: Optional[bool] = False


class TokenResponse(BaseModel):
    """JWT token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


class RefreshTokenRequest(BaseModel):
    """Refresh token request"""
    refresh_token: str


class PasswordChangeRequest(BaseModel):
    """Password change request"""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)
    
    @validator('new_password')
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class PasswordResetRequest(BaseModel):
    """Password reset request"""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation"""
    token: str
    new_password: str = Field(..., min_length=8, max_length=100)


class UserResponse(BaseModel):
    """User response (safe for client)"""
    id: int
    email: str
    name: str
    full_name: Optional[str]
    avatar_url: Optional[str]
    initials: str
    role: str
    status: str
    company_name: Optional[str]
    timezone: str
    preferred_language: str
    onboarding_completed: bool
    onboarding_step: int
    created_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class UserUpdateRequest(BaseModel):
    """User profile update request"""
    full_name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    company_name: Optional[str] = Field(None, max_length=200)
    timezone: Optional[str] = Field(None, max_length=50)
    preferred_language: Optional[str] = Field(None, max_length=10)
    avatar_url: Optional[str] = Field(None, max_length=500)


class OnboardingUpdateRequest(BaseModel):
    """Onboarding progress update"""
    step: int = Field(..., ge=0, le=5)
    completed: Optional[bool] = False
    data: Optional[dict] = None
