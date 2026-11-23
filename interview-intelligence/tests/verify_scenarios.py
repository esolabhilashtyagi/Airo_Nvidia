import requests
import json

scenarios = [
    ("Case A: Google SDE II (Tech)", {"company_name": "Google", "role": "Software Development Engineer II", "years_of_experience": 4.0, "skills": ["Python", "Distributed Systems", "Algorithms"]}),
    ("Case A: Netflix Senior Systems (Tech)", {"company_name": "Netflix", "role": "Senior Distributed Systems Engineer", "years_of_experience": 6.0, "skills": ["Java", "Concurrency", "Kafka"]}),
    ("Case A: Stripe Staff Backend (Tech)", {"company_name": "Stripe", "role": "Staff Backend Engineer", "years_of_experience": 8.0, "skills": ["Golang", "Idempotency", "Distributed Transactions"]}),
    ("Case A: NVIDIA Systems/CUDA (Tech)", {"company_name": "NVIDIA", "role": "Senior Systems Software Engineer", "years_of_experience": 7.0, "skills": ["C++", "CUDA", "Concurrency", "Linux"]}),
    ("Case A: Amazon Junior SDE (Junior Tech)", {"company_name": "Amazon", "role": "Software Development Engineer I", "years_of_experience": 1.0, "skills": ["Java", "Algorithms", "Clean Code"]}),
    ("Case A: Google PM (Non-Tech)", {"company_name": "Google", "role": "Senior Product Manager", "years_of_experience": 6.0, "skills": ["Product Strategy", "Metrics", "A/B Testing"]}),
    ("Case A: Figma Designer (Non-Tech)", {"company_name": "Figma", "role": "Lead Product Designer", "years_of_experience": 5.0, "skills": ["Figma", "Design Systems", "User Research"]}),
    ("Case A: Salesforce Sales (Non-Tech)", {"company_name": "Salesforce", "role": "Enterprise Account Executive", "years_of_experience": 5.5, "skills": ["MEDDPICC", "Pipeline Generation", "Objection Handling"]}),
    ("Case A: Microsoft Finance (Non-Tech)", {"company_name": "Microsoft", "role": "Senior Financial Analyst", "years_of_experience": 5.0, "skills": ["3-Statement Modeling", "SaaS Metrics", "DCF"]}),
    ("Case B: Startup Fintech Backend (Case B)", {"industry": "Fintech", "role": "Backend Engineer (Payments)", "years_of_experience": 3.0, "skills": ["Kafka", "PostgreSQL", "Idempotency"]}),
    ("Case B: Startup Growth Marketing (Case B Non-Tech)", {"industry": "Consumer Internet", "role": "Growth Marketing Lead", "years_of_experience": 3.5, "skills": ["CAC/LTV", "Funnel CRO", "Meta Ads"]}),
]

for label, payload in scenarios:
    res = requests.post("http://localhost:8000/intelligence/interview-blueprint", json=payload)
    if res.status_code == 200:
        data = res.json()
        print(f"\n=======================================================")
        print(f"=== {label} ===")
        print(f"Target: {data['target_name']} ({data['target_type']}) | Role Family: {data.get('role_family')} | Total Rounds: {data['total_rounds']}")
        for r in data["rounds"]:
            print(f"  [{r['round_number']}] {r['round_name']}")
            print(f"      Type: {r['round_type']}")
            if r["questions"]:
                q = r["questions"][0]
                q_snippet = q["question_text"][:110].replace("\n", " ")
                print(f"      Q: {q_snippet}...")
    else:
        print(f"Error for {label}: {res.status_code} {res.text}")
