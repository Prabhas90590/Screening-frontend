"""Raw response database entity model.

Represents an exact, unchanged external vendor API response stored in PostgreSQL.
"""

from datetime import datetime
from typing import Any, Dict, Optional, Union
from pydantic import BaseModel, Field


class RawResponse(BaseModel):
    """Database model for the raw_responses table."""
    id: str = Field(..., description="Unique raw response identifier, e.g. 'raw-20261022-abcd1234'")
    run_id: Optional[str] = Field(None, description="Screening run ID associated with this fetch")
    provider: str = Field(..., description="Data provider name: 'eodhd', 'lseg', or 'mock'")
    endpoint: str = Field(..., description="API endpoint or operation invoked")
    request_params: Dict[str, Any] = Field(default_factory=dict, description="Sanitized query/path parameters")
    response_body: Union[Dict[str, Any], list, str] = Field(..., description="100% original, unedited vendor JSON payload")
    fingerprint: str = Field(..., description="SHA-256 cryptographic hash of response_body")
    status_code: int = Field(default=200, description="HTTP status code from the provider")
    latency_ms: float = Field(default=0.0, description="Network roundtrip latency in milliseconds")
    received_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when response arrived")
    is_success: bool = Field(default=True, description="Whether the API request was successful")
    error_message: Optional[str] = Field(None, description="Sanitized error description if failed")
