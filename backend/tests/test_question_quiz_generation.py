from types import SimpleNamespace
from unittest.mock import AsyncMock
import operator
import uuid

import pytest
from fastapi import HTTPException

from app.models.assessment import Assessment, AssessmentAttempt, AssessmentQuestion, AttemptStatus
from app.models.candidate import CandidateProfile
from app.models.question import ApprovalStatus, DifficultyLevel, Question, QuestionPracticeLog, QuestionType
from app.services.assessment_service import AssessmentService, GeneratedAssessmentQuestion
from app.services.question_service import QuestionService


class Rows:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows

    def scalars(self):
        return self


class FakeDB:
    """Persist ORM objects/defaults and resolve links for the real start service.

    Bank/history filtering is exercised against PostgreSQL in the API tests;
    this harness only supplies empty bank/history and persisted session queries.
    """
    def __init__(self):
        self.profile = SimpleNamespace(
            id=uuid.uuid4(), user_id=uuid.uuid4(), industry_id=uuid.uuid4(),
            industry=SimpleNamespace(name="Information Technology"),
            target_role="Software Engineer", total_experience_months=24,
            key_skills=["Python", "PostgreSQL"],
        )
        self.records = {model: {} for model in (Assessment, AssessmentAttempt, AssessmentQuestion, Question)}
        self.pending = []
        self.commits = 0

    async def get(self, model, record_id, **_kwargs):
        if model is CandidateProfile:
            return self.profile if record_id == self.profile.id else None
        return self.records[model].get(record_id)

    def add(self, record):
        assert type(record) in self.records
        self.pending.append(record)

    async def flush(self):
        while self.pending:
            record = self.pending.pop(0)
            for column in record.__table__.columns:
                if getattr(record, column.key) is None and column.default is not None:
                    default = column.default
                    setattr(record, column.key, default.arg(None) if default.is_callable else default.arg)
            if isinstance(record, Assessment):
                assert record.candidate_profile_id == self.profile.id
                assert record.industry_id == self.profile.industry_id
            elif isinstance(record, Question):
                assert record.industry_id == self.profile.industry_id
            elif isinstance(record, AssessmentQuestion):
                record.assessment = self.records[Assessment][record.assessment_id]
                record.question = self.records[Question][record.question_id]
            elif isinstance(record, AssessmentAttempt):
                record.assessment = self.records[Assessment][record.assessment_id]
                assert record.candidate_profile_id == record.assessment.candidate_profile_id
            self.records[type(record)][record.id] = record

    async def commit(self):
        await self.flush()
        self.commits += 1

    def _select(self, query):
        model = query.column_descriptions[0]["entity"]
        if model in (Question, QuestionPracticeLog):
            return []  # No seeded bank/history; generated drafts are never bank content.
        assert model in (Assessment, AssessmentAttempt, AssessmentQuestion)
        rows = list(self.records[model].values())
        for condition in query._where_criteria:
            assert condition.operator is operator.eq
            rows = [row for row in rows if getattr(row, condition.left.key) == condition.right.value]
        if model is AssessmentQuestion:
            rows.sort(key=lambda row: row.order_index)
        return rows

    async def scalar(self, query):
        rows = self._select(query)
        assert len(rows) <= 1
        return rows[0] if rows else None

    async def scalars(self, query):
        return Rows(self._select(query))

    async def execute(self, query):
        return Rows(self._select(query))


def generated_questions(count):
    return [GeneratedAssessmentQuestion(
        question_type=QuestionType.SHORT_ANSWER, difficulty=DifficultyLevel.BEGINNER,
        question_text=f"Explain a practical {index} use of PostgreSQL transactions.",
        expected_answer="A transaction groups database operations atomically.",
        explanation="Atomicity prevents partial changes.",
        evaluation_rubric={"concepts": ["atomicity"]},
    ) for index in range(1, count + 1)]


@pytest.mark.asyncio
async def test_quiz_uses_validated_ai_questions_and_marks_provenance(monkeypatch):
    generator = AsyncMock(return_value=generated_questions(2))
    monkeypatch.setattr(AssessmentService, "generate_assessment_questions", generator)
    db = FakeDB()

    result = await QuestionService.generate_quiz(db, db.profile.id, "PostgreSQL", 2)

    assert len(result["questions"]) == result["generated_count"] == 2
    assert all(item["source_provenance"] == "ai_generated_unreviewed" for item in result["questions"])
    assert all(item["expected_answer"] is None for item in result["questions"])
    assert result["understanding_percentage"] is None
    assert result["suggested_difficulty"] == "beginner"
    assert result["sample_count"] == 0
    ids = {uuid.UUID(item["id"]) for item in result["questions"]}
    assert ids == set(db.records[Question])
    assessment = db.records[Assessment][uuid.UUID(result["assessment_id"])]
    attempt = db.records[AssessmentAttempt][uuid.UUID(result["attempt_id"])]
    assert assessment.candidate_profile_id == attempt.candidate_profile_id == db.profile.id
    assert assessment.total_questions == 2
    assert assessment.duration_minutes == 6
    assert attempt.status == AttemptStatus.IN_PROGRESS
    assert result["started_at"] == attempt.started_at
    assert (result["ends_at"] - result["started_at"]).total_seconds() == 360
    assert {link.question_id for link in db.records[AssessmentQuestion].values()} == ids
    assert all(question.expected_answer and question.evaluation_rubric for question in db.records[Question].values())
    assert all(question.workflow_status == "draft" and question.approval_status == ApprovalStatus.PENDING
               and "assessment_only" in question.tags for question in db.records[Question].values())
    assert db.commits == 2  # Persist the set, then start and persist its attempt.
    assert generator.await_args.kwargs["role_title"] == "Software Engineer"
    assert generator.await_args.kwargs["candidate_skills"] == ["Python", "PostgreSQL"]
    assert generator.await_args.kwargs["candidate_experience"] == "2-5 years"
    assert generator.await_args.kwargs["request"].question_types == ["mcq_single", "short_answer"]


@pytest.mark.asyncio
@pytest.mark.parametrize(("count", "minutes"), [(1, 5), (50, 150)])
async def test_quiz_duration_is_bounded_and_all_generated_questions_are_linked(monkeypatch, count, minutes):
    monkeypatch.setattr(AssessmentService, "generate_assessment_questions", AsyncMock(return_value=generated_questions(count)))
    db = FakeDB()
    result = await QuestionService.generate_quiz(db, db.profile.id, "PostgreSQL", count)
    assessment = db.records[Assessment][uuid.UUID(result["assessment_id"])]
    assert assessment.duration_minutes == minutes
    assert len(db.records[AssessmentQuestion]) == count


@pytest.mark.asyncio
async def test_quiz_propagates_provider_unavailability_without_fabricated_fallback(monkeypatch):
    generator = AsyncMock(side_effect=HTTPException(status_code=503, detail="AI question generation is unavailable"))
    monkeypatch.setattr(AssessmentService, "generate_assessment_questions", generator)
    db = FakeDB()
    with pytest.raises(HTTPException) as error:
        await QuestionService.generate_quiz(db, db.profile.id, "PostgreSQL", 3)
    assert error.value.status_code == 503
    assert "unavailable" in error.value.detail
    generator.assert_awaited_once()
    assert not db.pending and not any(db.records.values()) and db.commits == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(("topic", "count"), [("   ", 1), ("Python", 51), ("Python", 0)])
async def test_quiz_rejects_blank_topics_and_unbounded_question_counts(topic, count):
    with pytest.raises(HTTPException) as error:
        await QuestionService.generate_quiz(FakeDB(), uuid.uuid4(), topic, count)
    assert error.value.status_code == 422


@pytest.mark.asyncio
async def test_quiz_requires_profile_and_industry_before_persisting(monkeypatch):
    generator = AsyncMock()
    monkeypatch.setattr(AssessmentService, "generate_assessment_questions", generator)
    db = FakeDB()
    with pytest.raises(HTTPException) as missing:
        await QuestionService.generate_quiz(db, uuid.uuid4(), "PostgreSQL", 1)
    assert missing.value.status_code == 404
    db.profile.industry_id = None
    with pytest.raises(HTTPException) as no_industry:
        await QuestionService.generate_quiz(db, db.profile.id, "PostgreSQL", 1)
    assert no_industry.value.status_code == 422
    generator.assert_not_awaited()
    assert not any(db.records.values())
