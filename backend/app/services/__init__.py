"""Application business logic services package."""

from app.services.fx_service import FXService, fx_service
from app.services.auth_service import (  # Phase 2 – authentication
    authenticate_user,
    register_user,
    get_current_user,
    get_optional_user,
)

__all__ = [
    "FXService",
    "fx_service",
    "authenticate_user",   # Phase 2 – authentication
    "register_user",       # Phase 2 – authentication
    "get_current_user",    # Phase 2 – authentication
    "get_optional_user",   # Phase 2 – authentication
]
