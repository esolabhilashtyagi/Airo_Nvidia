import sqlite3

conn = sqlite3.connect("interview_intelligence.db")
c = conn.cursor()

c.execute("SELECT count(*) FROM interview_questions")
total = c.fetchone()[0]
print(f"Total rows in DB: {total}")

c.execute("""
SELECT count(*) FROM interview_questions 
WHERE original_url LIKE '%engineering_blogs%' 
   OR original_url LIKE '%company blog%' 
   OR original_url LIKE '%_1_%' 
   OR original_url LIKE '%_2_%' 
   OR original_url LIKE '%_3_%' 
   OR original_url LIKE '%_4_%' 
   OR original_url LIKE '%_5_%'
""")
synth_count = c.fetchone()[0]
print(f"Synthetic template spam rows: {synth_count}")

c.execute("SELECT count(*) FROM interview_questions WHERE question_category LIKE '% Domain%'")
domain_count = c.fetchone()[0]
print(f"Broken Domain category rows: {domain_count}")

c.execute("""
SELECT count(*) FROM interview_questions 
WHERE question_text LIKE '>%' 
   OR question_text LIKE '%suggest some website%' 
   OR question_text LIKE '%notion floating around%' 
   OR question_text LIKE '%Eric Schmidt%' 
   OR question_text LIKE '%Interview Questions Deconstructed%'
   OR question_text LIKE '%Interview Questions That Will Make%'
   OR question_text LIKE 'Interview Questions for Growth%'
""")
hn_garbage_count = c.fetchone()[0]
print(f"HN headline/comment garbage rows: {hn_garbage_count}")

c.execute("""
SELECT count(*) FROM interview_questions 
WHERE question_text LIKE 'I recently completed%'
   OR question_text LIKE 'Round 1 was%'
   OR question_text LIKE 'My interview experience at%'
""")
unsplit_dumps = c.fetchone()[0]
print(f"Unsplit interview experience dumps: {unsplit_dumps}")

c.execute("SELECT company_name, count(*) FROM interview_questions GROUP BY company_name ORDER BY count(*) DESC LIMIT 20")
print("\nTop 20 companies in DB:")
for row in c.fetchall():
    print(f"  {row[0]}: {row[1]}")

c.execute("SELECT DISTINCT question_category FROM interview_questions ORDER BY question_category")
cats = [r[0] for r in c.fetchall()]
print(f"\nDistinct categories in DB ({len(cats)}):")
for cat in cats[:30]:
    print(f"  {cat}")

conn.close()
