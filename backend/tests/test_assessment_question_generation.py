import uuid

import pytest
from fastapi import HTTPException

from app.integrations.ai.base import AIResponse
from app.models.candidate import CandidateProfile
from app.schemas.assessment import AssessmentConfigureRequest
from app.services import assessment_service


def generated_question(text: str, *, option_key: str = "A", difficulty: str = "intermediate") -> dict:
    return {
        "question_type": "mcq_single",
        "subject": "Database Systems",
        "topic": "SQL",
        "difficulty": difficulty,
        "question_text": text,
        "expected_answer": "The answer supported by the supplied technical context.",
        "explanation": "The selected option follows from the stated principle.",
        "options": [
            {"id": option_key, "text": "Correct answer", "is_correct": True},
            {"id": "B", "text": "Incorrect answer", "is_correct": False},
        ],
        "evaluation_rubric": {},
    }


class FakeProvider:
    def __init__(self, response: AIResponse, available: bool = True):
        self.response = response
        self.available = available
        self.prompts: list[str] = []

    def is_available(self) -> bool:
        return self.available

    async def generate_structured(self, prompt, response_schema, **kwargs):
        self.prompts.append(prompt)
        return self.response


@pytest.mark.parametrize(("candidate_type", "months", "expected"), [
    ("student_fresher", 0, "student/fresher; no professional experience duration recorded"),
    ("working_professional", 36, "2-5 years"),
    ("working_professional", 144, "10+ years"),
])
def test_candidate_experience_is_reduced_to_a_non_identifying_band(candidate_type, months, expected):
    profile = CandidateProfile(candidate_type=candidate_type, total_experience_months=months)

    assert assessment_service.AssessmentService._candidate_experience_context(profile) == expected


@pytest.mark.asyncio
async def test_candidate_practice_context_returns_only_topic_level_deterministic_aggregates():
    profile_id = uuid.uuid4()

    class Result:
        def all(self):
            return [("SQL", 62.56, 4), ("System Design", 90.0, 2)]

    class Database:
        async def execute(self, statement):
            assert "question_practice_logs" in str(statement)
            assert "questions" in str(statement)
            return Result()

    result = await assessment_service.AssessmentService._candidate_topic_practice_context(
        Database(), profile_id,
    )

    assert result == [
        {"topic": "SQL", "average_score_percentage": 62.6, "evaluated_question_count": 4},
        {"topic": "System Design", "average_score_percentage": 90.0, "evaluated_question_count": 2},
    ]
    assert all("response" not in str(item).lower() for item in result)


@pytest.mark.asyncio
async def test_assessment_generation_validates_complete_distinct_ai_questions(monkeypatch):
    provider = FakeProvider(AIResponse(
        structured_data={"questions": [
            generated_question("How does a database index improve lookup performance?"),
            generated_question("Which transaction property prevents partial commits?", option_key="C", difficulty="advanced"),
        ]},
        provider_name="test-double",
    ))
    monkeypatch.setattr(assessment_service, "get_ai_provider", lambda: provider)
    request = AssessmentConfigureRequest(industry_id=uuid.uuid4(), num_questions=2, difficulty="Mixed", interview_round="Mixed")

    questions = await assessment_service.AssessmentService.generate_assessment_questions(
        request, "Information Technology", "Software Engineer", [], 2, "3-5 years",
        candidate_skills=["Python", "PostgreSQL"],
        practice_performance=[{"topic": "SQL", "average_score_percentage": 55.0, "evaluated_question_count": 4}],
    )

    assert len(questions) == 2
    assert all(question.question_type.value == "mcq_single" for question in questions)
    assert '"number_of_questions": 2' in provider.prompts[0]
    assert '"difficulty": "mixed difficulty"' in provider.prompts[0]
    assert '"experience_level": "3-5 years"' in provider.prompts[0]
    assert '"subject": "Infer a suitable subject' in provider.prompts[0]
    assert '"topic": "SQL"' in provider.prompts[0]


@pytest.mark.asyncio
async def test_assessment_generation_does_not_fabricate_when_provider_unavailable(monkeypatch):
    provider = FakeProvider(AIResponse(is_success=False), available=False)
    monkeypatch.setattr(assessment_service, "get_ai_provider", lambda: provider)
    request = AssessmentConfigureRequest(industry_id=uuid.uuid4(), num_questions=1)

    with pytest.raises(HTTPException) as error:
        await assessment_service.AssessmentService.generate_assessment_questions(
            request, "Information Technology", "Software Engineer", [], 1,
        )

    assert error.value.status_code == 503
    assert "AI question generation is unavailable" in error.value.detail


@pytest.mark.asyncio
async def test_blank_assessment_topic_uses_candidate_skills_as_prompt_context(monkeypatch):
    provider = FakeProvider(AIResponse(structured_data={"questions": [
        generated_question("How should an engineer prioritize employee onboarding improvements?")
    ]}, provider_name="test-double"))
    monkeypatch.setattr(assessment_service, "get_ai_provider", lambda: provider)
    request = AssessmentConfigureRequest(industry_id=uuid.uuid4(), num_questions=1)

    result = await assessment_service.AssessmentService.generate_assessment_questions(
        request, "Human Resources", "HR Generalist", [], 1,
        candidate_experience="2-5 years", candidate_skills=["Python", "People analytics"],
    )

    assert len(result) == 1
    assert '"candidate_skills": ["Python", "People analytics"]' in provider.prompts[0]
    assert "infer relevant topics" in provider.prompts[0].lower()


@pytest.mark.asyncio
@pytest.mark.parametrize("questions", [
    [generated_question("How does a database index improve lookup performance?")],
    [
        generated_question("How does a database index improve lookup performance?"),
        generated_question("How does a database index improve lookup performance?"),
    ],
    [
        {**generated_question("How does a database index improve lookup performance?"), "options": []},
    ],
])
async def test_assessment_generation_rejects_incomplete_duplicate_or_invalid_provider_output(monkeypatch, questions):
    provider = FakeProvider(AIResponse(structured_data={"questions": questions}, provider_name="test-double"))
    monkeypatch.setattr(assessment_service, "get_ai_provider", lambda: provider)
    request = AssessmentConfigureRequest(industry_id=uuid.uuid4(), num_questions=2)

    with pytest.raises(HTTPException) as error:
        await assessment_service.AssessmentService.generate_assessment_questions(
            request, "Information Technology", "Software Engineer", [], 2,
        )

    assert error.value.status_code == 503
    assert "No assessment or generated questions were saved" in error.value.detail


@pytest.mark.asyncio
async def test_generation_prompt_includes_required_skill_and_all_requested_topics(monkeypatch):
    provider = FakeProvider(AIResponse(structured_data={"questions": [
        generated_question("How does an SQL index support transaction lookups?")
    ]}, provider_name="test-double"))
    monkeypatch.setattr(assessment_service, "get_ai_provider", lambda: provider)
    request = AssessmentConfigureRequest(
        industry_id=uuid.uuid4(), topics=["SQL", "Transactions"], topic="Indexes",
        subject="Database Systems", num_questions=1,
    )
    questions = await assessment_service.AssessmentService.generate_assessment_questions(
        request, "Information Technology", "Software Engineer", [], 1,
        required_skill="PostgreSQL", candidate_skills=["Python"],
    )
    assert questions[0].subject == "Database Systems"
    assert questions[0].topic == "SQL"
    assert '"requested_topics": ["SQL", "Transactions", "Indexes"]' in provider.prompts[0]
    assert '"required_skill": "PostgreSQL"' in provider.prompts[0]
    assert '"candidate_skills": ["Python"]' in provider.prompts[0]


@pytest.mark.asyncio
@pytest.mark.parametrize("labels", [
    {"topic": "Unrequested"}, {"topic": ""}, {"subject": ""},
    {"subject": "Unrequested subject"}, {"topic": "x" * 256},
    {"subject": None}, {"topic": None},
])
async def test_generation_rejects_missing_invalid_or_unrequested_labels(monkeypatch, labels):
    item = {**generated_question("How does a database index support efficient lookups?"), **labels}
    provider = FakeProvider(AIResponse(structured_data={"questions": [item]}, provider_name="test-double"))
    monkeypatch.setattr(assessment_service, "get_ai_provider", lambda: provider)
    request = AssessmentConfigureRequest(
        industry_id=uuid.uuid4(), subject="Database Systems", topics=["SQL"], num_questions=1,
    )
    with pytest.raises(HTTPException) as error:
        await assessment_service.AssessmentService.generate_assessment_questions(
            request, "Information Technology", "Software Engineer", [], 1,
        )
    assert error.value.status_code == 503
    assert "No assessment or generated questions were saved" in error.value.detail


@pytest.mark.asyncio
async def test_generation_supports_quiz_request_without_extra_topics(monkeypatch):
    from types import SimpleNamespace

    provider = FakeProvider(AIResponse(structured_data={"questions": [
        generated_question("How does an SQL transaction maintain atomicity?")
    ]}, provider_name="test-double"))
    monkeypatch.setattr(assessment_service, "get_ai_provider", lambda: provider)
    request = SimpleNamespace(
        question_types=["mcq_single"], difficulty="intermediate", subject="Database Systems",
        topic="SQL", interview_round="Practice",
    )
    result = await assessment_service.AssessmentService.generate_assessment_questions(
        request, "Information Technology", "Software Engineer", [], 1,
    )
    assert len(result) == 1
    assert '"requested_topics": ["SQL"]' in provider.prompts[0]
