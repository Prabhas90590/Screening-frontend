const fs = require('fs');

let p = 'backend/app/api/routes/schedules.py';
let content = fs.readFileSync(p, 'utf8').replace(/\r\n/g, '\n');

// 1. Ensure Query and Optional are imported
content = content.replace(
  'from typing import Any, Dict, List',
  'from typing import Any, Dict, List, Optional'
);
content = content.replace(
  'from fastapi import APIRouter, HTTPException, status',
  'from fastapi import APIRouter, HTTPException, Query, status'
);

// 2. Update get_schedules to accept cadence query
const oldGet = `def get_schedules():
    """Retrieve all saved schedules, active schedule, and aggregated next run timestamps."""
    try:
        schedules = scheduler_service.list_schedules()
        active = schedules[0] if schedules else None
        flat_runs, detailed_runs, by_freq = scheduler_service.calculate_all_next_runs()
        return ScheduleResponse(
            success=True,
            message="Schedule configurations retrieved.",
            schedule=active,
            schedules=schedules,
            next_runs=flat_runs,
            next_runs_detailed=detailed_runs,
            next_runs_by_frequency=by_freq,
        )`;

const newGet = `def get_schedules(cadence: Optional[str] = Query(default=None)):
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
        )`;

content = content.replace(oldGet, newGet);

// 3. Add remove_schedule_day before trigger_run_now
const dayRemovalEndpoint = `
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


`;

content = content.replace('@router.post("/run-now")', dayRemovalEndpoint + '@router.post("/run-now")');

fs.writeFileSync(p, content.replace(/\n/g, '\r\n'), 'utf8');
console.log('routes/schedules.py updated successfully.');

