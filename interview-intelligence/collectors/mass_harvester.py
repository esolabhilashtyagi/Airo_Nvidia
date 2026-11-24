"""
Massive Continuous Interview Question Web Harvester.
Harvests authentic interview questions across unlimited websites (Medium, Substack,
Blind, Dev.to, personal engineering blogs, etc.) using:
1. Multi-Engine Search Discovery (SearXNG / Multi-Engine with negative dorks)
2. Universal Main-Body Extraction via curl_cffi and trafilatura
3. Nemotron / LLM Extraction Gate for atomic question decomposition
4. Persistent cursor pagination across all tech companies and roles
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
from collectors.live_web_scraper import LiveWebScraper, TECH_GIANTS_AND_STARTUPS
from collectors.open_web_collector import OpenWebCollector
from agents.coding_extraction_agent import CodingProblemExtractionAgent
from core.workflow_state import workflow_state
from core.logging import logger

PROGRESS_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "harvesting_progress.json"))


class MassHarvester:
    def __init__(self, target_count: int = 15000, endless: bool = False):
        self.db = get_db_repository()
        self.scraper = LiveWebScraper()
        self.open_collector = OpenWebCollector()
        self.coding_agent = CodingProblemExtractionAgent()
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
        print(f"🚀 STARTING OPEN-WEB INTERVIEW QUESTION HARVESTER")
        print(f"Target: {'ENDLESS / CONTINUOUS STREAM' if self.endless else f'{self.target_count:,} Questions'}")
        print(f"Pipeline: SearXNG -> trafilatura -> Nemotron Extraction Gate")
        print(f"================================================================")

        initial_count = self.db.get_analytics_summary().get("total_questions", 0)
        print(f"Initial Database Questions: {initial_count:,}")

        roles = [
            "Software Development Engineer",
            "Systems Software Engineer",
            "Backend Engineer",
            "Machine Learning Engineer",
            "Senior Product Manager",
        ]

        while self.is_running:
            for company in TECH_GIANTS_AND_STARTUPS:
                if not self.endless and self.total_saved >= self.target_count:
                    self.is_running = False
                    break

                for role in roles:
                    if not self.endless and self.total_saved >= self.target_count:
                        self.is_running = False
                        break

                    cursor_page = workflow_state.get_cursor_page(company, role)
                    print(f"🌐 [OPEN WEB HARVEST] {company} | {role} (Page: {cursor_page}, Total Saved: {self.total_saved:,})...")
                    self._update_progress(company, f"{company} {role} page {cursor_page}")

                    try:
                        # 1. Harvest clean full articles across open web
                        articles = await self.open_collector.harvest_open_web(
                            company=company,
                            role=role,
                            page=cursor_page,
                            max_articles=8,
                        )
                        workflow_state.advance_cursor_page(company, role, 1)

                        candidate_qs = []
                        # 2. Gate articles through Nemotron
                        for art in articles:
                            qs = await self.coding_agent.extract_questions_from_full_article(
                                article_content=art["content"],
                                company=company,
                                role=role,
                                url=art["url"],
                                platform=art["platform"],
                            )
                            candidate_qs.extend(qs)

                        self.total_extracted += len(candidate_qs)
                        if candidate_qs:
                            saved = self.db.bulk_insert_questions(candidate_qs, batch_size=250)
                            self.total_saved += saved
                            if saved > 0:
                                print(f"   ✅ Saved +{saved} authentic questions for {company} (Total Database Saved: {self.total_saved:,})")

                        # Gentle pacing
                        await asyncio.sleep(0.5)

                    except Exception as e:
                        logger.warning(f"Error harvesting open web for {company} ({role}): {e}")
                        await asyncio.sleep(1.0)

        print(f"🎉 Harvester finished! Extracted: {self.total_extracted:,} | Saved into DB: {self.total_saved:,}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Mass Open Web Question Harvester")
    parser.add_argument("--count", type=int, default=5000, help="Target questions count")
    parser.add_argument("--endless", action="store_true", help="Run in continuous streaming mode")
    args = parser.parse_args()

    harvester = MassHarvester(target_count=args.count, endless=args.endless)
    asyncio.run(harvester.run())
