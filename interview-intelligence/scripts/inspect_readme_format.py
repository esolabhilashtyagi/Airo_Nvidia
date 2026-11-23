import httpx
import re

url = "https://raw.githubusercontent.com/bregman-arie/devops-exercises/master/topics/linux/README.md"
res = httpx.get(url, headers={"User-Agent": "Mozilla/5.0"})
lines = res.text.splitlines()

qs = []
for i, line in enumerate(lines):
    line_clean = line.strip()
    if "?" in line_clean or line_clean.lower().startswith("what is") or line_clean.lower().startswith("how "):
        qs.append(line_clean)

print("Found lines with questions:", len(qs))
for q in qs[:15]:
    print(" -", q)
