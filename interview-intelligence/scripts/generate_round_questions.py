"""
Generate Domain-Specific Dorks & Round-by-Round Interview Questions.
Uses NVIDIA Nemotron inference (with deterministic domain fallback) to take raw
(company, role, YoE, skills) input, generate dynamic open-web search queries for each round,
and output the exact, highly relevant interview questions for each canonical round.
"""

import argparse
import asyncio
import os
import sys
import pandas as pd
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.model_manager import get_model_manager
from database.repository import get_db_repository


async def run_generator(
    company: str,
    role: str,
    yoe: float,
    skills: list,
    round_number: int = None,
    export_csv: str = None,
):
    print("=" * 75)
    print(f"🎯 Nemotron Dynamic Dork & Round Question Synthesis Engine")
    print(f"🏢 Company: {company} | Role: {role} | YoE: {yoe} yrs | Skills: {skills}")
    print("=" * 75)

    mm = get_model_manager()
    db = get_db_repository()

    # Stage 1: Generate domain-specific open-web search queries
    print("\n🔍 [STAGE 1] Nemotron Domain-Specific Open-Web Search Dorks:")
    dorks_result = await mm.generate_domain_dorks(company=company, role=role, yoe=yoe, skills=skills)
    round_dorks = dorks_result.get("round_dorks", {})

    for r_key, q_list in round_dorks.items():
        r_title = r_key.replace("_", " ").upper()
        print(f"\n  🔹 {r_title}:")
        for q in q_list:
            print(f"     • {q}")

    platform_q = dorks_result.get("platform_queries", {})
    if platform_q:
        print("\n  🌐 Platform-Specific Deep Discovery Queries:")
        for plat, pq in platform_q.items():
            print(f"     [{plat}]: {pq}")

    # Stage 2: Retrieve & Synthesize High-Quality Questions for Each Round
    print("\n" + "=" * 75)
    print("📚 [STAGE 2] Synthesizing Exact, Highly-Relevant Questions For Each Round:")
    print("=" * 75)

    # 1. Fetch any verified authentic questions in database
    db_questions = db.get_maximum_relevant_questions(
        company=company, role=role, yoe=yoe, skills=skills, limit=100
    )

    # 2. Synthesize domain questions for complete 5-round coverage
    synthesized = await mm.synthesize_round_questions(
        company=company, role=role, yoe=yoe, skills=skills, round_number=round_number
    )

    combined_questions = []
    seen_texts = set()

    # Prioritize verified DB questions matching round
    for q in db_questions:
        q_text = q.question_text.strip()
        if len(q_text) >= 25 and q_text not in seen_texts:
            seen_texts.add(q_text)
            combined_questions.append({
                "Round": getattr(q, "round_number", 2),
                "Interview Round": getattr(q, "interview_round", "Round 2: Core Coding & Problem Solving (DSA)"),
                "Company": q.company_name,
                "Type": "MNC" if "MNC" in db.classify_company_tier(q.company_name) else "STARTUP",
                "Role": q.job_role or role,
                "Question": q_text,
                "Category": q.question_category or "Data Structures and Algorithms",
                "Difficulty": q.difficulty or "Medium",
                "Platform": q.source_platform or "Verified Interview Archive",
                "URL": q.original_url or f"https://www.{company.lower()}.com/careers",
            })

    # Add synthesized questions for rounds needing coverage
    for sq in synthesized:
        q_text = sq["question_text"].strip()
        if q_text not in seen_texts:
            seen_texts.add(q_text)
            combined_questions.append({
                "Round": sq["round_number"],
                "Interview Round": sq["interview_round"],
                "Company": company,
                "Type": "MNC",
                "Role": role,
                "Question": q_text,
                "Category": sq["category"],
                "Difficulty": sq["difficulty"],
                "Platform": sq["source_platform"],
                "URL": f"https://leetcode.com/discuss/interview-question/{company.lower()}-interview",
            })

    # Sort by round number
    combined_questions.sort(key=lambda x: (x["Round"], x["Difficulty"]))

    print(f"\n✅ Total Highly-Relevant Questions Generated: {len(combined_questions)}")
    for q in combined_questions:
        print(f"  [Round {q['Round']} | {q['Category']} | {q['Difficulty']}] {q['Question'][:90]}...")

    # Stage 3: Export to CSV if requested
    if export_csv:
        df = pd.DataFrame(combined_questions)
        df.to_csv(export_csv, index=False)
        print(f"\n💾 Saved {len(df)} questions cleanly to: {export_csv}")

    return combined_questions, dorks_result


def main():
    parser = argparse.ArgumentParser(description="Nemotron Dynamic Dork & Round Question Generator")
    parser.add_argument("--company", default="Google", help="Target company name (e.g. Google, Meta, Amazon)")
    parser.add_argument("--role", default="Software Development Engineer II", help="Target job role")
    parser.add_argument("--yoe", type=float, default=4.0, help="Years of Experience")
    parser.add_argument("--skills", default="Python,Distributed Systems,Concurrency,Algorithms", help="Comma-separated skills")
    parser.add_argument("--round", type=int, default=None, help="Specific round (1 to 5)")
    parser.add_argument("--export-csv", default=None, help="Path to export CSV")

    args = parser.parse_args()
    skills_list = [s.strip() for s in args.skills.split(",") if s.strip()]

    asyncio.run(
        run_generator(
            company=args.company,
            role=args.role,
            yoe=args.yoe,
            skills=skills_list,
            round_number=args.round,
            export_csv=args.export_csv,
        )
    )


if __name__ == "__main__":
    main()
