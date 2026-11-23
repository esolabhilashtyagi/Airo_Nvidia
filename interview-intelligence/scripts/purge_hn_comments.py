import sqlite3

conn = sqlite3.connect("interview_intelligence.db")
c = conn.cursor()

c.execute("""
DELETE FROM interview_questions 
WHERE source_platform = 'HackerNews Public Live Index'
""")
deleted = c.rowcount
print(f"Deleted {deleted} HackerNews forum comment rows.")
conn.commit()

c.execute("SELECT count(*) FROM interview_questions")
print(f"Total authentic questions in DB: {c.fetchone()[0]}")
conn.close()
