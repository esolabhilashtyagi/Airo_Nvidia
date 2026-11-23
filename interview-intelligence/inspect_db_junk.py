import sqlite3

conn = sqlite3.connect("interview_intelligence.db")
c = conn.cursor()

c.execute("SELECT id, company_name, job_role, question_text, source_platform, original_url FROM interview_questions WHERE NOT (original_url LIKE '%engineering_blogs%' OR original_url LIKE '%company blog%' OR original_url LIKE '%_1_%' OR original_url LIKE '%_2_%' OR original_url LIKE '%_3_%' OR original_url LIKE '%_4_%' OR original_url LIKE '%_5_%') LIMIT 20")
rows = c.fetchall()
print(f"Non-synthetic rows found: {len(rows)}")
for r in rows:
    print(r[0], "|", r[1], "|", r[4], "|", r[5], "|", r[3][:60])

c.execute("SELECT count(*) FROM interview_questions WHERE NOT (original_url LIKE '%engineering_blogs%' OR original_url LIKE '%company blog%' OR original_url LIKE '%_1_%' OR original_url LIKE '%_2_%' OR original_url LIKE '%_3_%' OR original_url LIKE '%_4_%' OR original_url LIKE '%_5_%')")
real_count = c.fetchone()[0]
print("Total real count:", real_count)

conn.close()
