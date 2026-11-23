"""
Interview Intelligence Dataset Maintenance Engine.
Maintains, validates, exports, and audits the 13,600+ interview questions repository.
Generates structured JSONL, CSV, and round-by-round splits in the data/ directory.
Supports automated quality auditing, deduplication verification, and round indexing.
"""

import sys
import os
import argparse
import json
import csv
from datetime import datetime
from typing import Dict, Any, List

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.repository import get_db_repository
from database.models import InterviewQuestion
from core.logging import logger

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
SPLITS_DIR = os.path.join(DATA_DIR, "splits")


def ensure_directories():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(SPLITS_DIR, exist_ok=True)


ROUND_METADATA = {
    1: {"name": "Round 1: Online Assessment (OA) / Screening", "code": "OA_SCREENING", "split_file": "round_1_oa.jsonl"},
    2: {"name": "Round 2: Core Coding & Problem Solving (DSA)", "code": "DSA_TECHNICAL_1", "split_file": "round_2_dsa.jsonl"},
    3: {"name": "Round 3: Machine Coding & Concurrency (LLD)", "code": "MACHINE_CODING_LLD", "split_file": "round_3_machine_coding.jsonl"},
    4: {"name": "Round 4: Large-Scale System Design & Scalability", "code": "SYSTEM_DESIGN_HLD", "split_file": "round_4_system_design.jsonl"},
    5: {"name": "Round 5: Behavioral, Culture & Senior Leadership", "code": "BEHAVIORAL_LEADERSHIP", "split_file": "round_5_behavioral.jsonl"},
}


def export_dataset() -> Dict[str, Any]:
    """
    Exports the entire database into structured JSONL, CSV, and round-wise splits.
    Maintains clean, versioned, portable dataset files.
    """
    ensure_directories()
    db = get_db_repository()
    logger.info("Beginning dataset maintenance export...")

    with db.get_session() as session:
        questions = session.query(InterviewQuestion).order_by(
            InterviewQuestion.company_name,
            InterviewQuestion.round_number,
            InterviewQuestion.id
        ).all()

        total_records = len(questions)
        logger.info(f"Loaded {total_records} questions from database for maintenance export.")

        jsonl_path = os.path.join(DATA_DIR, "interview_intelligence_dataset.jsonl")
        csv_path = os.path.join(DATA_DIR, "interview_intelligence_dataset.csv")

        # Open file handlers for round splits
        round_handlers = {}
        for r_num, meta in ROUND_METADATA.items():
            f_path = os.path.join(SPLITS_DIR, meta["split_file"])
            round_handlers[r_num] = open(f_path, "w", encoding="utf-8")

        round_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        company_counts = {}
        category_counts = {}
        difficulty_counts = {}

        csv_rows = []

        with open(jsonl_path, "w", encoding="utf-8") as f_jsonl:
            for q in questions:
                r_num = getattr(q, "round_number", 1) or 1
                if r_num not in round_counts:
                    r_num = 1
                round_counts[r_num] += 1

                c_name = q.company_name or "Technology Firm"
                company_counts[c_name] = company_counts.get(c_name, 0) + 1

                cat = q.question_category or "General Problem Solving"
                category_counts[cat] = category_counts.get(cat, 0) + 1

                diff = q.difficulty or "Medium"
                difficulty_counts[diff] = difficulty_counts.get(diff, 0) + 1

                r_title = getattr(q, "interview_round", None) or ROUND_METADATA[r_num]["name"]

                record = {
                    "id": q.id,
                    "company_name": c_name,
                    "company_type": getattr(q, "company_type", "ESTABLISHED"),
                    "industry": getattr(q, "industry", "Technology"),
                    "job_role": q.job_role or "General Engineering",
                    "role_family": getattr(q, "role_family", "TECH"),
                    "round_number": r_num,
                    "interview_round": r_title,
                    "round_code": ROUND_METADATA[r_num]["code"],
                    "question_text": q.question_text,
                    "question_category": cat,
                    "difficulty": diff,
                    "years_of_experience": getattr(q, "years_of_experience", 3.0),
                    "yoe_tier": getattr(q, "yoe_tier", "Mid (3-5 yrs)"),
                    "skills_tested": q.skills_tested or [],
                    "source_platform": q.source_platform or "Developer Archive",
                    "original_url": q.original_url or "https://interview-intelligence.internal",
                    "confidence_score": getattr(q, "confidence_score", 0.90),
                    "verification_status": getattr(q, "verification_status", "VERIFIED"),
                    "content_hash": q.content_hash,
                    "collection_timestamp": q.collection_timestamp.isoformat() if getattr(q, "collection_timestamp", None) else datetime.utcnow().isoformat(),
                }

                json_str = json.dumps(record, ensure_ascii=False)
                f_jsonl.write(json_str + "\n")

                # Write to round-specific split
                if r_num in round_handlers:
                    round_handlers[r_num].write(json_str + "\n")

                # Format row for CSV
                csv_rows.append({
                    "id": q.id,
                    "round_number": r_num,
                    "interview_round": r_title,
                    "company_name": c_name,
                    "job_role": q.job_role,
                    "difficulty": diff,
                    "question_category": cat,
                    "question_text": q.question_text,
                    "skills_tested": ", ".join(q.skills_tested) if q.skills_tested else "",
                    "source_platform": q.source_platform,
                    "original_url": q.original_url,
                    "confidence_score": q.confidence_score,
                    "verification_status": q.verification_status,
                })

        # Close all round split handlers
        for h in round_handlers.values():
            h.close()

        # Write CSV
        if csv_rows:
            with open(csv_path, "w", encoding="utf-8", newline="") as f_csv:
                writer = csv.DictWriter(f_csv, fieldnames=list(csv_rows[0].keys()))
                writer.writeheader()
                writer.writerows(csv_rows)

        # Write dataset metadata summary
        metadata = {
            "dataset_name": "Interview Intelligence Production Question Corpus",
            "version": "1.6.0",
            "last_maintained": datetime.utcnow().isoformat(),
            "total_questions": total_records,
            "total_companies": len(company_counts),
            "round_breakdown": {
                f"round_{r}": {
                    "name": ROUND_METADATA[r]["name"],
                    "count": count,
                    "file": f"splits/{ROUND_METADATA[r]['split_file']}",
                }
                for r, count in round_counts.items()
            },
            "top_companies": dict(sorted(company_counts.items(), key=lambda x: x[1], reverse=True)[:15]),
            "difficulty_breakdown": difficulty_counts,
            "category_breakdown": dict(sorted(category_counts.items(), key=lambda x: x[1], reverse=True)),
            "export_formats": {
                "jsonl": "data/interview_intelligence_dataset.jsonl",
                "csv": "data/interview_intelligence_dataset.csv",
                "splits_directory": "data/splits/",
            },
        }

        meta_path = os.path.join(DATA_DIR, "dataset_metadata.json")
        with open(meta_path, "w", encoding="utf-8") as f_meta:
            json.dump(metadata, f_meta, indent=2)

        logger.info(f"Dataset successfully exported and maintained! Total records: {total_records}")
        return metadata


def audit_dataset() -> Dict[str, Any]:
    """
    Performs comprehensive data quality audit across completeness, deduplication, and schema validity.
    """
    db = get_db_repository()
    issues = []
    with db.get_session() as session:
        questions = session.query(InterviewQuestion).all()
        seen_hashes = set()
        missing_fields = 0
        duplicate_hashes = 0
        invalid_rounds = 0

        for q in questions:
            if not q.question_text or len(q.question_text.strip()) < 10:
                missing_fields += 1
            if not q.company_name:
                missing_fields += 1
            if getattr(q, "round_number", 0) not in [1, 2, 3, 4, 5]:
                invalid_rounds += 1
            if q.content_hash in seen_hashes:
                duplicate_hashes += 1
            seen_hashes.add(q.content_hash)

        audit_results = {
            "total_questions_audited": len(questions),
            "duplicate_hashes": duplicate_hashes,
            "missing_critical_fields": missing_fields,
            "invalid_round_numbers": invalid_rounds,
            "health_score_pct": 100.0 if (duplicate_hashes == 0 and missing_fields == 0 and invalid_rounds == 0) else round(100.0 - ((duplicate_hashes + missing_fields + invalid_rounds) / max(len(questions), 1) * 100), 2),
            "status": "HEALTHY" if (duplicate_hashes == 0 and missing_fields == 0 and invalid_rounds == 0) else "NEEDS_REMEDIATION",
        }
        return audit_results


def main():
    parser = argparse.ArgumentParser(description="Interview Intelligence Dataset Maintenance")
    parser.add_argument("--action", choices=["export", "audit", "sync"], default="sync", help="Action to perform (export, audit, sync)")
    args = parser.parse_args()

    if args.action in ["export", "sync"]:
        print("Exporting and maintaining structured dataset...")
        meta = export_dataset()
        print(f"Dataset maintained successfully: {meta['total_questions']} questions exported across {meta['total_companies']} companies.")
        print(f"Files saved in: {DATA_DIR}")

    if args.action in ["audit", "sync"]:
        print("\nAuditing dataset quality...")
        audit = audit_dataset()
        print(f"Audit completed: Health Score = {audit['health_score_pct']}% | Status = {audit['status']} | Duplicates = {audit['duplicate_hashes']}")


if __name__ == "__main__":
    main()
