from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import AssessmentAttempt, AssessmentResult
from app.models.candidate import CandidateProfile
from app.models.interview import InterviewEvaluation, InterviewStatus, MockInterview
from app.models.module import CandidateModuleProgress
from app.models.question import Question, QuestionPracticeLog
from app.models.resume import Resume, ResumeAnalysis
from app.models.user import User
from app.schemas.dashboard import (
    AnalyticsResponse, DashboardMetricCard, DashboardOverviewResponse,
    ScoreHistoryItem, TopicPerformanceItem
)
from app.services.candidate_service import CandidateService


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
        latest_resume_score_value = res_res.scalars().first()
        latest_resume_score = float(latest_resume_score_value) if latest_resume_score_value is not None else 0.0

        # 2. Fetch completed tests count and average score
        test_q = (
            select(func.count(AssessmentResult.id), func.avg(AssessmentResult.percentage))
            .join(AssessmentAttempt, AssessmentResult.assessment_attempt_id == AssessmentAttempt.id)
            .where(AssessmentAttempt.candidate_profile_id == candidate_profile.id)
        )
        test_res = await db.execute(test_q)
        tests_count, avg_test_score = test_res.one()
        tests_completed = tests_count or 0
        avg_score = round(float(avg_test_score or 0.0), 1)

        # 3. Fetch completed mock interview count and validated evaluation average.
        int_q = select(func.count(MockInterview.id), func.avg(InterviewEvaluation.overall_score)).outerjoin(
            InterviewEvaluation, InterviewEvaluation.mock_interview_id == MockInterview.id
        ).where(
            MockInterview.candidate_profile_id == candidate_profile.id,
            MockInterview.status == InterviewStatus.COMPLETED
        )
        int_res = await db.execute(int_q)
        mock_interviews_completed, avg_interview_score = int_res.one()
        mock_interviews_completed = mock_interviews_completed or 0
        avg_interview_score = round(float(avg_interview_score), 1) if avg_interview_score is not None else None

        # 4. Recompute the transparent estimate from current evidence. Missing
        # evidence is excluded from the denominator rather than treated as 0.
        profile_score = round(min(CandidateService.calculate_readiness_score(candidate_profile) / 75 * 100, 100), 1)
        readiness_score, readiness_factors = DashboardService._readiness_estimate(
            profile_score=profile_score,
            resume_score=latest_resume_score if latest_resume_score_value is not None else None,
            assessment_score=avg_score if tests_completed > 0 else None,
            interview_score=avg_interview_score if mock_interviews_completed > 0 else None,
        )

        # Cards
        metrics = [
            DashboardMetricCard(
                title="Interview Readiness",
                value=f"{readiness_score}%",
                change_text=f"{readiness_factors['coverage_percent']}% evidence coverage",
                change_type="positive" if readiness_score >= 70 else "neutral",
                icon="Award"
            ),
            DashboardMetricCard(
                title="Resume Score",
                value=f"{round(latest_resume_score, 1)}%" if latest_resume_score_value is not None else "Pending",
                change_text="Completed resume analysis" if latest_resume_score_value is not None else "Upload resume to score",
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
        if latest_resume_score_value is not None:
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
        score_events: list[tuple[datetime | None, ScoreHistoryItem]] = []

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
            timestamp = dt.replace(tzinfo=timezone.utc) if dt and dt.tzinfo is None else dt
            score_events.append((dt, ScoreHistoryItem(
                date=dt.strftime("%b %d %H:%M") if dt else "Time unknown",
                timestamp=timestamp,
                score=pct,
                type="assessment",
            )))

        # Interview evaluations
        eval_q = (
            select(InterviewEvaluation.overall_score, MockInterview.completed_at)
            .join(MockInterview, InterviewEvaluation.mock_interview_id == MockInterview.id)
            .where(
                MockInterview.candidate_profile_id == candidate_profile_id,
                MockInterview.status == InterviewStatus.COMPLETED,
            )
            .order_by(MockInterview.completed_at.asc())
        )
        eval_results = await db.execute(eval_q)
        for osc, dt in eval_results.all():
            if osc is None:
                continue
            timestamp = dt.replace(tzinfo=timezone.utc) if dt and dt.tzinfo is None else dt
            score_events.append((dt, ScoreHistoryItem(
                date=dt.strftime("%b %d %H:%M") if dt else "Time unknown",
                timestamp=timestamp,
                score=osc,
                type="mock_interview",
            )))

        # Merge the separate source queries into one chronological timeline.
        score_events.sort(key=lambda event: (
            event[0] is None,
            (event[0].replace(tzinfo=timezone.utc) if event[0] and event[0].tzinfo is None else event[0].astimezone(timezone.utc))
            if event[0] else datetime.max.replace(tzinfo=timezone.utc),
        ))
        score_history = []
        for _, event in score_events:
            score_history.append(event)

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

    @staticmethod
    def _readiness_estimate(
        *,
        profile_score: float,
        resume_score: float | None,
        assessment_score: float | None,
        interview_score: float | None,
    ) -> tuple[float, dict[str, Any]]:
        def bounded(value: float | None) -> float | None:
            return round(min(max(float(value), 0.0), 100.0), 1) if value is not None else None

        components = {
            "profile_baseline": ("Profile completeness", 15, bounded(profile_score), "Industry, target role, skills, education, preferences, and target companies."),
            "resume_alignment": ("Resume structure and analysis", 25, bounded(resume_score), "Latest completed resume analysis."),
            "assessment_proficiency": ("Assessment performance", 30, bounded(assessment_score), "Average score across completed assessments."),
            "interview_delivery": ("Mock interview performance", 30, bounded(interview_score), "Average score across completed mock interview evaluations."),
        }
        available_weight = sum(weight for _, weight, score, _ in components.values() if score is not None)
        weighted_score = sum(weight * score for _, weight, score, _ in components.values() if score is not None)
        estimate = round(weighted_score / available_weight, 1) if available_weight else 0.0
        factors: dict[str, Any] = {"coverage_percent": available_weight, "components": {}}
        for key, (label, weight, score, description) in components.items():
            factors["components"][key] = {
                "label": label,
                "weight_percent": weight,
                "score_percent": score,
                "included": score is not None,
                "description": description,
            }
        return estimate, factors
