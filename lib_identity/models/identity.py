from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., description="Username or email")
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user_code: str
    username: str
    user_type: str
    school_name: Optional[str] = None
    subscription_end: Optional[date] = None
    subscription_status: str = "active"       # "active" | "expired" | "expiring_soon"
    subscription_days_left: Optional[int] = None


class LogoutRequest(BaseModel):
    user_code: str


class LogoutResponse(BaseModel):
    message: str


class TokenValidationRequest(BaseModel):
    token: str


class TokenValidationResponse(BaseModel):
    valid: bool
    user_code: Optional[str] = None
    username: Optional[str] = None
    user_type: Optional[str] = None
    expires_at: Optional[datetime] = None


class UsernameExistsResponse(BaseModel):
    can_use: bool
    suggestion: str | None = None


class CreateResetPasswordRequest(BaseModel):
    user_code: str
    previous_password: str
    new_password: str


class ResetPasswordResponse(BaseModel):
    message: str


class UserProfileResponse(BaseModel):
    user_code: str
    username: str
    email: str
    user_type: str
    school_name: Optional[str] = None
    owner_name: Optional[str] = None
    phone_number: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    subscription_plan: Optional[str] = None
    subscription_start: Optional[date] = None
    subscription_end: Optional[date] = None


class UpdateUserProfileRequest(BaseModel):
    school_name: Optional[str] = None
    owner_name: Optional[str] = None
    phone_number: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None


class UpdateUserProfileResponse(BaseModel):
    message: str


class IdentityError(Exception):
    """Base identity domain error."""


class InvalidCredentialsError(IdentityError):
    """Raised when provided credentials are invalid."""


class SessionCreationError(IdentityError):
    """Raised when a session record cannot be created."""


class TokenValidationError(IdentityError):
    """Raised when a token cannot be validated due to infra issues."""