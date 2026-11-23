import sqlite3
import re
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from models.fallback_models import strip_question_wrappers, get_dedup_hash

conn = sqlite3.connect("interview_intelligence.db")
c = conn.cursor()

c.execute("SELECT id, question_text FROM interview_questions")
rows = c.fetchall()

updated = 0
deleted = 0
seen_hashes = set()

for qid, text in rows:
    cleaned = strip_question_wrappers(text)
    
    # Strip any additional prefixes
    cleaned = re.sub(r"^(?:(?:Round \d+|Online Assessment|OA|Machine Coding|System Design|Technical Round|Behavioral Round)[\s:\-]+)+", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"^(?:Topics|Java Core|Concurrency|Follow-up|Product Sense|Problem Statement|Problem|Question)[\s:\-]+", "", cleaned, flags=re.IGNORECASE).strip()
    
    # Check if text is an unsplit multi-round experience dump
    if "Round 1 was" in cleaned or "Round 2 was" in cleaned or "I recently completed" in cleaned:
        c.execute("DELETE FROM interview_questions WHERE id = ?", (qid,))
        deleted += 1
        continue

    if len(cleaned) < 20:
        c.execute("DELETE FROM interview_questions WHERE id = ?", (qid,))
        deleted += 1
        continue

    h = get_dedup_hash(cleaned)
    if h in seen_hashes:
        c.execute("DELETE FROM interview_questions WHERE id = ?", (qid,))
        deleted += 1
        continue
    seen_hashes.add(h)

    if cleaned != text:
        c.execute("UPDATE interview_questions SET question_text = ?, content_hash = ? WHERE id = ?", (cleaned, h, qid))
        updated += 1

conn.commit()
print(f"Prefix cleanup complete: {updated} questions cleaned of prefixes, {deleted} dumps/duplicates deleted.")

c.execute("SELECT count(*) FROM interview_questions")
print(f"Total verified clean questions remaining: {c.fetchone()[0]}")
conn.close()
