"""Decision and portfolio holding request/response schemas."""

from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class DecisionUpdateRequest(BaseModel):
    """Payload to record or change an analyst Keep/Drop decision."""
    canonical_company_id: str
    company_name: Optional[str] = None
    profile_name: Optional[str] = None
    decision: Literal["keep", "drop"]
    decision_reason: Optional[str] = None
    decision_note: Optional[str] = None
    run_id: Optional[str] = None
    decided_by: Optional[str] = "Analyst"


class DecisionBulkSyncRequest(BaseModel):
    """Payload to bulk-sync all analyst Keep/Drop decisions upon Excel export."""
    profile_name: Optional[str] = None
    run_id: Optional[str] = None
    decisions: List[DecisionUpdateRequest] = Field(default_factory=list)


class DecisionResponse(BaseModel):
    """Decision record returned to the frontend."""
    decision_id: str
    canonical_company_id: str
    company_name: Optional[str] = None
    profile_name: Optional[str] = None
    decision: Literal["keep", "drop"]
    decision_reason: Optional[str] = None
    decision_note: Optional[str] = None
    run_id: Optional[str] = None
    decided_by: str = "Analyst"
    updated_at: datetime
