"""User account database model for authentication.

Represents a single analyst account. Passwords are stored as bcrypt hashes
(never plain-text). The 'created_by_email' column is reserved for the future
data-ownership migration that will assign existing strategy profiles and
screening runs to the primary analyst email.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserRecord(BaseModel):
    """Database model for the 'users' table."""

    id: str = Field(..., description="UUID primary key (gen_random_uuid() on Postgres, str UUID on SQLite)")
    email: str = Field(..., description="Unique login email address")
    hashed_password: str = Field(..., description="bcrypt hash of the user's password (never the raw password)")
    full_name: Optional[str] = Field(None, description="Display name shown in the UI header")
    is_active: bool = Field(default=True, description="False = account disabled (soft-delete)")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Account creation timestamp (UTC)")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last profile-update timestamp (UTC)")
    created_by_email: Optional[str] = Field(
        None,
        description="Reserved for Phase-9 data-ownership migration: original owner's email"
    )

    class Config:
        # Allow construction from ORM row-dicts / psycopg2 Row objects
        from_attributes = True

