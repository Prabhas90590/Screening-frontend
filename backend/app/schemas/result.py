"""Results view query and detail drawer response schemas."""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field

from app.schemas.screening import FunnelStageCounts, ScreenedSecurityResult


class ResultsViewResponse(BaseModel):
    """Payload returned when user selects a tab in the results table."""
    run_id: str
    view: Literal["top20", "rank_near_misses", "rule_near_misses", "my_holdings", "all_screened"]
    funnel: FunnelStageCounts
    total_count: int
    items: List[ScreenedSecurityResult]
