"""
Agent 14: Monitoring & Analytics Agent.
Tracks agent execution health, collection statistics, processing time,
Prometheus metrics, and system throughput.
"""

import time
from typing import Dict, Any
from prometheus_client import Counter, Gauge
from core.workflow_state import workflow_state, AgentStatus
from core.logging import logger

# Prometheus Metrics Definitions
ITEMS_COLLECTED_TOTAL = Counter("ii_items_collected_total", "Total raw items collected from sources")
QUESTIONS_EXTRACTED_TOTAL = Counter("ii_questions_extracted_total", "Total questions successfully extracted")
DUPLICATES_DETECTED_TOTAL = Counter("ii_duplicates_detected_total", "Total duplicate questions identified")
PIPELINE_EXECUTION_TIME_SECONDS = Gauge("ii_pipeline_execution_time_seconds", "Duration of last pipeline execution in seconds")


class MonitoringAnalyticsAgent:
    def __init__(self):
        self.name = "MonitoringAnalyticsAgent"
        workflow_state.register_agent(self.name, agent_type="OBSERVABILITY")

    def record_pipeline_metrics(self, pipeline_summary: Dict[str, Any]):
        workflow_state.update_agent_status(self.name, AgentStatus.RUNNING, current_task="Recording Prometheus metrics")
        ITEMS_COLLECTED_TOTAL.inc(pipeline_summary.get("collected", 0))
        QUESTIONS_EXTRACTED_TOTAL.inc(pipeline_summary.get("extracted", 0))
        DUPLICATES_DETECTED_TOTAL.inc(pipeline_summary.get("duplicates", 0))
        workflow_state.update_agent_status(self.name, AgentStatus.COMPLETED)
        logger.info(f"[{self.name}] Prometheus metrics updated successfully.")

    def get_system_health(self) -> Dict[str, Any]:
        return {
            "status": "HEALTHY",
            "timestamp": time.time(),
            "agents": workflow_state.get_all_agent_statuses(),
            "active_jobs_count": len(workflow_state.active_jobs),
        }
