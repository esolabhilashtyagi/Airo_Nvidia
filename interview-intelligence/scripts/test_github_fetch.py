import httpx
import re

url = "https://raw.githubusercontent.com/bregman-arie/devops-exercises/master/topics/linux/README.md"
headers = {"User-Agent": "Mozilla/5.0"}

res = httpx.get(url, headers=headers)
print("Status code:", res.status_code)
print("Length:", len(res.text))

# Print first 20 lines that look like questions
lines = res.text.splitlines()
questions = []
for line in lines:
    line = line.strip()
    if line.startswith("####") or line.startswith("###") or (line.startswith("*") and line.endswith("?")):
        clean_q = re.sub(r"^#+\s*", "", line).strip("* ")
        if len(clean_q) > 15:
            questions.append(clean_q)

print(f"Extracted {len(questions)} questions. Samples:")
for q in questions[:10]:
    print(" -", q)
