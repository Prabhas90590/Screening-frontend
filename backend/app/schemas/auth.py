"""Authentication request and response Pydantic schemas.

Defines strict input validation, corporate domain enforcement (@zeniusit.com),
password security requirements, email verification, and password reset models.
"""

from datetime import datetime, timezone
import re
from typing import Optional
from pydantic import BaseModel, Field, field_validator

ALLOWED_CORPORATE_DOMAIN = "@zeniusit.com"


class UserSignupRequest(BaseModel):
    """Payload for open user registration (POST /api/auth/signup)."""

    email: str = Field(..., description="Corporate email address ending in @zeniusit.com")
    password: str = Field(..., min_length=8, description="Password (at least 8 characters, letters and numbers)")
    full_name: Optional[str] = Field(None, max_length=128, description="Display name for header UI")

    @field_validator("email")
    @classmethod
    def validate_corporate_email(cls, value: str) -> str:
        clean = value.strip().lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", clean):
            raise ValueError("Invalid email format.")
        if not clean.endswith(ALLOWED_CORPORATE_DOMAIN):
            raise ValueError(
                f"Registration is restricted to authorized {ALLOWED_CORPORATE_DOMAIN} corporate email addresses."
            )
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


class SignupInitResponse(BaseModel):
    """Response returned upon initial signup initiation requiring OTP verification."""

    message: str = Field(..., description="Status explanation")
    email: str = Field(..., description="Target email address")
    requires_verification: bool = Field(True, description="Always true until OTP verified")
    verification_code: Optional[str] = Field(None, description="6-digit activation code for instant preview & dev verification")


class VerifyEmailRequest(BaseModel):
    """Payload for verifying email ownership via 6-digit OTP code."""

    email: str = Field(..., description="Registered corporate email")
    code: str = Field(..., min_length=4, max_length=16, description="6-digit verification code")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("code")
    @classmethod
    def clean_code(cls, value: str) -> str:
        return value.strip()


class ResendVerificationRequest(BaseModel):
    """Payload to request a new verification code."""

    email: str = Field(..., description="Target corporate email")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class ForgotPasswordRequest(BaseModel):
    """Payload to request a password reset code."""

    email: str = Field(..., description="Target corporate email")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class ResetPasswordRequest(BaseModel):
    """Payload to set a new password using a verified 6-digit authorization code."""

    email: str = Field(..., description="Corporate email address")
    code: str = Field(..., description="6-digit reset authorization code")
    new_password: str = Field(..., min_length=8, description="New account password")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("code")
    @classmethod
    def clean_code(cls, value: str) -> str:
        return value.strip()

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        if not re.search(r"[A-Za-z]", value):
            raise ValueError("Password must contain at least one letter.")
        if not re.search(r"[0-9]", value):
            raise ValueError("Password must contain at least one number.")
        return value


class ChangePasswordRequest(BaseModel):
    """Payload for an authenticated user to change their password in-app."""

    current_password: str = Field(..., description="Current account password")
    new_password: str = Field(..., min_length=8, description="New desired password")

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        if not re.search(r"[A-Za-z]", value):
            raise ValueError("Password must contain at least one letter.")
        if not re.search(r"[0-9]", value):
            raise ValueError("Password must contain at least one number.")
        return value


class UpdateProfileRequest(BaseModel):
    """Payload to update analyst profile display name."""

    full_name: str = Field(..., min_length=2, max_length=128, description="Updated full name")


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
    is_verified: bool = Field(True, description="Corporate email verification status")
    created_at: datetime = Field(..., description="Account creation timestamp (UTC)")

    class Config:
        from_attributes = True


class AuthTokenResponse(BaseModel):
    """Standard JWT authentication response returned on successful login or verification."""

    access_token: str = Field(..., description="Signed JWT Bearer access token")
    token_type: str = Field("bearer", description="Token scheme (bearer)")
    expires_in: int = Field(3600, description="Token validity duration in seconds (1 hour)")
    user: UserProfileResponse = Field(..., description="Basic profile of the authenticated user")


class LogoutResponse(BaseModel):
    """Confirmation message on session termination."""

    message: str = Field("Logged out successfully.", description="Status message")


class GenericMessageResponse(BaseModel):
    """Generic status response message with optional authorization code preview."""

    message: str = Field(..., description="Status feedback message")
    code: Optional[str] = Field(None, description="6-digit authorization code for instant preview & dev verification")


class SessionPingResponse(BaseModel):
    """Heartbeat response confirming active session status."""

    status: str = Field("active", description="Session state")
    user_id: str = Field(..., description="Active user UUID")
    email: str = Field(..., description="Active user email")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Server UTC timestamp")
