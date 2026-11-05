"""Authentication API Routes (Phase 3 & Phase 4).

Exposes REST endpoints for:
- POST /api/auth/signup  (Self-serve account creation with password validation)
- POST /api/auth/login   (Credentials verification with sliding-window brute-force rate limiting)
- GET  /api/auth/me      (Active session identity & 30-minute idle check)
- POST /api/auth/ping    (Heartbeat ping for frontend activity listener to prevent false idle logouts)
- POST /api/auth/logout  (Graceful session close)
"""

from datetime import datetime, timezone
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.core.rate_limiter import login_rate_limiter
from app.models.user import UserRecord
from app.repositories.user_repository import user_repository
from app.schemas.auth import (
    AuthTokenResponse,
    LogoutResponse,
    SessionPingResponse,
    UserLoginRequest,
    UserProfileResponse,
    UserSignupRequest,
)
from app.services.auth_service import (
    authenticate_user,
    get_current_user,
    register_user,
)

logger = logging.getLogger("app.api.routes.auth")

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


def _extract_client_ip(request: Request) -> str:
    """Extract client IP address, respecting X-Forwarded-For if behind a proxy."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


@router.post(
    "/signup",
    response_model=AuthTokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new analyst account",
)
def signup(request: UserSignupRequest):
    """Open self-sign-up for analysts.

    Validates password strength (min 8 chars, letters and digits),
    securely stores bcrypt hash, and returns a signed JWT access token.
    """
    try:
        result = register_user(
            email=request.email,
            password=request.password,
            full_name=request.full_name,
        )
        return AuthTokenResponse(
            access_token=result.access_token,
            token_type=result.token_type,
            expires_in=result.expires_in,
            user=UserProfileResponse.model_validate(result.user),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in signup for '{request.email}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating your account.",
        )


@router.post(
    "/login",
    response_model=AuthTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate with email and password",
)
def login(request: UserLoginRequest, http_request: Request):
    """Verify email and password against the database.

    Security guards (Phase 4):
    - Rate-limited to 5 failed attempts per minute per IP to block brute-force attacks.
    - Generic error message (anti-user-enumeration).
    - Failure counter immediately resets on successful login.
    """
    client_ip = _extract_client_ip(http_request)

    # 1. Rate-limit check
    is_blocked, seconds_remaining = login_rate_limiter.is_blocked(client_ip)
    if is_blocked:
        logger.warning(
            f"[RateLimiter] Blocked login attempt from '{client_ip}'. "
            f"Wait {seconds_remaining}s remaining."
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed login attempts. Please wait {seconds_remaining} seconds before trying again.",
            headers={"Retry-After": str(seconds_remaining)},
        )

    # 2. Authentication attempt
    try:
        result = authenticate_user(
            email=request.email,
            password=request.password,
        )
        # Login succeeded: clear any failure counter for this IP
        login_rate_limiter.reset(client_ip)
        return AuthTokenResponse(
            access_token=result.access_token,
            token_type=result.token_type,
            expires_in=result.expires_in,
            user=UserProfileResponse.model_validate(result.user),
        )
    except HTTPException as e:
        # Record failure on 401 Unauthorized
        if e.status_code == status.HTTP_401_UNAUTHORIZED:
            login_rate_limiter.record_failure(client_ip)
        raise
    except Exception as e:
        logger.error(f"Unexpected error in login for '{request.email}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during login.",
        )


@router.get(
    "/me",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user profile and validate active session",
)
def get_me(current_user: UserRecord = Depends(get_current_user)):
    """Fetch the currently authenticated user's profile.

    Validates:
    1. Signature of the JWT in the Authorization header.
    2. Idle inactivity window (30 minutes).
    3. User exists and is active in the database.
    """
    return UserProfileResponse.model_validate(current_user)


@router.post(
    "/ping",
    response_model=SessionPingResponse,
    status_code=status.HTTP_200_OK,
    summary="Keep-alive heartbeat for active frontend sessions",
)
def session_ping(current_user: UserRecord = Depends(get_current_user)):
    """Lightweight session heartbeat called by the frontend activity listener (Phase 5).

    Updates the user's last-seen timestamp in the database to prevent false idle logouts
    while an analyst is reading data or clicking client-side controls.
    """
    user_repository.update_last_seen(current_user.id)
    return SessionPingResponse(
        status="active",
        user_id=current_user.id,
        email=current_user.email,
        timestamp=datetime.now(timezone.utc),
    )


@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Log out of the current session",
)
def logout(current_user: UserRecord = Depends(get_current_user)):
    """Acknowledge session termination.

    Client should discard its stored access token upon receiving this response.
    """
    logger.info(f"User logged out: {current_user.email} (id={current_user.id})")
    return LogoutResponse(message="Logged out successfully.")
