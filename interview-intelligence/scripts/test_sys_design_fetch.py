import httpx
import re

url = "https://raw.githubusercontent.com/donnemartin/system-design-primer/master/solutions/system_design/README.md"
res = httpx.get(url, headers={"User-Agent": "Mozilla/5.0"})
print("System Design Primer Status:", res.status_code)
lines = res.text.splitlines()
sys_qs = []
for line in lines:
    line_clean = line.strip()
    # Match design topics e.g. [Design Pastebin](...) or ### Design ...
    m = re.search(r"\[(Design [^\]]+)\]", line_clean)
    if m:
        sys_qs.append(m.group(1))

print("Found system design questions:", len(sys_qs))
for q in sys_qs[:10]:
    print(" -", q)
