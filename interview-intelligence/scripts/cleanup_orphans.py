import sqlite3

conn = sqlite3.connect("interview_intelligence.db")
c = conn.cursor()

c.execute("DELETE FROM embeddings WHERE question_id NOT IN (SELECT id FROM interview_questions)")
del_emb = c.rowcount
print(f"Deleted {del_emb} orphaned embeddings.")

c.execute("DELETE FROM question_categories WHERE name LIKE '% Domain%'")
del_cats = c.rowcount
print(f"Deleted {del_cats} broken category rows.")

conn.commit()

print("Running VACUUM...")
conn.execute("VACUUM")
conn.close()
print("Orphan cleanup and vacuum complete.")
