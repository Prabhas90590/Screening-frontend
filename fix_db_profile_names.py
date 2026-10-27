import psycopg2

conn = psycopg2.connect('postgresql://postgres:prabhas123@localhost:5432/screening_db')
cur = conn.cursor()

# Update historical runs based on their rule_version_id
cur.execute("UPDATE screening_runs SET profile_name = 'core v1 - Version 1' WHERE rule_version_id = 'prof-b5e379d3';")
cur.execute("UPDATE screening_runs SET profile_name = 'core v1 - Version 2' WHERE rule_version_id = 'prof-784cff83';")
conn.commit()

cur.execute("SELECT run_id, profile_name, rule_version_id FROM screening_runs ORDER BY started_at DESC;")
for r in cur.fetchall():
    print(r)

conn.close()

