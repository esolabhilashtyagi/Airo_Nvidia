import httpx
import re

url = "https://raw.githubusercontent.com/bregman-arie/devops-exercises/master/topics/linux/README.md"
res = httpx.get(url, headers={"User-Agent": "Mozilla/5.0"})
summaries = re.findall(r"<summary>(.*?)</summary>", res.text, re.DOTALL)
print("Found summary questions:", len(summaries))
clean_qs = []
for s in summaries:
    c = re.sub(r"<[^>]+>", "", s).strip()
    c = " ".join(c.split())
    if len(c) > 15:
        clean_qs.append(c)

print(f"Clean valid questions: {len(clean_qs)}")
for q in clean_qs[:10]:
    print(" -", q)
