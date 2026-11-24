from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class DashboardMetricCard(BaseModel):
    title: str
    value: Any
    change_text: Optional[str] = None
    change_type: Optional[str] = "neutral" # "positive", "negative", "neutral"
    icon: str


class ScoreHistoryItem(BaseModel):
    date: str
    score: Optional[float] = None
    type: str # "assessment" or "mock_interview"


class TopicPerformanceItem(BaseModel):
    topic: str
    proficiency: Optional[float] = None # 0 - 100; null if no evaluated responses
    total_questions: int


class DashboardOverviewResponse(BaseModel):
    candidate_name: str
    target_role: Optional[str] = None
    industry_name: Optional[str] = None
    interview_readiness_score: float = 0.0
    readiness_factors: Dict[str, Any] = {}
    metrics: List[DashboardMetricCard] = []
    recent_activity: List[Dict[str, Any]] = []
    recommended_actions: List[Dict[str, Any]] = []


class AnalyticsResponse(BaseModel):
    weekly_activity: List[Dict[str, Any]] = []
    score_history: List[ScoreHistoryItem] = []
    topic_performance: List[TopicPerformanceItem] = []
    module_completion_percentage: float = 0.0
    total_practice_count: int = 0
