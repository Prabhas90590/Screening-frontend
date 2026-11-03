import sqlite3, os

for p in ['screening.db', 'backend/screening.db']:
    if os.path.exists(p):
        conn = sqlite3.connect(p)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [r[0] for r in cur.fetchall()]
        print(f"=== {p} ({len(tables)} tables) ===")
        for t in ['schedules', 'schedules_daily', 'schedules_weekly']:
            if t in tables:
                cur.execute(f"SELECT schedule_id, frequency, active_days, time_of_day FROM {t}")
                print(f"  {t}:", cur.fetchall())
    else:
        print(f"{p} does not exist.")

