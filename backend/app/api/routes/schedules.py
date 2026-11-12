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
def get_schedules(
    cadence: Optional[str] = Query(default=None),
    current_user: Optional[UserRecord] = Depends(get_optional_user),
):
    """Retrieve saved schedules for the current user (optionally filtered by cadence)."""
    if not current_user:
        return ScheduleResponse(
            success=True,
            message="No authenticated session.",
            schedule=None,
            schedules=[],
            next_runs=[],
            next_runs_detailed=[],
            next_runs_by_frequency={"Daily": [], "Weekly": [], "Monthly": [], "Custom": []},
        )
    try:
        schedules = scheduler_service.list_schedules(
            cadence=cadence,
            owner_email=current_user.email,
            user_id=current_user.id,
        )
        all_schedules = scheduler_service.list_schedules(
            owner_email=current_user.email,
            user_id=current_user.id,
        )
        active = schedules[0] if schedules else (all_schedules[0] if all_schedules else None)
        flat_runs, detailed_runs, by_freq = scheduler_service.calculate_all_next_runs(
            owner_email=current_user.email,
            user_id=current_user.id,
        )
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
    """Save or update screening schedule configuration for the authenticated user."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to save schedules.",
        )
    payload.owner_email = current_user.email
    payload.user_id = current_user.id
    if payload.profile_id:
        from app.repositories.rule_repository import rule_repository
        owned_prof = rule_repository.get_version_by_id(
            payload.profile_id,
            owner_email=current_user.email,
            user_id=current_user.id,
        )
        if not owned_prof:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Profile '{payload.profile_id}' not found for current user.",
            )
    try:
        updated = scheduler_service.save_schedule(payload)
        schedules = scheduler_service.list_schedules(
            owner_email=current_user.email,
            user_id=current_user.id,
        )
        flat_runs, detailed_runs, by_freq = scheduler_service.calculate_all_next_runs(
            owner_email=current_user.email,
            user_id=current_user.id,
        )
        return ScheduleResponse(
            success=True,
            message=f"Schedule '{updated.schedule_id}' saved successfully.",
            schedule=updated,
            schedules=schedules,
            next_runs=flat_runs,
            next_runs_detailed=detailed_runs,
            next_runs_by_frequency=by_freq,
        )
    except PermissionError as pe:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(pe),
        )
    except Exception as e:
        logger.error(f"Error saving schedule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save schedule: {str(e)}",
        )


@router.put("/{schedule_id}", response_model=ScheduleResponse)
def update_schedule(
    schedule_id: str,
    payload: ScheduleConfigSchema,
    current_user: Optional[UserRecord] = Depends(get_optional_user),
):
    """Update a specific schedule configuration."""
    payload.schedule_id = schedule_id
    return save_schedule(payload, current_user=current_user)


@router.delete("/{schedule_id}", response_model=ScheduleResponse)
def delete_schedule(
    schedule_id: str,
    current_user: Optional[UserRecord] = Depends(get_optional_user),
):
    """Delete a saved screening schedule owned by the authenticated user."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to delete schedules.",
        )
    try:
        deleted = scheduler_service.delete_schedule(
            schedule_id,
            owner_email=current_user.email,
            user_id=current_user.id,
        )
        if not deleted:
            logger.info(f"Schedule '{schedule_id}' not found for {current_user.email} or already deleted.")
        schedules = scheduler_service.list_schedules(
            owner_email=current_user.email,
            user_id=current_user.id,
        )
        active = schedules[0] if schedules else None
        flat_runs, detailed_runs, by_freq = scheduler_service.calculate_all_next_runs(
            owner_email=current_user.email,
            user_id=current_user.id,
        )
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
def remove_schedule_day(
    schedule_id: str,
    day: str,
    current_user: Optional[UserRecord] = Depends(get_optional_user),
):
    """Remove a single specific day (e.g. 'wed') from a schedule owned by caller."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to modify schedules.",
        )
    try:
        updated = scheduler_service.remove_day_from_schedule(
            schedule_id,
            day,
            owner_email=current_user.email,
            user_id=current_user.id,
        )
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule '{schedule_id}' not found.",
            )
        schedules = scheduler_service.list_schedules(
            owner_email=current_user.email,
            user_id=current_user.id,
        )
        flat_runs, detailed_runs, by_freq = scheduler_service.calculate_all_next_runs(
            owner_email=current_user.email,
            user_id=current_user.id,
        )
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
async def trigger_run_now(
    schedule_id: str = "default-schedule",
    current_user: Optional[UserRecord] = Depends(get_optional_user),
):
    """Immediately trigger a screening run using the authenticated user's saved schedule."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to run schedules.",
        )
    owned = scheduler_service.get_schedule(
        schedule_id,
        owner_email=current_user.email,
        user_id=current_user.id,
    )
    if not owned:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule '{schedule_id}' not found for current user.",
        )
    try:
        result = await scheduler_service.execute_scheduled_run(schedule_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule '{schedule_id}' not found or paused.",
            )
        return {
            "success": True,
            "message": f"Screening run {result.run_id} executed successfully.",
            "run_id": result.run_id,
            "status": result.status,
            "securities_count": result.results_count,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing run now: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute screening run: {str(e)}",
        )
