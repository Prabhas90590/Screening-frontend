"""Authentication API Routes.

Exposes REST endpoints for:
- POST /api/auth/signup               (Initiate registration for corporate @zeniusit.com with 6-digit OTP)
- POST /api/auth/verify-email          (Confirm email ownership via 6-digit OTP code)
- POST /api/auth/resend-verification   (Dispatch fresh verification OTP code)
- POST /api/auth/login                (Credentials verification with brute-force rate limiter)
- POST /api/auth/forgot-password      (Dispatch 6-digit password reset authorization code)
- POST /api/auth/reset-password       (Set new password via verified reset code)
- POST /api/auth/change-password      (Authenticated in-app password update)
- PUT  /api/auth/profile              (Authenticated profile name update)
- GET  /api/auth/me                   (Active session identity & 30-minute idle check)
- POST /api/auth/ping                 (Heartbeat keep-alive ping for active session)
- POST /api/auth/logout               (Graceful session close)
"""

from datetime import datetime, timezone
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.core.rate_limiter import login_rate_limiter
from app.models.user import UserRecord
from app.repositories.user_repository import user_repository
from app.schemas.auth import (
    AuthTokenResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    GenericMessageResponse,
    LogoutResponse,
    ResendVerificationRequest,
    ResetPasswordRequest,
    SessionPingResponse,
    SignupInitResponse,
    UpdateProfileRequest,
    UserLoginRequest,
    UserProfileResponse,
    UserSignupRequest,
    VerifyEmailRequest,
)
from app.services.auth_service import (
    authenticate_user,
    change_authenticated_password,
    complete_password_reset,
    get_current_user,
    register_user,
    request_password_reset,
    resend_verification_code,
    verify_user_email,
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
    response_model=SignupInitResponse,
    status_code=status.HTTP_200_OK,
    summary="Register a new analyst account (Corporate domain only)",
)
def signup(request: UserSignupRequest):
    """Enforces corporate @zeniusit.com domain.

    Dispatches a 6-digit activation OTP to the user's corporate email.
    The account remains unverified until the OTP is provided to /verify-email.
    """
    try:
        result = register_user(
            email=request.email,
            password=request.password,
            full_name=request.full_name,
        )
        return SignupInitResponse(
            message=result.message,
            email=result.email,
            requires_verification=True,
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
    "/verify-email",
    response_model=AuthTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify corporate email ownership using 6-digit code",
)
def verify_email(request: VerifyEmailRequest):
    """Confirm email ownership and activate account.

    On successful verification, marks account as verified and issues a JWT session token.
    """
    try:
        result = verify_user_email(email=request.email, code=request.code)
        return AuthTokenResponse(
            access_token=result.access_token,
            token_type=result.token_type,
            expires_in=result.expires_in,
            user=UserProfileResponse.model_validate(result.user),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying email for '{request.email}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while verifying your email.",
        )


@router.post(
    "/resend-verification",
    response_model=GenericMessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Resend a 6-digit activation code",
)
def resend_verification(request: ResendVerificationRequest):
    """Generate and dispatch a fresh 6-digit activation code to corporate inbox."""
    try:
        resend_verification_code(email=request.email)
        return GenericMessageResponse(
            message="A fresh verification code has been dispatched to your corporate inbox."
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resending verification code to '{request.email}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not dispatch verification code. Please try again later.",
        )


@router.post(
    "/login",
    response_model=AuthTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate with email and password",
)
def login(request: UserLoginRequest, http_request: Request):
    """Verify email and password against the database.

    Enforces:
    - Brute-force rate limiting per client IP.
    - Verified corporate email check (403 with instruction if unverified).
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
        login_rate_limiter.reset(client_ip)
        return AuthTokenResponse(
            access_token=result.access_token,
            token_type=result.token_type,
            expires_in=result.expires_in,
            user=UserProfileResponse.model_validate(result.user),
        )
    except HTTPException as e:
        if e.status_code == status.HTTP_401_UNAUTHORIZED:
            login_rate_limiter.record_failure(client_ip)
        raise
    except Exception as e:
        logger.error(f"Unexpected error in login for '{request.email}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during login.",
        )


@router.post(
    "/forgot-password",
    response_model=GenericMessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Request a 6-digit password reset authorization code",
)
def forgot_password(request: ForgotPasswordRequest):
    """Dispatches a password reset authorization code via email.

    Uses generic message to prevent user enumeration.
    """
    try:
        request_password_reset(email=request.email)
        return GenericMessageResponse(
            message="If an account exists with this email address, a password reset code has been dispatched to your corporate inbox."
        )
    except Exception as e:
        logger.error(f"Unexpected error in forgot_password for '{request.email}': {e}")
        return GenericMessageResponse(
            message="If an account exists with this email address, a password reset code has been dispatched to your corporate inbox."
        )


@router.post(
    "/reset-password",
    response_model=GenericMessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Set a new password using 6-digit authorization code",
)
def reset_password(request: ResetPasswordRequest):
    """Validates 6-digit code and securely hashes the new password."""
    try:
        complete_password_reset(
            email=request.email,
            code=request.code,
            new_password=request.new_password,
        )
        return GenericMessageResponse(
            message="Password has been reset successfully. You may now sign in with your new password."
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in reset_password for '{request.email}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while resetting your password.",
        )


@router.post(
    "/change-password",
    response_model=GenericMessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Change password from an active session",
)
def change_password(
    request: ChangePasswordRequest,
    current_user: UserRecord = Depends(get_current_user),
):
    """Authenticated endpoint allowing analysts to update their password from within the app."""
    try:
        change_authenticated_password(
            user=current_user,
            current_password=request.current_password,
            new_password=request.new_password,
        )
        return GenericMessageResponse(message="Password updated successfully.")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error changing password for user {current_user.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update password.",
        )


@router.put(
    "/profile",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Update user display name",
)
def update_profile(
    request: UpdateProfileRequest,
    current_user: UserRecord = Depends(get_current_user),
):
    """Authenticated endpoint to update analyst display name."""
    updated = user_repository.update_profile(current_user.id, request.full_name)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile.",
        )
    return UserProfileResponse.model_validate(updated)


@router.get(
    "/me",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user profile and validate active session",
)
def get_me(current_user: UserRecord = Depends(get_current_user)):
    """Fetch the currently authenticated user's profile."""
    return UserProfileResponse.model_validate(current_user)


@router.post(
    "/ping",
    response_model=SessionPingResponse,
    status_code=status.HTTP_200_OK,
    summary="Keep-alive heartbeat for active frontend sessions",
)
def session_ping(current_user: UserRecord = Depends(get_current_user)):
    """Lightweight session heartbeat called by the frontend activity listener."""
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
    """Acknowledge session termination."""
    logger.info(f"User logged out: {current_user.email} (id={current_user.id})")
    return LogoutResponse(message="Logged out successfully.")
