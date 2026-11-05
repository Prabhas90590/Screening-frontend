"""Schedule management and triggering API routes (Phase 17)."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.logging import DiagnosticLogger
from app.models.user import UserRecord
from app.schemas.schedule import ScheduleConfigSchema, ScheduleResponse
from app.services.auth_service import get_optional_user
from app.services.scheduler_service import scheduler_service

logger = DiagnosticLogger("schedules_api")
router = APIRouter(prefix="/api/schedules", tags=["schedules"])


@router.get("", response_model=ScheduleResponse)
def get_schedules(cadence: Optional[str] = Query(default=None)):
    """Retrieve saved schedules (optionally filtered by cadence: daily, weekly, monthly, custom)."""
    try:
        schedules = scheduler_service.list_schedules(cadence=cadence)
        all_schedules = scheduler_service.list_schedules()
        active = schedules[0] if schedules else (all_schedules[0] if all_schedules else None)
        flat_runs, detailed_runs, by_freq = scheduler_service.calculate_all_next_runs()
        return ScheduleResponse(
            success=True,
            message="Schedule configurations retrieved.",
            schedule=active,
            schedules=schedules,
            next_runs=flat_runs,
            next_runs_detailed=detailed_runs,
            next_runs_by_frequency=by_freq,
        )
    except Exception as e:
        logger.error(f"Error fetching schedules: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch schedules: {str(e)}",
        )


@router.post("", response_model=ScheduleResponse)
def save_schedule(
    payload: ScheduleConfigSchema,
    current_user: Optional[UserRecord] = Depends(get_optional_user),
):
    """Save or update screening schedule configuration."""
    if current_user and current_user.email:
        payload.owner_email = current_user.email
    try:
        updated = scheduler_service.save_schedule(payload)
        schedules = scheduler_service.list_schedules()
        flat_runs, detailed_runs, by_freq = scheduler_service.calculate_all_next_runs()
        return ScheduleResponse(
            success=True,
            message=f"Schedule '{updated.schedule_id}' saved successfully.",
            schedule=updated,
            schedules=schedules,
            next_runs=flat_runs,
            next_runs_detailed=detailed_runs,
            next_runs_by_frequency=by_freq,
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


@router.delete("/{schedule_id}", response_model=ScheduleResponse)
def delete_schedule(schedule_id: str):
    """Delete a saved screening schedule."""
    try:
        deleted = scheduler_service.delete_schedule(schedule_id)
        if not deleted:
            logger.info(f"Schedule '{schedule_id}' not found in database or already deleted.")
        schedules = scheduler_service.list_schedules()
        active = schedules[0] if schedules else None
        flat_runs, detailed_runs, by_freq = scheduler_service.calculate_all_next_runs()
        return ScheduleResponse(
            success=True,
            message=f"Schedule '{schedule_id}' deleted successfully." if deleted else f"Schedule '{schedule_id}' already removed.",
            schedule=active,
            schedules=schedules,
            next_runs=flat_runs,
            next_runs_detailed=detailed_runs,
            next_runs_by_frequency=by_freq,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting schedule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete schedule: {str(e)}",
        )



@router.delete("/{schedule_id}/days/{day}", response_model=ScheduleResponse)
def remove_schedule_day(schedule_id: str, day: str):
    """Remove a single specific day (e.g. 'wed') from a daily/weekly schedule without deleting the whole schedule."""
    try:
        updated = scheduler_service.remove_day_from_schedule(schedule_id, day)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule '{schedule_id}' not found.",
            )
        schedules = scheduler_service.list_schedules()
        flat_runs, detailed_runs, by_freq = scheduler_service.calculate_all_next_runs()
        return ScheduleResponse(
            success=True,
            message=f"Day '{day.capitalize()}' removed from schedule '{schedule_id}'.",
            schedule=updated,
            schedules=schedules,
            next_runs=flat_runs,
            next_runs_detailed=detailed_runs,
            next_runs_by_frequency=by_freq,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing day '{day}' from schedule '{schedule_id}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove day: {str(e)}",
        )


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
