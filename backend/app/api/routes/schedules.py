"""Schedule management and triggering API routes (Phase 17)."""

from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException, status

from app.core.logging import DiagnosticLogger
from app.schemas.schedule import ScheduleConfigSchema, ScheduleResponse
from app.services.scheduler_service import scheduler_service

logger = DiagnosticLogger("schedules_api")
router = APIRouter(prefix="/api/schedules", tags=["schedules"])


@router.get("", response_model=ScheduleResponse)
def get_schedule(schedule_id: str = "default-schedule"):
    """Retrieve the current schedule configuration and upcoming execution timestamps."""
    try:
        config = scheduler_service.get_schedule(schedule_id)
        next_dts = scheduler_service.calculate_next_runs(config, count=3)
        formatted_runs = [d.isoformat() for d in next_dts]
        return ScheduleResponse(
            success=True,
            message="Schedule configuration retrieved.",
            schedule=config,
            next_runs=formatted_runs,
        )
    except Exception as e:
        logger.error(f"Error fetching schedule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch schedule: {str(e)}",
        )


@router.post("", response_model=ScheduleResponse)
def save_schedule(payload: ScheduleConfigSchema):
    """Save or update screening schedule configuration."""
    try:
        updated = scheduler_service.save_schedule(payload)
        next_dts = scheduler_service.calculate_next_runs(updated, count=3)
        formatted_runs = [d.isoformat() for d in next_dts]
        return ScheduleResponse(
            success=True,
            message="Schedule configuration saved successfully.",
            schedule=updated,
            next_runs=formatted_runs,
        )
    except Exception as e:
        logger.error(f"Error saving schedule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save schedule: {str(e)}",
        )


@router.put("/{schedule_id}", response_model=ScheduleResponse)
def update_schedule(schedule_id: str, payload: ScheduleConfigSchema):
    """Update a specific schedule configuration."""
    payload.schedule_id = schedule_id
    return save_schedule(payload)


@router.post("/run-now")
async def trigger_run_now(schedule_id: str = "default-schedule"):
    """Immediately trigger a screening run using the saved schedule parameters."""
    try:
        result = await scheduler_service.execute_scheduled_run(schedule_id)
        return {
            "success": True,
            "message": f"Screening run {result.run_id} executed successfully.",
            "run_id": result.run_id,
            "profile_name": result.profile_name,
            "securities_count": len(result.results),
        }
    except Exception as e:
        logger.error(f"Error executing run now: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute screening run: {str(e)}",
        )
