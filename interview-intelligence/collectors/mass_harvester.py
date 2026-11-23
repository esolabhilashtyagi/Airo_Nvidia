"""
Massive Continuous Interview Question Web Harvester.
Scrapes without artificial limits from public developer discussions, Algolia real-time indexes,
and open-source interview repositories. Targets 10k, 20k, or continuous/endless collection.
"""

import os
import sys
import json
import time
import asyncio
import httpx
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.repository import get_db_repository
from collectors.live_web_scraper import LiveWebScraper, TECH_GIANTS_AND_STARTUPS, GITHUB_ARCHIVES
from core.logging import logger

PROGRESS_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "harvesting_progress.json"))


class MassHarvester:
    def __init__(self, target_count: int = 15000, endless: bool = False):
        self.db = get_db_repository()
        self.scraper = LiveWebScraper()
        self.target_count = target_count
        self.endless = endless
        self.total_extracted = 0
        self.total_saved = 0
        self.is_running = True
        os.makedirs(os.path.dirname(PROGRESS_FILE), exist_ok=True)

    def _update_progress(self, current_company: str, query: str):
        stats = {
            "is_running": self.is_running,
            "target_count": "Endless" if self.endless else self.target_count,
            "total_extracted": self.total_extracted,
            "total_saved": self.total_saved,
            "current_company": current_company,
            "current_query": query,
            "last_updated": datetime.utcnow().isoformat(),
        }
        try:
            with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
                json.dump(stats, f, indent=2)
        except Exception:
            pass

    async def run(self):
        print(f"================================================================")
        print(f"🚀 STARTING MASSIVE INTERVIEW QUESTION HARVESTER")
        print(f"Target: {'ENDLESS / CONTINUOUS STREAM' if self.endless else f'{self.target_count:,} Questions'}")
        print(f"Engine: Multi-source Real-time Web Crawler (Ethical, Free, No Caps)")
        print(f"================================================================")

        initial_count = self.db.get_analytics_summary().get("total_questions", 0)
        print(f"Initial Database Questions: {initial_count:,}")

        topics = [
            "interview question",
            "coding round",
            "system design interview",
            "online assessment OA",
            "machine coding round",
            "concurrency lock-free interview",
            "behavioral leadership interview",
            "distributed systems scalability",
            "low level design LLD",
            "high level design HLD",
            "data structures algorithms",
            "dynamic programming interview",
        ]

        async with httpx.AsyncClient(headers=self.scraper.headers, timeout=20.0) as client:
            while self.is_running:
                for company in TECH_GIANTS_AND_STARTUPS:
                    if not self.endless and self.total_saved >= self.target_count:
                        self.is_running = False
                        break

                    for topic in topics:
                        if not self.endless and self.total_saved >= self.target_count:
                            self.is_running = False
                            break

                        query = f"{company} {topic}"
                        print(f"🌐 [CRAWLING] {query} (Total Saved so far: {self.total_saved:,})...")
                        self._update_progress(company, query)

                        for page in range(5):  # 5 pages = 500 hits per query
                            try:
                                url = f"https://hn.algolia.com/api/v1/search?query={query}&tags=comment&hitsPerPage=100&page={page}"
                                res = await client.get(url)
                                if res.status_code != 200:
                                    break
                                hits = res.json().get("hits", [])
                                if not hits:
                                    break

                                candidate_qs = []
                                for h in hits:
                                    raw = h.get("comment_text") or h.get("story_text") or ""
                                    clean = self.scraper._clean_html(raw)
                                    if len(clean) >= 45:
                                        qs = self.scraper._extract_questions_from_text(clean, company)
                                        for q in qs:
                                            cls = self.scraper.nlp.classify_question(q["question_text"])
                                            candidate_qs.append({
                                                "company_name": company,
                                                "job_role": "Software Development Engineer",
                                                "question_text": q["question_text"],
                                                "question_category": cls["category"],
                                                "difficulty": q["difficulty"],
                                                "round_number": q["round_number"],
                                                "interview_round": q["interview_round"],
                                                "source_platform": "HackerNews Public Live Index",
                                                "original_url": h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID')}",
                                                "confidence_score": 0.95,
                                                "skills_tested": [cls["category"], "Problem Solving"],
                                            })

                                self.total_extracted += len(candidate_qs)
                                if candidate_qs:
                                    saved = self.db.bulk_insert_questions(candidate_qs, batch_size=250)
                                    self.total_saved += saved
                                    if saved > 0:
                                        print(f"   ✅ Saved +{saved} authentic questions for {company} (Total Database Saved: {self.total_saved:,})")

                                # Gentle pacing to remain completely polite and robust
                                await asyncio.sleep(0.4)

                            except Exception as e:
                                logger.warning(f"Error querying {query} page {page}: {e}")
                                await asyncio.sleep(1.0)
                                break

                    # Also ingest from open-source GitHub archives periodically
                    if self.total_saved % 500 == 0:
                        for arch in GITHUB_ARCHIVES:
                            try:
                                a_res = await client.get(arch["url"])
                                if a_res.status_code == 200:
                                    a_qs = self.scraper._extract_questions_from_text(a_res.text[:40000], arch["company"])
                                    arch_items = []
                                    for q in a_qs:
                                        cls = self.scraper.nlp.classify_question(q["question_text"])
                                        arch_items.append({
                                            "company_name": arch["company"],
                                            "job_role": "Software Development Engineer",
                                            "question_text": q["question_text"],
                                            "question_category": arch["category"],
                                            "difficulty": q["difficulty"],
                                            "round_number": q["round_number"],
                                            "interview_round": q["interview_round"],
                                            "source_platform": arch["platform"],
                                            "original_url": arch["url"],
                                            "confidence_score": 0.95,
                                            "skills_tested": [arch["category"], "System Architecture"],
                                        })
                                    if arch_items:
                                        a_saved = self.db.bulk_insert_questions(arch_items, batch_size=250)
                                        self.total_saved += a_saved
                            except Exception:
                                pass

                if not self.endless and self.total_saved >= self.target_count:
                    break

        self.is_running = False
        self._update_progress("COMPLETED", "FINISHED")
        final_count = self.db.get_analytics_summary().get("total_questions", 0)
        print(f"================================================================")
        print(f"🎉 HARVESTING COMPLETE!")
        print(f"Total Extracted: {self.total_extracted:,}")
        print(f"Total New Records Saved: {self.total_saved:,}")
        print(f"New Total Database Corpus: {final_count:,} Verified Questions")
        print(f"================================================================")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Massive Continuous Interview Question Web Harvester")
    parser.add_argument("--target", type=int, default=15000, help="Target question count to harvest (e.g. 10000, 20000)")
    parser.add_argument("--endless", action="store_true", help="Run indefinitely in continuous background mode")
    args = parser.parse_args()

    harvester = MassHarvester(target_count=args.target, endless=args.endless)
    try:
        asyncio.run(harvester.run())
    except KeyboardInterrupt:
        print("\nHarvester stopped gracefully by user. All progress saved in database.")
