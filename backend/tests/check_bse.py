import psycopg2

conn = psycopg2.connect('postgresql://postgres:prabhas123@localhost:5432/screening_db')
cur = conn.cursor()
cur.execute("SELECT primary_ticker, primary_exchange FROM companies WHERE primary_exchange = 'BSE';")
rows = cur.fetchall()
print(f"Total BSE companies in companies table: {len(rows)}")
for r in rows[:10]:
    print(r)

cur.execute("SELECT ticker, exchange_id, is_primary FROM listings WHERE exchange_id = 'bse';")
listings_bse = cur.fetchall()
print(f"Total BSE listings in listings table: {len(listings_bse)}")
for r in listings_bse[:10]:
    print(r)

conn.close()

