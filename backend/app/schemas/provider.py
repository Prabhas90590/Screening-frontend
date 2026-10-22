"""Provider interaction and raw response audit schemas.

Captures vendor metadata, response fingerprints, latency, and status.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class RawResponseAudit(BaseModel):
    """Metadata recorded for every vendor API call for audit and reproducibility."""
    provider_name: str = Field(..., description="Provider name, e.g. 'eodhd', 'lseg', 'mock'")
    endpoint: str = Field(..., description="API endpoint or function invoked")
    request_params: Dict[str, Any] = Field(default_factory=dict, description="Sanitized query/path parameters")
    status_code: int = Field(default=200, description="HTTP status code or internal execution status")
    latency_ms: float = Field(default=0.0, description="Roundtrip call duration in milliseconds")
    fingerprint: str = Field(..., description="SHA-256 hash fingerprint of original response body")
    received_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp response was received")
    is_success: bool = Field(default=True, description="Whether call completed successfully")
    error_message: Optional[str] = Field(None, description="Sanitized error description if failed")

