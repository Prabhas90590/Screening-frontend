"""Screening schedule configuration schemas."""

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class ScheduleConfigSchema(BaseModel):
    """Configuration for automated background screening runs."""
    schedule_id: str = "default-schedule"
    profile_id: Optional[str] = None
    profile_name: Optional[str] = "Default Strategy"
    frequency: str = Field(default="Daily", description="Daily, Weekly, Monthly, Custom")
    daily_type: str = Field(default="trading_days", description="trading_days (Mon-Fri) or all_days (7 days)")
    active_days: List[str] = Field(default_factory=lambda: ["mon", "tue", "wed", "thu", "fri"])
    day_of_month: int = Field(default=1, ge=1, le=31)
    time_of_day: str = Field(default="08:30", description="HH:MM format in 24-hr")
    timezone: str = Field(default="Asia/Kolkata", description="Target execution timezone")
    cron_expression: str = Field(default="0 9 * * 1-5")
    is_enabled: bool = True
    auto_run: bool = True
    refresh_data_first: bool = True
    skip_holidays: bool = True
    notify_on_complete: bool = True
    notification_email: Optional[str] = None
    notify_triggers: Dict[str, bool] = Field(
        default_factory=lambda: {
            "runCompletes": True,
            "runFails": True,
            "dataBlockers": True,
        }
    )
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ScheduleResponse(BaseModel):
    """Response returned upon schedule retrieval or update."""
    success: bool = True
    message: str = "Schedule updated successfully"
    schedule: ScheduleConfigSchema
    next_runs: List[str] = []
