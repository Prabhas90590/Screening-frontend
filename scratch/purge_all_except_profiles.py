import psycopg2, os
from dotenv import load_dotenv

load_dotenv('backend/.env')
url = os.getenv('DATABASE_URL')
conn = psycopg2.connect(url)
cur = conn.cursor()

print("=" * 60)
print("PRE-PURGE PROFILE CHECK (These will be PRESERVED):")
print("=" * 60)
cur.execute("SELECT version_id, profile_name, version_number, is_active FROM rule_versions;")
profiles = cur.fetchall()
for p in profiles:
    print(f"  Profile: {p[0]} | {p[1]} v{p[2]} | Active: {p[3]}")

cur.execute("SELECT count(*) FROM rules;")
print(f"  Associated Rules count: {cur.fetchone()[0]}")

print("\n" + "=" * 60)
print("PURGING ALL NON-PROFILE TABLES...")
print("=" * 60)

tables_to_purge = [
    "screening_results",
    "funnel_counts",
    "screening_runs",
    "holdings",
    "raw_responses",
    "decisions",
    "estimate_snapshots",
    "financial_snapshots",
    "company_metrics",
    "listings",
    "companies",
    "schedules",
    "schedules_daily",
    "schedules_weekly",
    "schedules_monthly",
    "schedules_custom",
    "audit_events",
]

truncate_sql = f"TRUNCATE TABLE {', '.join(tables_to_purge)} CASCADE;"
cur.execute(truncate_sql)
conn.commit()
print("Successfully executed TRUNCATE CASCADE on all non-profile tables.")

print("\n" + "=" * 60)
print("POST-PURGE VERIFICATION:")
print("=" * 60)
cur.execute("""
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public' 
    ORDER BY table_name;
""")
all_tables = [r[0] for r in cur.fetchall()]
for t in all_tables:
    cur.execute(f"SELECT count(*) FROM {t};")
    cnt = cur.fetchone()[0]
    status = "PRESERVED" if t in ("rule_versions", "rules") else ("CLEARED (0)" if cnt == 0 else "WARNING")
    print(f"  {t:25} -> {cnt:5} rows [{status}]")

conn.close()

