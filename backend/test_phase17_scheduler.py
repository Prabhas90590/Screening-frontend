"""Unit and integration test for Phase 17 Scheduler."""

from datetime import datetime, timezone, timedelta
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from app.db.connection import db_manager
from app.schemas.schedule import ScheduleConfigSchema
from app.services.scheduler_service import scheduler_service, IST_TZ


def test_scheduler_lifecycle():
    print("1. Initializing database tables and migrations...")
    db_manager.init_tables()
    print("   [SUCCESS] Database tables and migrations verified!")

    print("2. Testing next-run calculation for Daily (trading days)...")
    daily_cfg = ScheduleConfigSchema(
        schedule_id="test-daily",
        frequency="Daily",
        daily_type="trading_days",
        time_of_day="08:30",
        timezone="Asia/Kolkata",
    )
    # Ref: Friday 14:00 IST
    ref_dt = datetime(2026, 10, 30, 14, 0, 0, tzinfo=IST_TZ)
    daily_runs = scheduler_service.calculate_next_runs(daily_cfg, count=3, ref_dt=ref_dt)
    print(f"   Daily next runs: {[r.strftime('%Y-%m-%d %H:%M') for r in daily_runs]}")
    assert len(daily_runs) == 3
    # Next trading day after Friday Oct 30 is Monday Nov 02
    assert daily_runs[0].date().weekday() == 0  # Monday
    assert daily_runs[0].day == 2
    assert daily_runs[0].hour == 8 and daily_runs[0].minute == 30
    print("   [SUCCESS] Daily trading days calculation verified!")

    print("3. Testing next-run calculation for Weekly...")
    weekly_cfg = ScheduleConfigSchema(
        schedule_id="test-weekly",
        frequency="Weekly",
        active_days=["mon", "thu"],
        time_of_day="09:00",
        timezone="Asia/Kolkata",
    )
    weekly_runs = scheduler_service.calculate_next_runs(weekly_cfg, count=3, ref_dt=ref_dt)
    print(f"   Weekly next runs: {[r.strftime('%Y-%m-%d %H:%M') for r in weekly_runs]}")
    assert len(weekly_runs) == 3
    assert weekly_runs[0].weekday() == 0  # Mon
    assert weekly_runs[1].weekday() == 3  # Thu
    print("   [SUCCESS] Weekly next runs verified!")

    print("4. Testing next-run calculation for Monthly...")
    monthly_cfg = ScheduleConfigSchema(
        schedule_id="test-monthly",
        frequency="Monthly",
        day_of_month=1,
        time_of_day="10:00",
        timezone="Asia/Kolkata",
    )
    monthly_runs = scheduler_service.calculate_next_runs(monthly_cfg, count=3, ref_dt=ref_dt)
    print(f"   Monthly next runs: {[r.strftime('%Y-%m-%d %H:%M') for r in monthly_runs]}")
    assert len(monthly_runs) == 3
    assert monthly_runs[0].day == 1 and monthly_runs[0].month == 11
    assert monthly_runs[1].day == 1 and monthly_runs[1].month == 12
    print("   [SUCCESS] Monthly next runs verified!")

    print("5. Testing save and retrieval from database...")
    save_cfg = ScheduleConfigSchema(
        schedule_id="default-schedule",
        profile_name="Global Quality Growth Core - Version 1",
        frequency="Daily",
        daily_type="trading_days",
        time_of_day="08:30",
        timezone="Asia/Kolkata",
        notification_email="prabhas.muthyala@zeniusit.com, manoj@zenius.com",
    )
    saved = scheduler_service.save_schedule(save_cfg)
    assert saved.next_run_at is not None
    print(f"   Saved next_run_at: {saved.next_run_at}")

    retrieved = scheduler_service.get_schedule("default-schedule")
    print(f"   Retrieved frequency: {retrieved.frequency}, time: {retrieved.time_of_day}, emails: {retrieved.notification_email}")
    assert retrieved.frequency == "Daily"
    assert retrieved.daily_type == "trading_days"
    assert retrieved.time_of_day == "08:30"
    assert "prabhas.muthyala@zeniusit.com" in retrieved.notification_email
    print("   [SUCCESS] Database persistence and retrieval verified!")


if __name__ == "__main__":
    test_scheduler_lifecycle()
    print("\n" + "=" * 60)
    print("ALL PHASE 17 SCHEDULER BACKEND CHECKS PASSED!")
    print("=" * 60)

