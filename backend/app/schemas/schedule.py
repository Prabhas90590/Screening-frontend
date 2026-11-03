"""Screening schedule configuration schemas."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


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

    @field_validator("time_of_day")
    @classmethod
    def validate_time_of_day(cls, v: str) -> str:
        """Validate and clamp time_of_day to valid 24h range (00:00 to 23:59)."""
        if not v or ":" not in v:
            return "08:30"
        try:
            parts = v.strip().split(":")
            h, m = int(parts[0]), int(parts[1])
            # Clamp hours (0-23) and minutes (0-59)
            h_clamped = max(0, min(h, 23))
            m_clamped = max(0, min(m, 59))
            return f"{h_clamped:02d}:{m_clamped:02d}"
        except Exception:
            return "08:30"


class NextRunItemSchema(BaseModel):
    """Detailed item for an upcoming run with schedule context."""
    datetime: str
    schedule_id: str
    frequency: str
    time_of_day: str
    profile_name: str
    label: str
    notification_email: Optional[str] = None
    timezone: str = Field(default="Asia/Kolkata", description="Target execution timezone")


class ScheduleResponse(BaseModel):
    """Response returned upon schedule retrieval or update."""
    success: bool = True
    message: str = "Schedule updated successfully"
    schedule: Optional[ScheduleConfigSchema] = None
    schedules: List[ScheduleConfigSchema] = []
    next_runs: List[str] = []
    next_runs_detailed: List[NextRunItemSchema] = []
    next_runs_by_frequency: Dict[str, List[str]] = Field(default_factory=dict)
