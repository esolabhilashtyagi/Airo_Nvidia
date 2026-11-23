import httpx
import re

url = "https://raw.githubusercontent.com/donnemartin/system-design-primer/master/README.md"
res = httpx.get(url, headers={"User-Agent": "Mozilla/5.0"})
print("System Design Primer Status:", res.status_code)
lines = res.text.splitlines()
sys_qs = []
for line in lines:
    line_clean = line.strip()
    m = re.findall(r"\[(Design\s+[^\]]+)\]", line_clean)
    for match in m:
        if len(match) > 10 and not match.endswith("topics"):
            sys_qs.append(match)

print("Found system design questions:", len(sys_qs))
for q in set(sys_qs):
    print(" -", q)
