"""Service for capturing and storing immutable raw external API responses.

Generates SHA-256 cryptographic hashes for tamper-proof data verification,
sanitizes sensitive query parameters, and persists payloads to PostgreSQL.
"""

from datetime import datetime
import hashlib
import json
from typing import Any, Dict, Optional, Union
from uuid import uuid4

from app.core.logging import DiagnosticLogger
from app.models.raw_response import RawResponse
from app.repositories.raw_response_repository import raw_response_repository

logger = DiagnosticLogger("raw_store")


def _sanitize_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """Scrub sensitive secrets from query parameters before persisting."""
    sanitized: Dict[str, Any] = {}
    sensitive_keys = {"api_token", "api_key", "token", "password", "secret"}
    for key, val in params.items():
        if key.lower() in sensitive_keys:
            sanitized[key] = "***REDACTED***"
        else:
            sanitized[key] = val
    return sanitized


def compute_fingerprint(response_body: Union[Dict[str, Any], list, str]) -> str:
    """Generate deterministic SHA-256 hash of a response payload."""
    if isinstance(response_body, (dict, list)):
        payload_str = json.dumps(response_body, sort_keys=True)
    else:
        payload_str = str(response_body)
    return hashlib.sha256(payload_str.encode("utf-8")).hexdigest()


class RawResponseStore:
    """Service to capture and store vendor API responses."""

    def __init__(self, repository=raw_response_repository):
        self.repository = repository

    def store_response(
        self,
        provider: str,
        endpoint: str,
        response_body: Union[Dict[str, Any], list, str],
        request_params: Optional[Dict[str, Any]] = None,
        run_id: Optional[str] = None,
        status_code: int = 200,
        latency_ms: float = 0.0,
        is_success: bool = True,
        error_message: Optional[str] = None,
    ) -> RawResponse:
        """Capture and persist an external vendor API response into PostgreSQL."""
        sanitized_params = _sanitize_params(request_params or {})
        fingerprint = compute_fingerprint(response_body)
        timestamp = datetime.utcnow()
        response_id = f"raw-{timestamp.strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:8]}"

        raw_model = RawResponse(
            id=response_id,
            run_id=run_id,
            provider=provider.lower(),
            endpoint=endpoint,
            request_params=sanitized_params,
            response_body=response_body,
            fingerprint=fingerprint,
            status_code=status_code,
            latency_ms=round(latency_ms, 2),
            received_at=timestamp,
            is_success=is_success,
            error_message=error_message,
        )

        self.repository.save(raw_model)

        logger.provider_info(
            provider,
            f"Stored raw response '{response_id}' for endpoint '{endpoint}' "
            f"(status={status_code}, latency={latency_ms:.1f}ms, hash={fingerprint[:8]}...)"
        )

        return raw_model

    def find_cached_response(self, fingerprint: str) -> Optional[RawResponse]:
        """Check if an identical response is already stored in the database."""
        return self.repository.get_by_fingerprint(fingerprint)


# Global store instance
raw_response_store = RawResponseStore()
