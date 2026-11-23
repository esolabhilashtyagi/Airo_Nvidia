"""
Workflow State & Job Lifecycle Tracking for Orchestration.
Tracks pipeline progress, agent heartbeat, and task dependencies.
"""

from typing import Dict, Any, Optional, List
from enum import Enum
import uuid
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
