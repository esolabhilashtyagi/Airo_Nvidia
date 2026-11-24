"""
Async Scheduler and Task Queue for executing background pipeline runs and continuous harvesting.
"""

import asyncio
from typing import Callable, Coroutine, Any, List, Dict, Optional
from datetime import datetime
from .logging import logger


class TaskScheduler:
    def __init__(self):
        self.queue: asyncio.Queue = asyncio.Queue()
        self.workers: List[asyncio.Task] = []
        self._running = False
        self._harvester_task: Optional[asyncio.Task] = None
        self._harvester_running = False
        self._harvester_stats: Dict[str, Any] = {
            "status": "STOPPED",
            "total_harvested": 0,
            "last_company": None,
            "last_role": None,
            "last_run": None,
        }

    async def add_task(self, coro_func: Callable[..., Coroutine[Any, Any, Any]], *args, **kwargs):
        await self.queue.put((coro_func, args, kwargs))

    async def start(self, num_workers: int = 2):
        self._running = True
        for i in range(num_workers):
            task = asyncio.create_task(self._worker(i))
            self.workers.append(task)
        logger.info(f"TaskScheduler started with {num_workers} async worker(s).")

    async def _worker(self, worker_id: int):
        while self._running:
            try:
                coro_func, args, kwargs = await self.queue.get()
                try:
                    await coro_func(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Task execution error in worker {worker_id}: {e}", exc_info=True)
                finally:
                    self.queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} loop encountered unexpected error: {e}")

    def start_background_harvester(self, interval_seconds: int = 60):
        """
        Launches continuous non-blocking open-web background harvesting.
        """
        if self._harvester_running and self._harvester_task and not self._harvester_task.done():
            logger.info("Background harvester is already active.")
            return

        self._harvester_running = True
        self._harvester_task = asyncio.create_task(self._harvester_loop(interval_seconds))
        self._harvester_stats["status"] = "RUNNING"
        logger.info(f"Continuous background harvester started (interval: {interval_seconds}s).")

    async def _harvester_loop(self, interval_seconds: int):
        from collectors.open_web_collector import OpenWebCollector
        from collectors.live_web_scraper import TECH_GIANTS_AND_STARTUPS
        from agents.coding_extraction_agent import CodingProblemExtractionAgent
        from core.workflow_state import workflow_state
        from database.repository import get_db_repository

        collector = OpenWebCollector()
        coding_agent = CodingProblemExtractionAgent()
        db = get_db_repository()

        tech_roles = [
            "Software Development Engineer",
            "Systems Software Engineer",
            "Backend Engineer",
            "Machine Learning Engineer",
        ]

        logger.info("Starting background harvesting loop iteration...")
        while self._harvester_running:
            try:
                for company in TECH_GIANTS_AND_STARTUPS:
                    if not self._harvester_running:
                        break
                    for role in tech_roles:
                        if not self._harvester_running:
                            break

                        cursor_page = workflow_state.get_cursor_page(company, role)
                        self._harvester_stats["last_company"] = company
                        self._harvester_stats["last_role"] = role
                        self._harvester_stats["last_run"] = datetime.utcnow().isoformat()

                        try:
                            articles = await collector.harvest_open_web(
                                company=company, role=role, page=cursor_page, max_articles=2
                            )
                            for art in articles:
                                questions = await coding_agent.extract_questions_from_full_article(
                                    art["full_text"], company=company, role=role
                                )
                                for q_text, r_num, r_name in questions:
                                    saved = db.save_interview_question(
                                        company_name=company,
                                        job_role=role,
                                        round_number=r_num,
                                        interview_round=r_name,
                                        question_text=q_text,
                                        source_platform=art.get("source_domain", "Open Web"),
                                        original_url=art.get("url", ""),
                                        source_type="scraped",
                                    )
                                    if saved:
                                        self._harvester_stats["total_harvested"] += 1
                        except Exception as e:
                            logger.debug(f"Background harvest cycle error for {company} {role}: {e}")

                        # Advance cursor to keep fresh next cycle
                        workflow_state.advance_cursor_page(company, role)
                        await asyncio.sleep(2.0)

                await asyncio.sleep(max(interval_seconds, 10))
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Background harvester loop exception: {e}")
                await asyncio.sleep(15.0)

        self._harvester_stats["status"] = "STOPPED"

    def stop_background_harvester(self):
        self._harvester_running = False
        if self._harvester_task:
            self._harvester_task.cancel()
            self._harvester_task = None
        self._harvester_stats["status"] = "STOPPED"
        logger.info("Background harvester stopped.")

    def get_harvester_status(self) -> Dict[str, Any]:
        return dict(self._harvester_stats)

    async def stop(self):
        self.stop_background_harvester()
        self._running = False
        for task in self.workers:
            task.cancel()
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()
