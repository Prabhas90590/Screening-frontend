"""User account database model for authentication.

Represents a single analyst account. Passwords are stored as bcrypt hashes
(never plain-text). Includes email verification flags and password reset tokens.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class UserRecord(BaseModel):
    """Database model for the 'users' table."""

    id: str = Field(..., description="UUID primary key (gen_random_uuid() on PostgreSQL)")
    email: str = Field(..., description="Unique login email address")
    hashed_password: str = Field(..., description="bcrypt hash of the user's password (never the raw password)")
    full_name: Optional[str] = Field(None, description="Display name shown in the UI header")
    is_active: bool = Field(default=True, description="False = account disabled (soft-delete)")
    is_verified: bool = Field(default=False, description="True = corporate email ownership confirmed via OTP")
    verification_code: Optional[str] = Field(None, description="Current 6-digit email activation code")
    verification_expires_at: Optional[datetime] = Field(None, description="Expiration timestamp for activation code")
    reset_token: Optional[str] = Field(None, description="Current 6-digit password reset authorization code")
    reset_expires_at: Optional[datetime] = Field(None, description="Expiration timestamp for password reset code")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Account creation timestamp (UTC)")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last profile-update timestamp (UTC)")
    created_by_email: Optional[str] = Field(
        None,
        description="Reserved for data-ownership migration: original owner's email"
    )

    class Config:
        from_attributes = True
