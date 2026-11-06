"""Authentication Service.

Orchestrates corporate login, domain-restricted registration (@zeniusit.com),
6-digit email OTP verification, password reset workflows, and authenticated
password updates.
"""

from datetime import datetime, timedelta, timezone
import logging
import secrets
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    is_session_active,
    verify_password,
)
from app.models.user import UserRecord
from app.repositories.user_repository import user_repository
from app.services.email_service import email_service

logger = logging.getLogger("app.services.auth")

ALLOWED_CORPORATE_DOMAIN = "@zeniusit.com"

# Extracts "Authorization: Bearer <token>" from request headers.
http_bearer = HTTPBearer(auto_error=True)
http_bearer_optional = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# Results & DTOs
# ---------------------------------------------------------------------------

class AuthResult:
    """Value object returned on successful authentication."""

    def __init__(self, user: UserRecord, access_token: str):
        self.user = user
        self.access_token = access_token
        self.token_type = "bearer"
        self.expires_in = 3600  # seconds


class SignupInitiatedResult:
    """Value object returned when registration requires OTP verification."""

    def __init__(self, email: str, message: str):
        self.email = email
        self.message = message
        self.requires_verification = True


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

def authenticate_user(email: str, password: str) -> AuthResult:
    """Verify credentials and issue a JWT access token.

    Rejects:
    - Wrong email or password (401).
    - Unverified corporate email accounts (403 with instruction to verify).
    - Inactive / disabled accounts (403).
    """
    _credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect email or password.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    clean_email = email.lower().strip()
    user = user_repository.get_by_email(clean_email)
    if user is None:
        # Check if user has an unverified pending registration
        pending = user_repository.get_pending_registration(clean_email)
        if pending and verify_password(password, pending.hashed_password):
            logger.warning(f"Login attempt for pending unverified account: '{clean_email}'")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Corporate email is not verified yet. Please enter the 6-digit verification code sent to your inbox to complete registration.",
            )
        logger.warning(f"Login attempt for unknown email: '{clean_email}'")
        raise _credentials_error

    if not verify_password(password, user.hashed_password):
        logger.warning(f"Failed login attempt for '{clean_email}' – wrong password.")
        raise _credentials_error

    if not user.is_active:
        logger.warning(f"Login attempt for disabled account: '{clean_email}'")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled. Please contact your system administrator.",
        )

    # Check email verification status
    if not user.is_verified:
        logger.warning(f"Login attempt for unverified corporate account: '{clean_email}'")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Corporate email is not verified yet. Please enter the 6-digit verification code sent to your inbox.",
        )

    token = create_access_token(
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
    )
    logger.info(f"Successful login for '{clean_email}' (id={user.id})")
    return AuthResult(user=user, access_token=token)


# ---------------------------------------------------------------------------
# Sign-up & Verification
# ---------------------------------------------------------------------------

def register_user(
    email: str,
    password: str,
    full_name: Optional[str] = None,
) -> SignupInitiatedResult:
    """Initiate registration for a corporate @zeniusit.com account.

    Architectural Invariant:
    The user account is NOT stored in the 'users' table until email ownership is
    confirmed via the random 6-digit OTP code. Pending registration data is held
    in 'pending_registrations' with a 15-minute expiration.
    """
    clean_email = email.lower().strip()

    if not clean_email.endswith(ALLOWED_CORPORATE_DOMAIN):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registration is strictly restricted to authorized {ALLOWED_CORPORATE_DOMAIN} corporate email addresses.",
        )

    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long.",
        )

    # Check if already registered in verified users table
    if user_repository.email_exists(clean_email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists. Please sign in.",
        )

    # Cryptographically secure random 6-digit OTP valid for 15 minutes
    code = f"{secrets.randbelow(900000) + 100000}"
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
    hashed = hash_password(password)

    # Store in pending_registrations ONLY (users table is NOT touched)
    saved = user_repository.save_pending_registration(
        email=clean_email,
        hashed_password=hashed,
        full_name=full_name,
        verification_code=code,
        expires_at=expires_at,
    )
    if not saved:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not initiate registration. Please try again later.",
        )

    # Dispatch actual email via live SMTP
    email_service.send_verification_email(clean_email, code, full_name)
    logger.info(
        f"[Auth] Initiated registration for '{clean_email}'. Random OTP {code} generated and dispatched. User NOT stored in 'users' table until verified."
    )

    return SignupInitiatedResult(
        email=clean_email,
        message=f"Verification code sent to {clean_email}. Please check your corporate inbox (and Junk/Spam folder).",
    )


def verify_user_email(email: str, code: str) -> AuthResult:
    """Verify 6-digit email activation code.

    ONLY UPON SUCCESSFUL VERIFICATION is the user permanently persisted
    into the PostgreSQL 'users' table, and an active session JWT established.
    """
    clean_email = email.lower().strip()
    clean_code = code.strip()

    # If user is already verified and stored in users
    existing_user = user_repository.get_by_email(clean_email)
    if existing_user and existing_user.is_verified:
        token = create_access_token(user_id=existing_user.id, email=existing_user.email, full_name=existing_user.full_name)
        return AuthResult(user=existing_user, access_token=token)

    pending = user_repository.get_pending_registration(clean_email)
    if pending is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No pending registration found for this email address. Please register first.",
        )

    if pending.verification_code.strip() != clean_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code. Please check your corporate email or click 'Resend Code'.",
        )

    now = datetime.now(timezone.utc)
    if pending.expires_at < now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code has expired. Please request a new code.",
        )

    # VERIFICATION CONFIRMED: Store user in 'users' table ONLY NOW
    try:
        user = user_repository.create_verified_user(
            email=clean_email,
            hashed_password=pending.hashed_password,
            full_name=pending.full_name,
        )
        user_repository.delete_pending_registration(clean_email)
    except Exception as e:
        logger.error(f"Failed to persist verified user for '{clean_email}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not finalize account creation. Please try again.",
        )

    token = create_access_token(
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
    )
    logger.info(f"[Auth] Corporate email verified! User permanently stored in database: '{clean_email}' (id={user.id})")
    return AuthResult(user=user, access_token=token)


def resend_verification_code(email: str) -> None:
    """Generate and dispatch a fresh random 6-digit activation code via email."""
    clean_email = email.lower().strip()

    if user_repository.email_exists(clean_email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This account is already verified. You can sign in directly.",
        )

    pending = user_repository.get_pending_registration(clean_email)
    if not pending:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No pending registration found for this email address. Please register first.",
        )

    # Fresh random 6-digit OTP
    code = f"{secrets.randbelow(900000) + 100000}"
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
    user_repository.save_pending_registration(
        email=clean_email,
        hashed_password=pending.hashed_password,
        full_name=pending.full_name,
        verification_code=code,
        expires_at=expires_at,
    )
    email_service.send_verification_email(clean_email, code, pending.full_name)
    logger.info(f"[Auth] Resent fresh random verification code {code} for '{clean_email}'.")


# ---------------------------------------------------------------------------
# Password Reset (Forgot Password)
# ---------------------------------------------------------------------------

def request_password_reset(email: str) -> None:
    """Dispatch random 6-digit password reset authorization code to the user's email."""
    clean_email = email.lower().strip()

    if not clean_email.endswith(ALLOWED_CORPORATE_DOMAIN):
        logger.warning(f"Password reset requested for non-corporate email: '{clean_email}'")
        return

    user = user_repository.get_by_email(clean_email)
    if not user or not user.is_active:
        logger.info(f"Password reset requested for non-existent/inactive email: '{clean_email}'")
        return

    code = f"{secrets.randbelow(900000) + 100000}"
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
    user_repository.set_reset_token(clean_email, code, expires_at)
    email_service.send_password_reset_email(clean_email, code, user.full_name)
    logger.info(f"[Auth] Password reset random OTP {code} generated and dispatched for '{clean_email}'.")


def complete_password_reset(email: str, code: str, new_password: str) -> None:
    """Validate 6-digit reset code and update user's password."""
    clean_email = email.lower().strip()
    clean_code = code.strip()

    user = user_repository.get_by_email(clean_email)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset code.",
        )

    success = user_repository.reset_password_with_token(clean_email, clean_code, new_password)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset authorization code. Please request a new one.",
        )

    logger.info(f"[Auth] Password reset successful for user '{clean_email}'.")


def change_authenticated_password(
    user: UserRecord,
    current_password: str,
    new_password: str,
) -> None:
    """Allow an authenticated user to change their password from within the app."""
    if not verify_password(current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )

    if current_password == new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from your current password.",
        )

    success = user_repository.update_password(user.id, new_password)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update password. Please try again.",
        )

    logger.info(f"Password changed successfully by user '{user.email}' (id={user.id}).")


# ---------------------------------------------------------------------------
# Current-user dependency (used by all protected routes)
# ---------------------------------------------------------------------------

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(http_bearer),
) -> UserRecord:
    """FastAPI dependency that validates the JWT and returns the active user."""
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


def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer_optional),
) -> Optional[UserRecord]:
    """Like get_current_user but returns None instead of raising 401."""
    if not credentials or not credentials.credentials:
        return None
    try:
        return get_current_user(credentials)
    except HTTPException:
        return None
