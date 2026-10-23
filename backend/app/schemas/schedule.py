"""Screening schedule configuration schemas."""

from typing import Optional
from pydantic import BaseModel, Field


class ScheduleConfigSchema(BaseModel):
    """Configuration for automated background screening runs."""
    schedule_id: str = "default-schedule"
    frequency: str = Field(default="Weekly", description="Daily, Weekly, Monthly")
    day_of_week: str = "Monday"
    time_of_day: str = "09:00"
    is_enabled: bool = False
    auto_run: bool = True
    notify_on_complete: bool = True
