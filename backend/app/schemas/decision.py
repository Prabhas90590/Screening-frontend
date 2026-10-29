"""Decision and portfolio holding request/response schemas."""

from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field


class DecisionUpdateRequest(BaseModel):
    """Payload to record or change an analyst Keep/Drop decision."""
    canonical_company_id: str
    decision: Literal["keep", "drop"]
    decision_reason: Optional[str] = None
    decision_note: Optional[str] = None
    run_id: Optional[str] = None
    decided_by: Optional[str] = "Analyst"


class DecisionResponse(BaseModel):
    """Decision record returned to the frontend."""
    decision_id: str
    canonical_company_id: str
    decision: Literal["keep", "drop"]
    decision_reason: Optional[str] = None
    decision_note: Optional[str] = None
    run_id: Optional[str] = None
    decided_by: str = "Analyst"
    updated_at: datetime
