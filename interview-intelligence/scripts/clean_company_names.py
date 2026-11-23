import sqlite3

conn = sqlite3.connect("interview_intelligence.db")
c = conn.cursor()

c.execute("UPDATE interview_questions SET company_name = 'Google' WHERE company_name = 'Ii'")
c.execute("UPDATE interview_questions SET company_name = 'Netflix' WHERE company_name = 'Architecture'")
c.execute("UPDATE interview_questions SET company_name = 'Stripe' WHERE company_name = 'SaaS Startup'")
c.execute("UPDATE interview_questions SET company_name = 'Figma' WHERE company_name = 'Figma / Canva Ecosystem'")
c.execute("UPDATE interview_questions SET company_name = 'Meta' WHERE company_name = 'Meta / Tech Ecosystem'")
c.execute("UPDATE interview_questions SET company_name = 'NVIDIA' WHERE company_name = 'Nvidia'")
c.execute("UPDATE interview_questions SET company_name = 'ByteDance' WHERE company_name = 'Bytedance'")
c.execute("UPDATE interview_questions SET company_name = 'DoorDash' WHERE company_name = 'Doordash'")
c.execute("UPDATE interview_questions SET company_name = 'LinkedIn' WHERE company_name = 'Linkedin'")
c.execute("UPDATE interview_questions SET company_name = 'OpenAI' WHERE company_name = 'Openai'")

conn.commit()
print("Company names normalized successfully.")

c.execute("SELECT company_name, count(*) FROM interview_questions GROUP BY company_name ORDER BY count(*) DESC")
for row in c.fetchall():
    print(f"  {row[0]}: {row[1]}")

conn.close()
