import sys
sys.path.insert(0, 'backend')

from app.services.scheduler_service import scheduler_service
from app.schemas.schedule import ScheduleConfigSchema

print("=" * 70)
print("TEST: Cadence Table Isolation & Single-Day Deletion")
print("=" * 70)

# 1. Clean slate
for s in scheduler_service.list_schedules():
    scheduler_service.delete_schedule(s.schedule_id)

# 2. Create 4 schedules, one for each cadence
s_daily = ScheduleConfigSchema(
    schedule_id="test-sched-daily-5pm",
    frequency="Daily",
    time_of_day="17:00",
    profile_name="Daily Growth",
    active_days=["mon", "tue", "wed", "thu", "fri"],
    is_enabled=True
)
s_weekly = ScheduleConfigSchema(
    schedule_id="test-sched-weekly-mon",
    frequency="Weekly",
    time_of_day="09:00",
    profile_name="Weekly Dividend",
    active_days=["mon"],
    is_enabled=True
)
s_monthly = ScheduleConfigSchema(
    schedule_id="test-sched-monthly-1st",
    frequency="Monthly",
    time_of_day="10:00",
    profile_name="Monthly Rebalance",
    day_of_month=1,
    is_enabled=True
)
s_custom = ScheduleConfigSchema(
    schedule_id="test-sched-custom-cron",
    frequency="Custom",
    time_of_day="12:00",
    profile_name="Custom Strategy",
    cron_expression="0 12 * * 1-5",
    is_enabled=True
)

scheduler_service.save_schedule(s_daily)
scheduler_service.save_schedule(s_weekly)
scheduler_service.save_schedule(s_monthly)
scheduler_service.save_schedule(s_custom)

print("1. All 4 cadence schedules saved successfully!")

# 3. Test cadence-specific queries
daily_list = scheduler_service.list_schedules(cadence="daily")
weekly_list = scheduler_service.list_schedules(cadence="weekly")
monthly_list = scheduler_service.list_schedules(cadence="monthly")
custom_list = scheduler_service.list_schedules(cadence="custom")

print(f"   Daily count: {len(daily_list)} -> {[s.schedule_id for s in daily_list]}")
print(f"   Weekly count: {len(weekly_list)} -> {[s.schedule_id for s in weekly_list]}")
print(f"   Monthly count: {len(monthly_list)} -> {[s.schedule_id for s in monthly_list]}")
print(f"   Custom count: {len(custom_list)} -> {[s.schedule_id for s in custom_list]}")

assert len(daily_list) == 1 and daily_list[0].schedule_id == "test-sched-daily-5pm"
assert len(weekly_list) == 1 and weekly_list[0].schedule_id == "test-sched-weekly-mon"
assert len(monthly_list) == 1 and monthly_list[0].schedule_id == "test-sched-monthly-1st"
assert len(custom_list) == 1 and custom_list[0].schedule_id == "test-sched-custom-cron"
print("2. [PASS] Cadence table isolation verified! Each cadence lives in its own table.")

# 4. Test removing Wednesday ('wed') from the 5pm Daily schedule
print("\n3. Testing single-day deletion: Removing Wednesday from Mon-Fri Daily schedule...")
updated_daily = scheduler_service.remove_day_from_schedule("test-sched-daily-5pm", "wed")
assert updated_daily is not None
print(f"   Updated active_days: {updated_daily.active_days}")
assert "wed" not in updated_daily.active_days, "Wednesday was not removed!"
assert "mon" in updated_daily.active_days, "Monday must still be active!"
assert "tue" in updated_daily.active_days, "Tuesday must still be active!"
assert "thu" in updated_daily.active_days, "Thursday must still be active!"
assert "fri" in updated_daily.active_days, "Friday must still be active!"
print("   [PASS] Wednesday deleted successfully! Mon, Tue, Thu, Fri preserved and running!")

# 5. Verify deleting an entire schedule deletes ONLY that schedule
print("\n4. Testing deleting only Weekly schedule...")
scheduler_service.delete_schedule("test-sched-weekly-mon")

remaining_all = scheduler_service.list_schedules()
remaining_ids = [s.schedule_id for s in remaining_all]
print(f"   Remaining schedules: {remaining_ids}")
assert "test-sched-weekly-mon" not in remaining_ids, "Weekly schedule should be deleted!"
assert "test-sched-daily-5pm" in remaining_ids, "Daily schedule MUST still exist!"
assert "test-sched-monthly-1st" in remaining_ids, "Monthly schedule MUST still exist!"
assert "test-sched-custom-cron" in remaining_ids, "Custom schedule MUST still exist!"
print("   [PASS] Only the Weekly schedule was deleted! Daily, Monthly, and Custom untouched.")

# 6. Cleanup
for s in remaining_all:
    scheduler_service.delete_schedule(s.schedule_id)
print("\n[SUCCESS] ALL VERIFICATION TESTS PASSED CLEANLY!")

