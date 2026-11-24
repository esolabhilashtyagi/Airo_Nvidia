"""
Workflow State & Job Lifecycle Tracking for Orchestration.
Tracks pipeline progress, agent heartbeat, task dependencies,
and persistent cursor pagination across companies and roles for open-web harvesting.
"""

from typing import Dict, Any, Optional, List
from enum import Enum
import uuid
import sqlite3
import os
from datetime import datetime


class AgentStatus(str, Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PAUSED = "PAUSED"


class WorkflowState:
    def __init__(self):
        self.active_jobs: Dict[str, Dict[str, Any]] = {}
        self.agent_statuses: Dict[str, Dict[str, Any]] = {}
        self.job_history: List[Dict[str, Any]] = []
        self._cursor_cache: Dict[str, int] = {}
        self._db_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "interview_intelligence.db")
        )
        self._init_cursor_table()

    def _init_cursor_table(self):
        """Ensures the harvesting cursor table exists for persistent pagination."""
        try:
            conn = sqlite3.connect(self._db_path)
            c = conn.cursor()
            c.execute("""
                CREATE TABLE IF NOT EXISTS harvesting_cursors (
                    cursor_key TEXT PRIMARY KEY,
                    company TEXT NOT NULL,
                    role TEXT NOT NULL,
                    last_page INTEGER NOT NULL DEFAULT 1,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.commit()
            conn.close()
        except Exception:
            pass

    def get_cursor_page(self, company: str, role: str) -> int:
        """Retrieves the next page index to scrape for a given company and role."""
        key = f"{company.lower().strip()}::{role.lower().strip()}"
        if key in self._cursor_cache:
            return self._cursor_cache[key]

        try:
            conn = sqlite3.connect(self._db_path)
            c = conn.cursor()
            c.execute("SELECT last_page FROM harvesting_cursors WHERE cursor_key = ?", (key,))
            row = c.fetchone()
            conn.close()
            page = row[0] if row else 1
            self._cursor_cache[key] = page
            return page
        except Exception:
            return 1

    def advance_cursor_page(self, company: str, role: str, step: int = 1) -> int:
        """Increments the cursor page so subsequent harvest cycles fetch fresh search results."""
        current = self.get_cursor_page(company, role)
        next_page = current + step
        key = f"{company.lower().strip()}::{role.lower().strip()}"
        self._cursor_cache[key] = next_page

        try:
            conn = sqlite3.connect(self._db_path)
            c = conn.cursor()
            c.execute("""
                INSERT INTO harvesting_cursors (cursor_key, company, role, last_page, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(cursor_key) DO UPDATE SET
                    last_page = excluded.last_page,
                    updated_at = excluded.updated_at
            """, (key, company.strip(), role.strip(), next_page, datetime.utcnow().isoformat()))
            conn.commit()
            conn.close()
        except Exception:
            pass

        return next_page

    def register_agent(self, agent_name: str, agent_type: str = "DETERMINISTIC"):
        self.agent_statuses[agent_name] = {
            "name": agent_name,
            "type": agent_type,
            "status": AgentStatus.IDLE,
            "last_active": datetime.utcnow().isoformat(),
            "tasks_completed": 0,
            "tasks_failed": 0,
            "current_task": None,
        }

    def update_agent_status(
        self, agent_name: str, status: AgentStatus, current_task: Optional[str] = None, failed: bool = False
    ):
        if agent_name in self.agent_statuses:
            self.agent_statuses[agent_name]["status"] = status
            self.agent_statuses[agent_name]["last_active"] = datetime.utcnow().isoformat()
            self.agent_statuses[agent_name]["current_task"] = current_task
            if status == AgentStatus.COMPLETED:
                self.agent_statuses[agent_name]["tasks_completed"] += 1
            if failed:
                self.agent_statuses[agent_name]["tasks_failed"] += 1

    def create_job(self, source_name: str, parameters: Optional[Dict[str, Any]] = None) -> str:
        job_id = str(uuid.uuid4())
        self.active_jobs[job_id] = {
            "job_id": job_id,
            "source_name": source_name,
            "status": "RUNNING",
            "parameters": parameters or {},
            "items_collected": 0,
            "items_extracted": 0,
            "items_indexed": 0,
            "duplicates_detected": 0,
            "started_at": datetime.utcnow().isoformat(),
            "completed_at": None,
            "errors": [],
        }
        return job_id

    def update_job_progress(self, job_id: str, collected: int = 0, extracted: int = 0, indexed: int = 0, duplicates: int = 0):
        if job_id in self.active_jobs:
            job = self.active_jobs[job_id]
            job["items_collected"] += collected
            job["items_extracted"] += extracted
            job["items_indexed"] += indexed
            job["duplicates_detected"] += duplicates

    def complete_job(self, job_id: str, status: str = "COMPLETED", error: Optional[str] = None):
        if job_id in self.active_jobs:
            job = self.active_jobs[job_id]
            job["status"] = status
            job["completed_at"] = datetime.utcnow().isoformat()
            if error:
                job["errors"].append(error)
            self.job_history.append(job)

    def get_all_agent_statuses(self) -> List[Dict[str, Any]]:
        return list(self.agent_statuses.values())


workflow_state = WorkflowState()
