"""Authentication Service (Phase 2 – user-side login).

Orchestrates login, sign-up, and current-user resolution.
Ties together the security utilities (core/security.py) and the
user repository (repositories/user_repository.py).

No endpoint logic lives here — that belongs in the API layer (Phase 3).
"""

import logging
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

from app.core.security import (
    create_access_token,
    decode_access_token,
    is_session_active,
    verify_password,
)
from app.models.user import UserRecord
from app.repositories.user_repository import user_repository

logger = logging.getLogger("app.services.auth")

# ---------------------------------------------------------------------------
# HTTP Bearer token extraction helper
# ---------------------------------------------------------------------------
# Extracts "Authorization: Bearer <token>" from request headers.
# In Swagger UI, this shows a simple single "Value" box to paste your JWT token.
http_bearer = HTTPBearer(auto_error=True)
http_bearer_optional = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

class LoginResult:
    """Value object returned by authenticate_user()."""

    def __init__(self, user: UserRecord, access_token: str):
        self.user = user
        self.access_token = access_token
        self.token_type = "bearer"
        self.expires_in = 3600  # seconds (matches the 60-min token lifetime)


def authenticate_user(email: str, password: str) -> LoginResult:
    """Verify credentials and issue a JWT access token.

    Steps:
        1. Look up the user by email.
        2. Verify the supplied password against the bcrypt hash.
        3. Check the account is active.
        4. Create and return a signed JWT.

    Args:
        email:    Email address submitted on the login form.
        password: Plain-text password submitted on the login form.

    Returns:
        A LoginResult containing the user record and access token.

    Raises:
        HTTPException 401: If credentials are wrong or account is inactive.
    """
    _credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect email or password.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    user = user_repository.get_by_email(email)
    if user is None:
        logger.warning(f"Login attempt for unknown email: '{email}'")
        raise _credentials_error

    if not verify_password(password, user.hashed_password):
        logger.warning(f"Failed login attempt for '{email}' – wrong password.")
        raise _credentials_error

    if not user.is_active:
        logger.warning(f"Login attempt for disabled account: '{email}'")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled. Contact your administrator.",
        )

    token = create_access_token(
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
    )
    logger.info(f"Successful login for '{email}' (id={user.id})")
    return LoginResult(user=user, access_token=token)


# ---------------------------------------------------------------------------
# Sign-up
# ---------------------------------------------------------------------------

class SignupResult:
    """Value object returned by register_user()."""

    def __init__(self, user: UserRecord, access_token: str):
        self.user = user
        self.access_token = access_token
        self.token_type = "bearer"
        self.expires_in = 3600


def register_user(
    email: str,
    password: str,
    full_name: Optional[str] = None,
) -> SignupResult:
    """Create a new analyst account and issue a JWT access token.

    Open self-registration: any visitor can call this endpoint.
    Passwords must be at least 8 characters (enforced here, not just in the schema).

    Args:
        email:     Email address for the new account.
        password:  Plain-text password chosen by the user.
        full_name: Optional display name.

    Returns:
        A SignupResult with the new UserRecord and access token.

    Raises:
        HTTPException 400: If the email is already registered or the password is too short.
        HTTPException 500: If the database insert fails.
    """
    # Basic password policy
    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long.",
        )

    try:
        user = user_repository.create_user(
            email=email,
            plain_password=password,
            full_name=full_name,
        )
    except ValueError as e:
        # Email already registered
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not create account: {e}",
        )

    token = create_access_token(
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
    )
    logger.info(f"New account registered: '{email}' (id={user.id})")
    return SignupResult(user=user, access_token=token)


# ---------------------------------------------------------------------------
# Current-user dependency (used by all protected routes)
# ---------------------------------------------------------------------------

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(http_bearer),
) -> UserRecord:
    """FastAPI dependency that validates the JWT and returns the active user.

    Usage in a route:
        @router.get("/protected")
        def protected(current_user: UserRecord = Depends(get_current_user)):
            ...

    Validation steps:
        1. Decode and verify the JWT signature.
        2. Check the session idle window (SESSION_IDLE_LIMIT env var, default 30 min).
        3. Fetch the user from the database to confirm they still exist and are active.

    Raises:
        HTTPException 401: Token invalid, expired, or session timed out.
        HTTPException 403: Account disabled.
    """
    _auth_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except JWTError as e:
        logger.debug(f"JWT decode failed: {e}")
        raise _auth_error

    user_id: Optional[str] = payload.get("sub")
    issued_at: Optional[int] = payload.get("iat")

    if not user_id:
        raise _auth_error

    # Idle-session check
    if issued_at is not None and not is_session_active(issued_at):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired due to inactivity. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = user_repository.get_by_id(user_id)
    if user is None:
        raise _auth_error

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled.",
        )

    # Bump last-seen activity timestamp
    user_repository.update_last_seen(user.id)

    return user


# ---------------------------------------------------------------------------
# Optional dependency — returns None for unauthenticated visitors
# ---------------------------------------------------------------------------

def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer_optional),
) -> Optional[UserRecord]:
    """Like get_current_user but returns None instead of raising 401.

    Useful for routes that work for both authenticated and anonymous visitors.
    """
    if not credentials or not credentials.credentials:
        return None
    try:
        return get_current_user(credentials)
    except HTTPException:
        return None

