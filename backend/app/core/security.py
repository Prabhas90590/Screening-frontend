"""Security utilities for password hashing and JWT token management.

This module provides pure, stateless functions used by the auth service.
No database access happens here — this is intentionally kept as a utility layer.
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

logger = logging.getLogger("app.core.security")

# ---------------------------------------------------------------------------
# Password hashing configuration (using native bcrypt)
# ---------------------------------------------------------------------------
# Uses native bcrypt (12 rounds) directly to prevent passlib's 72-byte bug
# with modern bcrypt 4.x / 5.x releases.


def hash_password(plain_password: str) -> str:
    """Hash a plain-text password using bcrypt.

    Args:
        plain_password: The raw password supplied by the user.

    Returns:
        A bcrypt hash string safe to store in the database.
    """
    pwd_bytes = plain_password.encode("utf-8")[:72]
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a stored bcrypt hash.

    Args:
        plain_password:   What the user typed at login.
        hashed_password:  The hash stored in the users table.

    Returns:
        True if the passwords match, False otherwise.
    """
    try:
        pwd_bytes = plain_password.encode("utf-8")[:72]
        hash_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except Exception as e:
        logger.warning(f"Password verification error: {e}")
        return False


# ---------------------------------------------------------------------------
# JWT configuration
# ---------------------------------------------------------------------------
_JWT_ALGORITHM = "HS256"


def _get_jwt_secret() -> str:
    """Read the JWT secret from settings."""
    secret = settings.jwt_secret_key
    if not secret or secret == "YOUR_RANDOM_256_BIT_BASE64":
        logger.warning(
            "JWT_SECRET_KEY is not set or is using the placeholder value. "
            "Set a strong random key in your backend/.env file before deploying to production."
        )
    return secret or "INSECURE_FALLBACK_DO_NOT_USE_IN_PRODUCTION"


def create_access_token(
    user_id: str,
    email: str,
    full_name: Optional[str] = None,
    expires_minutes: Optional[int] = None,
) -> str:
    """Create a signed JWT access token.

    The token payload contains:
        - sub   : user UUID (the primary key in the users table)
        - email : for display purposes
        - name  : full_name for the UI header
        - iat   : issued-at timestamp (used for idle-session checks)
        - exp   : expiry timestamp

    Args:
        user_id:        UUID string of the user record.
        email:          User's email address.
        full_name:      Optional display name.
        expires_minutes: Token lifetime in minutes (defaults to settings.access_token_expire_minutes).

    Returns:
        A signed JWT string to be returned to the client.
    """
    if expires_minutes is None:
        expires_minutes = settings.access_token_expire_minutes

    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=expires_minutes)
    payload = {
        "sub": user_id,
        "email": email,
        "name": full_name or email.split("@")[0],
        "iat": int(now.timestamp()),
        "exp": expire,
    }
    return jwt.encode(payload, _get_jwt_secret(), algorithm=_JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT access token.

    Args:
        token: The raw JWT string from the Authorization header.

    Returns:
        The decoded payload dict (contains sub, email, name, iat, exp).

    Raises:
        JWTError: If the token is invalid, expired, or tampered with.
    """
    return jwt.decode(token, _get_jwt_secret(), algorithms=[_JWT_ALGORITHM])


def is_session_active(issued_at_unix: int) -> bool:
    """Check whether a session is still within the allowed idle window.

    The idle window is controlled by settings.session_idle_limit (default 1800s / 30m).
    This compares the token's 'iat' (issued-at) claim to now, which acts as a
    simple inactivity guard.

    Args:
        issued_at_unix: The 'iat' claim from the decoded JWT (Unix timestamp).

    Returns:
        True if within the idle limit, False if the session has timed out.
    """
    now_unix = int(datetime.now(timezone.utc).timestamp())
    elapsed = now_unix - issued_at_unix
    return elapsed <= settings.session_idle_limit

