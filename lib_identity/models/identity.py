from datetime import datetime, date
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


# ── Enums ────────────────────────────────────────────────────

class UserType(str, Enum):
    admin = "admin"
    school_admin = "school_admin"


# ── Auth Models ──────────────────────────────────────────────

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
    subscription_status: str = "active"
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


# ── Password Models ──────────────────────────────────────────

class CreateResetPasswordRequest(BaseModel):
    user_code: str
    previous_password: str
    new_password: str


class ResetPasswordResponse(BaseModel):
    message: str


# ── Username Models ──────────────────────────────────────────

class UsernameExistsResponse(BaseModel):
    can_use: bool
    suggestion: Optional[str] = None


# ── Profile Models (school_admin use) ────────────────────────

class UserProfileResponse(BaseModel):
    user_code: str
    username: str
    email: str
    user_type: str
    school_name: Optional[str] = None
    school_logo: Optional[str] = None
    owner_name: Optional[str] = None
    phone_number: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    subscription_plan: Optional[str] = None
    subscription_start: Optional[date] = None
    subscription_end: Optional[date] = None


class UpdateUserProfileRequest(BaseModel):
    """What a school_admin can update about themselves"""
    owner_name: Optional[str] = None
    phone_number: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    school_logo: Optional[str] = None


class UpdateUserProfileResponse(BaseModel):
    message: str


# ── Admin Models (admin use only) ────────────────────────────

class CreateUserRequest(BaseModel):
    username: str
    password: str
    email: str
    school_name: Optional[str] = None
    owner_name: Optional[str] = None
    phone_number: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    user_type: UserType = UserType.school_admin
    subscription_plan: Optional[str] = None
    subscription_start: Optional[date] = None
    subscription_end: Optional[date] = None
    class_ids: list[int] = []


class CreateUserResponse(BaseModel):
    message: str
    user_code: str
    username: str


class UpdateUserRequest(BaseModel):
    """What an admin can update about any user"""
    school_name: Optional[str] = None
    owner_name: Optional[str] = None
    phone_number: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    user_type: Optional[UserType] = None
    subscription_plan: Optional[str] = None
    subscription_start: Optional[date] = None
    subscription_end: Optional[date] = None
    is_active: Optional[bool] = None
    class_ids: Optional[list[int]] = None


class UpdateUserResponse(BaseModel):
    message: str


class UserListItem(BaseModel):
    user_code: str
    username: str
    email: str
    school_name: Optional[str] = None
    school_logo: Optional[str] = None
    owner_name: Optional[str] = None
    phone_number: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    user_type: str
    is_active: bool
    subscription_plan: Optional[str] = None
    subscription_end: Optional[date] = None
    subscription_status: str
    subscription_days_left: Optional[int] = None
    created_at: Optional[datetime] = None
    class_ids: list[int] = []


class UserListResponse(BaseModel):
    users: list[UserListItem]
    total: int


class UploadLogoResponse(BaseModel):
    message: str
    logo_url: str


class UpdateBoardPermissionsRequest(BaseModel):
    class_ids: list[int]


class UpdateBoardPermissionsResponse(BaseModel):
    message: str


# ── Exceptions ───────────────────────────────────────────────

class IdentityError(Exception):
    """Base identity domain error."""


class InvalidCredentialsError(IdentityError):
    """Raised when provided credentials are invalid."""


class SessionCreationError(IdentityError):
    """Raised when a session record cannot be created."""


class TokenValidationError(IdentityError):
    """Raised when a token cannot be validated due to infra issues."""