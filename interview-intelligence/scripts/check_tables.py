import sqlite3

conn = sqlite3.connect("interview_intelligence.db")
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = c.fetchall()
for t in tables:
    c.execute(f"SELECT count(*) FROM {t[0]}")
    cnt = c.fetchone()[0]
    print(f"{t[0]}: {cnt}")
conn.close()
