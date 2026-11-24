

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
from database.models import InterviewQuestion, QuestionEmbedding
from agents.deduplication_agent import canonicalize_text, calculate_containment_similarity
from models.fallback_models import normalize_canonical_role, STOP_WORDS
from models.embedding_model import LocalEmbeddingModel
from core.logging import logger
import uuid
import re

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


def purge_noise_and_junk(dry_run: bool = False) -> Dict[str, Any]:
    """
    Purges synthetic clones, HTML fragments, blog headlines, HackerNews comment noise, and broken categories.
    """
    db = get_db_repository()
    purged_ids = []
    reasons = {}

    with db.get_session() as session:
        questions = session.query(InterviewQuestion).all()
        for q in questions:
            text = q.question_text or ""
            cat = q.question_category or ""
            url = (q.original_url or "").lower()
            plat = q.source_platform or ""

            is_junk = False
            reason = ""

            # Check HackerNews comments / item?id=
            if any(hn in url for hn in ["news.ycombinator.com", "item?id=", "algolia.com"]):
                is_junk = True
                reason = "HackerNews comment URL"
            elif plat in ["Developer Technical Discussion", "HackerNews", "HackerNews Public Live Index"]:
                is_junk = True
                reason = f"Unwanted platform: {plat}"
            # Check HTML noise
            elif any(tag in text.lower() for tag in ["<details", "<summary", "<div", "<span", "<table", "<tr", "<td"]):
                is_junk = True
                reason = "HTML tags in question text"
            # Check broken categories
            elif cat.endswith(" Domain") or cat == "Domain":
                is_junk = True
                reason = f"Broken category '{cat}'"
            # Check length
            elif len(text.split()) < 10 or len(text.strip()) < 40:
                is_junk = True
                reason = "Question too short (<10 words)"
            # Check conversational artifacts, blog headlines, or rants
            elif (
                text.startswith("Deconstructed:")
                or text.startswith("Maybe these are the types")
                or text.startswith("Then erase it and try")
                or text.startswith("Front end engineer and your stack")
                or text.startswith("Key Insights for Improving UX")
                or "Interview Questions for Growth from" in text
                or "would you tolerate male-only" in text.lower()
            ):
                is_junk = True
                reason = "Blog headline or forum debate noise"

            if is_junk:
                purged_ids.append(q.id)
                reasons[q.id] = reason
                if not dry_run:
                    # Delete embedding
                    session.query(QuestionEmbedding).filter(QuestionEmbedding.question_id == q.id).delete()
                    # Delete question
                    session.delete(q)

        if not dry_run and purged_ids:
            session.commit()
            logger.info(f"Purged {len(purged_ids)} junk questions and embeddings.")

    return {
        "purged_count": len(purged_ids),
        "dry_run": dry_run,
        "sample_purged": list(reasons.items())[:10],
    }


def normalize_dataset_roles_and_rounds(dry_run: bool = False) -> Dict[str, Any]:
    """
    Standardizes job role casing across canonical titles and syncs round numbers
    for multi-round experiences (e.g. sample_google_sde2).
    """
    db = get_db_repository()
    updated_count = 0

    with db.get_session() as session:
        questions = session.query(InterviewQuestion).all()
        for q in questions:
            # 1. Normalize role casing
            norm_role = normalize_canonical_role(q.job_role)
            if q.job_role != norm_role:
                q.job_role = norm_role
                updated_count += 1

            # 2. Fix round sync on sample_google_sde2
            if q.original_url and "sample_google_sde2" in q.original_url:
                t_low = (q.question_text or "").lower()
                if "rate limiter" in t_low:
                    q.round_number = 4
                    q.interview_round = "Round 4: Large-Scale System Design"
                    q.question_category = "System Design"
                    updated_count += 1
                elif "disagreement" in t_low or "conflict" in t_low:
                    q.round_number = 5
                    q.interview_round = "Round 5: Behavioral & Leadership"
                    q.question_category = "HR and Behavioral"
                    updated_count += 1
                elif "k-group" in t_low:
                    q.round_number = 2
                    q.interview_round = "Round 2: Core Coding & Problem Solving (DSA)"
                    q.question_category = "Linked Lists"
                    updated_count += 1
                elif "subarray" in t_low:
                    q.round_number = 1
                    q.interview_round = "Round 1: Online Assessment (OA)"
                    q.question_category = "Arrays and Strings"
                    updated_count += 1
                elif "lowest common ancestor" in t_low:
                    q.round_number = 1
                    q.interview_round = "Round 1: Online Assessment (OA)"
                    q.question_category = "Trees and Graphs"
                    updated_count += 1

            # 3. Fix Senior Product Manager categories
            if q.job_role == "Senior Product Manager" and q.question_category == "Data Structures and Algorithms":
                t_low = (q.question_text or "").lower()
                if "collaborative editing" in t_low or "docs" in t_low:
                    q.question_category = "System Design"
                    updated_count += 1
                elif any(k in t_low for k in ["checkout", "monetization", "strategy", "respond to generative ai"]):
                    q.question_category = "Product Management"
                    updated_count += 1

        if not dry_run and updated_count > 0:
            session.commit()
            logger.info(f"Normalized roles and rounds for {updated_count} questions.")

    return {"updated_count": updated_count, "dry_run": dry_run}


def deduplicate_dataset(dry_run: bool = False) -> Dict[str, Any]:
    """
    Identifies and collapses duplicate questions using:
    1. Exact canonical <NUM> unit masking
    2. Containment token similarity >= 0.70 (collapses short summaries into full problems)
    """
    db = get_db_repository()
    duplicates_to_delete = []

    with db.get_session() as session:
        questions = session.query(InterviewQuestion).all()

        # Step 1: Exact canonical hash groups
        canonical_groups: Dict[tuple, List[InterviewQuestion]] = {}
        for q in questions:
            norm_key = (
                (q.company_name or "").lower().strip(),
                canonicalize_text(q.question_text or ""),
            )
            canonical_groups.setdefault(norm_key, []).append(q)

        for norm_key, group in canonical_groups.items():
            if len(group) > 1:
                # Keep highest confidence or longest text
                sorted_group = sorted(
                    group,
                    key=lambda x: (getattr(x, "confidence_score", 0.0) or 0.0, len(x.question_text or "")),
                    reverse=True,
                )
                keep_item = sorted_group[0]
                remove_items = sorted_group[1:]
                for rem in remove_items:
                    if rem.id not in duplicates_to_delete:
                        duplicates_to_delete.append(rem.id)

        # Step 2: Containment similarity (collapses brief summaries like rate limiter or tech lead disagreement)
        questions_by_company: Dict[str, List[InterviewQuestion]] = {}
        for q in questions:
            if q.id not in duplicates_to_delete:
                c_name = (q.company_name or "").lower().strip()
                questions_by_company.setdefault(c_name, []).append(q)

        for c_name, comp_questions in questions_by_company.items():
            # Sort longest to shortest so we always keep the richer problem statement
            comp_questions.sort(key=lambda x: len(x.question_text or ""), reverse=True)
            for i in range(len(comp_questions)):
                q1 = comp_questions[i]
                if q1.id in duplicates_to_delete:
                    continue
                for j in range(i + 1, len(comp_questions)):
                    q2 = comp_questions[j]
                    if q2.id in duplicates_to_delete:
                        continue
                    containment = calculate_containment_similarity(q1.question_text, q2.question_text)
                    if containment >= 0.70:
                        duplicates_to_delete.append(q2.id)

        if not dry_run and duplicates_to_delete:
            for d_id in duplicates_to_delete:
                session.query(QuestionEmbedding).filter(QuestionEmbedding.question_id == d_id).delete()
                session.query(InterviewQuestion).filter(InterviewQuestion.id == d_id).delete()
            session.commit()
            logger.info(f"Deduplicated {len(duplicates_to_delete)} duplicate questions.")

    return {
        "duplicate_count": len(duplicates_to_delete),
        "dry_run": dry_run,
    }


def rebuild_or_verify_embeddings() -> Dict[str, Any]:
    """
    Verifies that every active interview question has an associated embedding vector.
    Rebuilds any missing embeddings using LocalEmbeddingModel.
    """
    db = get_db_repository()
    embedder = LocalEmbeddingModel()
    created_count = 0

    with db.get_session() as session:
        questions = session.query(InterviewQuestion).all()
        existing_embeddings = {
            e.question_id for e in session.query(QuestionEmbedding.question_id).all()
        }

        for q in questions:
            if q.id not in existing_embeddings:
                vec = embedder.generate_embedding(q.question_text)
                emb_entry = QuestionEmbedding(
                    id=str(uuid.uuid4()),
                    question_id=q.id,
                    model_version=embedder.model_name,
                    embedding_vector=vec,
                    created_at=datetime.utcnow(),
                )
                session.add(emb_entry)
                created_count += 1

        if created_count > 0:
            session.commit()
            logger.info(f"Generated {created_count} missing question embeddings.")

        total_questions = len(questions)
        total_embeddings = session.query(QuestionEmbedding).count()

    return {
        "total_questions": total_questions,
        "total_embeddings": total_embeddings,
        "newly_generated": created_count,
    }


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
    parser.add_argument(
        "--action",
        choices=["export", "audit", "sync", "purge", "deduplicate", "rebuild-embeddings", "full-maintenance"],
        default="sync",
        help="Action to perform",
    )
    parser.add_argument("--dry-run", action="store_true", help="Perform checks without deleting records")
    args = parser.parse_args()

    if args.action in ["purge", "full-maintenance"]:
        print("\n🧹 Purging HTML noise, broken categories, HackerNews comments, and non-question fragments...")
        p_res = purge_noise_and_junk(dry_run=args.dry_run)
        print(f"Purge complete: {p_res['purged_count']} items {'flagged' if args.dry_run else 'purged'}.")

    if args.action in ["full-maintenance", "sync"]:
        print("\n🏷️ Normalizing canonical roles and synchronizing multi-round numbers...")
        n_res = normalize_dataset_roles_and_rounds(dry_run=args.dry_run)
        print(f"Normalization complete: {n_res['updated_count']} questions updated.")

    if args.action in ["deduplicate", "full-maintenance"]:
        print("\n🔍 Running canonical <NUM> and containment token deduplication...")
        d_res = deduplicate_dataset(dry_run=args.dry_run)
        print(f"Deduplication complete: {d_res['duplicate_count']} duplicates {'flagged' if args.dry_run else 'removed'}.")

    if args.action in ["rebuild-embeddings", "full-maintenance"]:
        print("\n🧠 Verifying and rebuilding missing vector embeddings...")
        e_res = rebuild_or_verify_embeddings()
        print(f"Embeddings: {e_res['total_embeddings']}/{e_res['total_questions']} present, {e_res['newly_generated']} generated.")

    if args.action in ["export", "sync", "full-maintenance"]:
        print("\n📦 Exporting and maintaining structured dataset...")
        meta = export_dataset()
        print(f"Dataset maintained: {meta['total_questions']} questions exported across {meta['total_companies']} companies.")
        print(f"Files saved in: {DATA_DIR}")

    if args.action in ["audit", "sync", "full-maintenance"]:
        print("\n🩺 Auditing dataset quality...")
        audit = audit_dataset()
        print(f"Audit completed: Health Score = {audit['health_score_pct']}% | Status = {audit['status']} | Duplicates = {audit['duplicate_hashes']}")


if __name__ == "__main__":
    main()
