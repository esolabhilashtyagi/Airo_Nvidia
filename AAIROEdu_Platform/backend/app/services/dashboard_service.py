from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.assessment import AssessmentAttempt, AssessmentResult, AttemptStatus
from app.models.candidate import CandidateProfile
from app.models.interview import InterviewEvaluation, InterviewStatus, MockInterview
from app.models.module import CandidateModuleProgress, Module, ModuleProgressStatus
from app.models.question import Question, QuestionPracticeLog
from app.models.resume import Resume, ResumeAnalysis
from app.models.user import User
from app.schemas.dashboard import (
    AnalyticsResponse, DashboardMetricCard, DashboardOverviewResponse,
    ScoreHistoryItem, TopicPerformanceItem
)


class DashboardService:
    @staticmethod
    async def get_overview(
        db: AsyncSession,
        candidate_profile: CandidateProfile,
        user: User
    ) -> DashboardOverviewResponse:
        # 1. Fetch latest resume score
        res_q = (
            select(ResumeAnalysis.overall_score)
            .join(Resume, ResumeAnalysis.resume_id == Resume.id)
            .where(
                Resume.candidate_profile_id == candidate_profile.id,
                ResumeAnalysis.status == "analysis_completed",
                ResumeAnalysis.analysis_provider.is_not(None),
            )
            .order_by(ResumeAnalysis.created_at.desc())
        )
        res_res = await db.execute(res_q)
        latest_resume_score = res_res.scalars().first() or 0.0

        # 2. Fetch completed modules count
        mod_q = select(func.count(CandidateModuleProgress.id)).where(
            CandidateModuleProgress.candidate_profile_id == candidate_profile.id,
            CandidateModuleProgress.status == ModuleProgressStatus.COMPLETED
        )
        mod_res = await db.execute(mod_q)
        completed_modules = mod_res.scalar_one()

        # 3. Fetch completed tests count and average score
        test_q = (
            select(func.count(AssessmentResult.id), func.avg(AssessmentResult.percentage))
            .join(AssessmentAttempt, AssessmentResult.assessment_attempt_id == AssessmentAttempt.id)
            .where(AssessmentAttempt.candidate_profile_id == candidate_profile.id)
        )
        test_res = await db.execute(test_q)
        tests_count, avg_test_score = test_res.one()
        tests_completed = tests_count or 0
        avg_score = round(float(avg_test_score or 0.0), 1)

        # 4. Fetch completed mock interviews count
        int_q = select(func.count(MockInterview.id)).where(
            MockInterview.candidate_profile_id == candidate_profile.id,
            MockInterview.status == InterviewStatus.COMPLETED
        )
        int_res = await db.execute(int_q)
        mock_interviews_completed = int_res.scalar_one()

        # 5. Explainable Interview Readiness Calculation
        readiness_score = candidate_profile.interview_readiness_score
        if readiness_score == 0.0:
            # Baseline calculation
            score = 30.0 if candidate_profile.onboarding_completed else 10.0
            if latest_resume_score > 0:
                score += latest_resume_score * 0.25
            if tests_completed > 0:
                score += min(tests_completed * 8.0, 20.0)
            if mock_interviews_completed > 0:
                score += min(mock_interviews_completed * 10.0, 25.0)
            readiness_score = round(min(score, 100.0), 1)

        readiness_factors = {
            "onboarding_weight": "15% (Profile Completeness)",
            "resume_alignment_weight": "25% (Resume Evaluation)",
            "assessment_proficiency_weight": "30% (Validated Knowledge)",
            "interview_simulation_weight": "30% (Mock Interview Articulation)"
        }

        # Cards
        metrics = [
            DashboardMetricCard(
                title="Interview Readiness",
                value=f"{readiness_score}%",
                change_text="Explainable multi-factor score",
                change_type="positive" if readiness_score >= 70 else "neutral",
                icon="Award"
            ),
            DashboardMetricCard(
                title="Resume Score",
                value=f"{round(latest_resume_score, 1)}/100" if latest_resume_score > 0 else "Pending",
                change_text="AI Rubric Analysis" if latest_resume_score > 0 else "Upload resume to score",
                change_type="positive" if latest_resume_score >= 75 else "neutral",
                icon="FileText"
            ),
            DashboardMetricCard(
                title="Tests Completed",
                value=tests_completed,
                change_text=f"Avg Score: {avg_score}%" if tests_completed > 0 else "No assessments taken yet",
                change_type="positive" if tests_completed > 0 else "neutral",
                icon="CheckCircle2"
            ),
            DashboardMetricCard(
                title="Mock Interviews",
                value=mock_interviews_completed,
                change_text="Completed sessions" if mock_interviews_completed > 0 else "Ready for session 1",
                change_type="positive" if mock_interviews_completed > 0 else "neutral",
                icon="Video"
            )
        ]

        recent_activity = []
        if latest_resume_score > 0:
            recent_activity.append({
                "action": "Resume Analyzed",
                "detail": f"Overall Score: {latest_resume_score}%",
                "timestamp": "Recently"
            })
        if tests_completed > 0:
            recent_activity.append({
                "action": "Assessment Completed",
                "detail": f"Scored {avg_score}% on latest assessment",
                "timestamp": "Recently"
            })
        if mock_interviews_completed > 0:
            recent_activity.append({
                "action": "Mock Interview Concluded",
                "detail": f"Completed {candidate_profile.target_role or 'Technical'} round",
                "timestamp": "Recently"
            })

        recommended_actions = [
            {"title": "Review Skill Gap Analysis", "link": "/coach", "category": "Coach"},
            {"title": "Practice 5 Centralized Questions", "link": "/question-bank", "category": "Practice"},
            {"title": "Start Timed Assessment", "link": "/testing", "category": "Assessment"}
        ]

        industry_name = candidate_profile.industry.name if candidate_profile.industry else "General Industry"

        return DashboardOverviewResponse(
            candidate_name=user.full_name,
            target_role=candidate_profile.target_role,
            industry_name=industry_name,
            interview_readiness_score=readiness_score,
            readiness_factors=readiness_factors,
            metrics=metrics,
            recent_activity=recent_activity,
            recommended_actions=recommended_actions
        )

    @staticmethod
    async def get_analytics(
        db: AsyncSession,
        candidate_profile_id: Any
    ) -> AnalyticsResponse:
        # Practice activity is based on persisted events in the last seven days.
        prac_q = select(func.count(QuestionPracticeLog.id)).where(
            QuestionPracticeLog.candidate_profile_id == candidate_profile_id
        )
        prac_res = await db.execute(prac_q)
        total_practice = prac_res.scalar_one() or 0
        today = datetime.now(timezone.utc).date()
        weekly_activity = [{"day": (today - timedelta(days=offset)).strftime("%a"), "date": (today - timedelta(days=offset)).isoformat(), "questions": 0, "minutes": None} for offset in reversed(range(7))]
        activity_by_date = {item["date"]: item for item in weekly_activity}
        practice_dates = await db.execute(select(QuestionPracticeLog.created_at).where(
            QuestionPracticeLog.candidate_profile_id == candidate_profile_id,
            QuestionPracticeLog.created_at >= datetime.combine(today - timedelta(days=6), datetime.min.time(), tzinfo=timezone.utc),
        ))
        for (created_at,) in practice_dates.all():
            if created_at:
                key = created_at.astimezone(timezone.utc).date().isoformat()
                if key in activity_by_date:
                    activity_by_date[key]["questions"] += 1

        # 2. Score History
        score_history: List[ScoreHistoryItem] = []

        # Assessment results
        res_q = (
            select(AssessmentResult.percentage, AssessmentAttempt.completed_at)
            .join(AssessmentAttempt, AssessmentResult.assessment_attempt_id == AssessmentAttempt.id)
            .where(AssessmentAttempt.candidate_profile_id == candidate_profile_id)
            .order_by(AssessmentAttempt.completed_at.asc())
        )
        res_results = await db.execute(res_q)
        for pct, dt in res_results.all():
            if pct is None:
                continue
            date_str = dt.strftime("%b %d") if dt else "Recent"
            score_history.append(ScoreHistoryItem(date=date_str, score=pct, type="assessment"))

        # Interview evaluations
        eval_q = (
            select(InterviewEvaluation.overall_score, MockInterview.completed_at)
            .join(MockInterview, InterviewEvaluation.mock_interview_id == MockInterview.id)
            .where(MockInterview.candidate_profile_id == candidate_profile_id)
            .order_by(MockInterview.completed_at.asc())
        )
        eval_results = await db.execute(eval_q)
        for osc, dt in eval_results.all():
            if osc is None:
                continue
            date_str = dt.strftime("%b %d") if dt else "Recent"
            score_history.append(ScoreHistoryItem(date=date_str, score=osc, type="mock_interview"))

        topic_rows = await db.execute(select(
            Question.topic, func.avg(QuestionPracticeLog.score_percentage), func.count(QuestionPracticeLog.id)
        ).join(Question, Question.id == QuestionPracticeLog.question_id).where(
            QuestionPracticeLog.candidate_profile_id == candidate_profile_id,
            QuestionPracticeLog.score_percentage.is_not(None),
        ).group_by(Question.topic).order_by(func.count(QuestionPracticeLog.id).desc()).limit(12))
        topic_performance = [TopicPerformanceItem(topic=topic or "Uncategorized", proficiency=round(float(avg), 1) if avg is not None else None, total_questions=count) for topic, avg, count in topic_rows.all()]

        # 4. Module completion percentage
        mod_q = select(func.avg(CandidateModuleProgress.completion_percentage)).where(
            CandidateModuleProgress.candidate_profile_id == candidate_profile_id
        )
        mod_res = await db.execute(mod_q)
        avg_mod = mod_res.scalar_one() or 0.0

        return AnalyticsResponse(
            weekly_activity=weekly_activity,
            score_history=score_history,
            topic_performance=topic_performance,
            module_completion_percentage=round(float(avg_mod), 1),
            total_practice_count=total_practice
        )
