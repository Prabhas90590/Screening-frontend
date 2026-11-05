"""Authentication request and response Pydantic schemas (Phase 3 & Phase 4).

Defines strict input validation, security policies (password strength, email validation),
and clean JSON serialization models for the auth endpoints.
"""

from datetime import datetime, timezone
import re
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class UserSignupRequest(BaseModel):
    """Payload for open user registration (POST /api/auth/signup)."""

    email: str = Field(..., description="User's email address (login identifier)")
    password: str = Field(..., min_length=8, description="Password (at least 8 characters, letters and numbers)")
    full_name: Optional[str] = Field(None, max_length=128, description="Display name for header UI")

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, value: str) -> str:
        clean = value.strip().lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", clean):
            raise ValueError("Invalid email format.")
        return clean

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        if not re.search(r"[A-Za-z]", value):
            raise ValueError("Password must contain at least one letter.")
        if not re.search(r"[0-9]", value):
            raise ValueError("Password must contain at least one number.")
        return value


class UserLoginRequest(BaseModel):
    """Payload for credentials login (POST /api/auth/login)."""

    email: str = Field(..., description="Registered email address")
    password: str = Field(..., description="Plain-text account password")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class UserProfileResponse(BaseModel):
    """Public user profile data returned to client (never contains hashed_password)."""

    id: str = Field(..., description="User UUID")
    email: str = Field(..., description="User email")
    full_name: Optional[str] = Field(None, description="Display name")
    is_active: bool = Field(True, description="Account active status")
    created_at: datetime = Field(..., description="Account creation timestamp (UTC)")

    class Config:
        from_attributes = True


class AuthTokenResponse(BaseModel):
    """Standard JWT authentication response returned on successful login or sign-up."""

    access_token: str = Field(..., description="Signed JWT Bearer access token")
    token_type: str = Field("bearer", description="Token scheme (bearer)")
    expires_in: int = Field(3600, description="Token validity duration in seconds (1 hour)")
    user: UserProfileResponse = Field(..., description="Basic profile of the authenticated user")


class LogoutResponse(BaseModel):
    """Confirmation message on session termination."""

    message: str = Field("Logged out successfully.", description="Status message")


class SessionPingResponse(BaseModel):
    """Heartbeat response confirming active session status for frontend activity listener (Phase 4)."""

    status: str = Field("active", description="Session state")
    user_id: str = Field(..., description="Active user UUID")
    email: str = Field(..., description="Active user email")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Server UTC timestamp")
