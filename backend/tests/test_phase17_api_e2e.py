from pathlib import Path
"""End-to-end API test for Phase 17 Scheduler endpoints."""

import os
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_schedules_api_endpoints():
    print("1. Testing GET /api/schedules...")
    res = client.get("/api/schedules")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    assert data["success"] is True
    assert "schedule" in data
    assert "next_runs" in data
    print(f"   [SUCCESS] GET /api/schedules returned: frequency={data['schedule']['frequency']}, next_runs count={len(data['next_runs'])}")

    print("2. Testing POST /api/schedules with Daily schedule...")
    daily_payload = {
        "schedule_id": "default-schedule",
        "profile_name": "Global Quality Growth Core - Version 1",
        "frequency": "Daily",
        "daily_type": "trading_days",
        "time_of_day": "08:30",
        "timezone": "Asia/Kolkata",
        "notification_email": "prabhas.muthyala@zeniusit.com, manoj@zeniusit.com",
        "is_enabled": True,
        "auto_run": True,
        "refresh_data_first": True,
        "skip_holidays": True,
        "notify_triggers": {
            "runCompletes": True,
            "runFails": True,
            "dataBlockers": True
        }
    }
    post_res = client.post("/api/schedules", json=daily_payload)
    assert post_res.status_code == 200, f"Expected 200, got {post_res.status_code}: {post_res.text}"
    post_data = post_res.json()
    assert post_data["success"] is True
    assert post_data["schedule"]["frequency"] == "Daily"
    assert post_data["schedule"]["time_of_day"] == "08:30"
    assert len(post_data["next_runs"]) == 3
    print(f"   [SUCCESS] POST /api/schedules saved successfully! Next 3 runs: {post_data['next_runs']}")

    print("3. Testing POST /api/schedules with Weekly schedule...")
    weekly_payload = {
        "schedule_id": "default-schedule",
        "profile_name": "Global Quality Growth Core - Version 1",
        "frequency": "Weekly",
        "active_days": ["mon", "thu"],
        "time_of_day": "09:00",
        "timezone": "Asia/Kolkata",
        "notification_email": "prabhas.muthyala@zeniusit.com",
    }
    post_w_res = client.post("/api/schedules", json=weekly_payload)
    assert post_w_res.status_code == 200
    assert post_w_res.json()["schedule"]["frequency"] == "Weekly"
    print("   [SUCCESS] Weekly schedule saved and verified!")

    print("4. Testing POST /api/schedules with Monthly schedule...")
    monthly_payload = {
        "schedule_id": "default-schedule",
        "profile_name": "Global Quality Growth Core - Version 1",
        "frequency": "Monthly",
        "day_of_month": 1,
        "time_of_day": "08:30",
        "timezone": "Asia/Kolkata",
        "notification_email": "prabhas.muthyala@zeniusit.com",
    }
    post_m_res = client.post("/api/schedules", json=monthly_payload)
    assert post_m_res.status_code == 200
    assert post_m_res.json()["schedule"]["frequency"] == "Monthly"
    print("   [SUCCESS] Monthly schedule saved and verified!")

    print("5. Restoring Daily default schedule for production use...")
    client.post("/api/schedules", json=daily_payload)
    print("   [SUCCESS] Daily production schedule restored!")


if __name__ == "__main__":
    test_schedules_api_endpoints()
    print("\n" + "=" * 60)
    print("ALL API END-TO-END TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

