import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from fastapi import HTTPException
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, async_engine
from app.integrations.ai.base import AIResponse
from app.models.assessment import AssessmentAttempt, AssessmentQuestion, AssessmentResult, AttemptStatus, CandidateAnswer
from app.models.candidate import CandidateProfile
from app.models.question import ApprovalStatus, DifficultyLevel, Question, QuestionType
from app.models.taxonomy import Industry, JobRole, Skill
from app.schemas.assessment import AssessmentConfigureRequest, CandidateAnswerSaveRequest
from app.services import assessment_service


async def configure_assessment_for_candidate(async_client: AsyncClient, headers: dict, industry_id: str) -> dict:
    configured = await async_client.post("/api/v1/testing/configure", headers=headers, json={
        "industry_id": industry_id, "difficulty": None, "duration_minutes": 5, "num_questions": 1,
    })
    assert configured.status_code == 201, configured.text
    return configured.json()["data"]


@pytest.mark.asyncio
async def test_assessment_lifecycle(async_client: AsyncClient, candidate_headers: dict):
    # 1. Fetch an industry
    ind_res = await async_client.get("/api/v1/industries")
    assert ind_res.status_code == 200
    industry_id = None
    for industry in ind_res.json()["data"]:
        matching = await async_client.get(
            "/api/v1/questions", headers=candidate_headers,
            params={"industry_id": industry["id"], "limit": 100},
        )
        if matching.status_code == 200 and len(matching.json()["data"]) >= 2:
            industry_id = industry["id"]
            break
    assert industry_id, "Test fixtures must contain an industry with at least two published questions"

    # 2. Configure Assessment
    conf_res = await async_client.post(
        "/api/v1/testing/configure",
        headers=candidate_headers,
        json={
            "industry_id": industry_id,
            "difficulty": None,
            "duration_minutes": 15,
            "num_questions": 2
        }
    )
    assert conf_res.status_code == 201, conf_res.text
    assessment = conf_res.json()["data"]
    assessment_id = assessment["id"]

    # 3. Start Assessment Attempt
    start_res = await async_client.post(
        f"/api/v1/testing/{assessment_id}/start",
        headers=candidate_headers
    )
    assert start_res.status_code == 200
    start_data = start_res.json()["data"]
    attempt_id = start_data["attempt_id"]
    questions = start_data["questions"]
    assert len(questions) > 0

    in_progress_history = await async_client.get("/api/v1/testing/history", headers=candidate_headers)
    current_attempt = next(item for item in in_progress_history.json()["data"] if item["id"] == attempt_id)
    assert current_attempt["percentage"] is None
    assert current_attempt["passed"] is None
    assert current_attempt["evaluation_status"] == "pending"

    # Verify answers and explanations are hidden during test
    assert questions[0]["expected_answer"] is None
    assert questions[0]["explanation"] is None

    # 4. Save Answer
    q1 = questions[0]
    save_res = await async_client.post(
        f"/api/v1/testing/attempts/{attempt_id}/save-answer",
        headers=candidate_headers,
        json={
            "question_id": q1["id"],
            "selected_options": ["B"],
            "is_marked_for_review": False
        }
    )
    assert save_res.status_code == 200
    assert save_res.json()["data"]["saved"] is True

    # 5. Submit Assessment
    sub_res = await async_client.post(
        f"/api/v1/testing/attempts/{attempt_id}/submit",
        headers=candidate_headers
    )
    assert sub_res.status_code == 200
    result = sub_res.json()["data"]
    assert "total_score" in result
    assert "percentage" in result
    assert "passed" in result
    assert "topic_breakdown" in result
    assert result["evaluation_status"] in {"evaluated", "partial"}
    if result["evaluation_status"] == "partial":
        assert result["percentage"] is None
        assert result["passed"] is None
    assert len(result["question_feedback"]) == assessment["total_questions"]


@pytest.mark.asyncio
async def test_assessment_requires_published_question_and_honors_role_and_skill_links(
    async_client: AsyncClient, candidate_headers: dict, admin_headers: dict,
):
    profile = (await async_client.get("/api/v1/candidates/profile", headers=candidate_headers)).json()["data"]
    taxonomy = (await async_client.get(
        f"/api/v1/question-taxonomy?industry_id={profile['industry_id']}", headers=candidate_headers,
    )).json()["data"]
    assert taxonomy["job_roles"]
    assert taxonomy["skills"]
    role = taxonomy["job_roles"][0]
    skill = taxonomy["skills"][0]
    topic = f"assessment publication check {uuid.uuid4()}"
    question = await async_client.post("/api/v1/questions", headers=admin_headers, json={
        "question_text": f"How should a candidate demonstrate {skill['name']}?",
        "question_type": "mcq_single", "industry_id": profile["industry_id"],
        "job_role_id": role["id"], "job_role_ids": [role["id"]], "skill_ids": [skill["id"]],
        "subject": "Assessment publication regression", "topic": topic,
        "difficulty": "intermediate", "interview_round": "Technical",
        "options": [
            {"id": "A", "text": "A grounded, correct answer", "is_correct": True},
            {"id": "B", "text": "A distractor", "is_correct": False},
        ], "expected_answer": "Explain the relevant evidence.",
        "source_provenance": "editorially_reviewed",
    })
    assert question.status_code == 201, question.text
    question_id = question.json()["data"]["id"]
    approved = await async_client.post(f"/api/v1/questions/manage/{question_id}/review", headers=admin_headers,
        json={"decision": "approved"})
    assert approved.status_code == 200, approved.text

    config = {
        "industry_id": profile["industry_id"], "job_role_id": role["id"],
        "skill_id": skill["id"], "topics": [topic], "num_questions": 1,
        "duration_minutes": 5, "randomize_questions": False,
    }
    unpublished = await async_client.post("/api/v1/testing/configure", headers=candidate_headers, json=config)
    assert unpublished.status_code == 400, unpublished.text

    published = await async_client.post(f"/api/v1/questions/manage/{question_id}/publish", headers=admin_headers)
    assert published.status_code == 200, published.text
    configured = await async_client.post("/api/v1/testing/configure", headers=candidate_headers, json=config)
    assert configured.status_code == 201, configured.text
    started = await async_client.post(f"/api/v1/testing/{configured.json()['data']['id']}/start", headers=candidate_headers)
    assert started.status_code == 200, started.text
    assert [item["id"] for item in started.json()["data"]["questions"]] == [question_id]


@pytest.mark.asyncio
async def test_gemini_generated_questions_persist_for_candidate_assessment_and_stay_unpublished(
    async_client: AsyncClient, candidate_headers: dict, monkeypatch,
):
    from app.services import assessment_service

    class TestProvider:
        def is_available(self):
            return True

        async def generate_structured(self, prompt, response_schema, **kwargs):
            return AIResponse(provider_name="test-double", structured_data={"questions": [
                {
                    "question_type": "mcq_single", "difficulty": "intermediate",
                    "subject": "Database Systems", "topic": topic,
                    "question_text": "How does a transaction maintain atomic database updates?",
                    "expected_answer": "All included changes commit together or roll back together.",
                    "explanation": "Atomicity prevents a partially applied transaction.",
                    "options": [
                        {"id": "A", "text": "All changes commit or roll back together", "is_correct": True},
                        {"id": "B", "text": "Every query runs in a separate database", "is_correct": False},
                    ],
                    "evaluation_rubric": {},
                },
            ]})

    monkeypatch.setattr(assessment_service, "get_ai_provider", lambda: TestProvider())
    profile = (await async_client.get("/api/v1/candidates/profile", headers=candidate_headers)).json()["data"]
    topic = f"zz_test_assessment_gemini_{uuid.uuid4()}"
    configured = await async_client.post("/api/v1/testing/configure", headers=candidate_headers, json={
        "industry_id": profile["industry_id"], "subject": "Database Systems", "topic": topic,
        "difficulty": "Mixed", "interview_round": "Mixed", "num_questions": 1,
        "duration_minutes": 5,
    })
    assert configured.status_code == 201, configured.text
    assert "AI-generated, unreviewed question(s)" in configured.json()["data"]["description"]
    assert configured.json()["data"]["ai_generated_question_count"] == 1

    started = await async_client.post(
        f"/api/v1/testing/{configured.json()['data']['id']}/start", headers=candidate_headers,
    )
    assert started.status_code == 200, started.text
    question = started.json()["data"]["questions"][0]
    assert question["source_provenance"] == "ai_generated"
    assert question["approval_status"] == "pending"
    assert question["expected_answer"] is None
    assert question["options"] == [
        {"id": "A", "text": "All changes commit or roll back together"},
        {"id": "B", "text": "Every query runs in a separate database"},
    ]

    attempt_id = started.json()["data"]["attempt_id"]
    saved = await async_client.post(
        f"/api/v1/testing/attempts/{attempt_id}/save-answer", headers=candidate_headers,
        json={"question_id": question["id"], "selected_options": ["A"]},
    )
    assert saved.status_code == 200, saved.text
    submitted = await async_client.post(
        f"/api/v1/testing/attempts/{attempt_id}/submit", headers=candidate_headers,
    )
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["data"]["correct_count"] == 1
    assert submitted.json()["data"]["evaluation_provenance"] == "deterministic"

    visible_bank = await async_client.get("/api/v1/questions", headers=candidate_headers, params={
        "industry_id": profile["industry_id"], "search": topic,
    })
    assert visible_bank.status_code == 200, visible_bank.text
    assert all(item["id"] != question["id"] for item in visible_bank.json()["data"])


@pytest.mark.asyncio
async def test_assessment_configuration_and_attempt_routes_are_candidate_owned(
    async_client: AsyncClient, candidate_headers: dict,
):
    profile = (await async_client.get("/api/v1/candidates/profile", headers=candidate_headers)).json()["data"]
    assessment = await configure_assessment_for_candidate(async_client, candidate_headers, profile["industry_id"])
    owner_start = await async_client.post(f"/api/v1/testing/{assessment['id']}/start", headers=candidate_headers)
    assert owner_start.status_code == 200, owner_start.text
    attempt_id = owner_start.json()["data"]["attempt_id"]
    question_id = owner_start.json()["data"]["questions"][0]["id"]

    email = f"zz_test_assessment_owner_{uuid.uuid4()}@example.com"
    password = "ZzTestAssessmentOwner123!"
    registered = await async_client.post("/api/v1/auth/register", json={
        "email": email, "password": password, "full_name": "zz_test Assessment Owner Isolation",
    })
    assert registered.status_code == 201, registered.text
    login = await async_client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    other_headers = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}

    assert (await async_client.post(f"/api/v1/testing/{assessment['id']}/start", headers=other_headers)).status_code == 404
    assert (await async_client.post(f"/api/v1/testing/attempts/{attempt_id}/save-answer", headers=other_headers,
        json={"question_id": question_id, "selected_options": ["A"]})).status_code == 404
    assert (await async_client.post(f"/api/v1/testing/attempts/{attempt_id}/submit", headers=other_headers)).status_code == 404
    assert (await async_client.get(f"/api/v1/testing/attempts/{attempt_id}/results", headers=other_headers)).status_code == 404
    other_history = await async_client.get("/api/v1/testing/history", headers=other_headers)
    assert other_history.status_code == 200
    assert all(item["id"] != attempt_id for item in other_history.json()["data"])

    owner_history = await async_client.get("/api/v1/testing/history", headers=candidate_headers)
    assert any(item["id"] == attempt_id for item in owner_history.json()["data"])


@pytest.mark.asyncio
async def test_expired_attempt_is_finalized_and_cannot_be_resumed_or_modified(
    async_client: AsyncClient, candidate_headers: dict,
):
    profile = (await async_client.get("/api/v1/candidates/profile", headers=candidate_headers)).json()["data"]
    assessment = await configure_assessment_for_candidate(async_client, candidate_headers, profile["industry_id"])
    started = await async_client.post(f"/api/v1/testing/{assessment['id']}/start", headers=candidate_headers)
    assert started.status_code == 200, started.text
    start_data = started.json()["data"]
    attempt_id = start_data["attempt_id"]
    question_id = start_data["questions"][0]["id"]

    async with AsyncSessionLocal() as db:
        attempt = await db.get(AssessmentAttempt, uuid.UUID(attempt_id))
        attempt.started_at = datetime.now(timezone.utc) - timedelta(minutes=assessment["duration_minutes"] + 1)
        await db.commit()

    resume = await async_client.post(f"/api/v1/testing/{assessment['id']}/start", headers=candidate_headers)
    assert resume.status_code == 410, resume.text
    history = await async_client.get("/api/v1/testing/history", headers=candidate_headers)
    expired = next(item for item in history.json()["data"] if item["id"] == attempt_id)
    assert expired["status"] == "timed_out"
    assert expired["completed_at"] is not None

    modification = await async_client.post(f"/api/v1/testing/attempts/{attempt_id}/save-answer", headers=candidate_headers,
        json={"question_id": question_id, "selected_options": ["A"]})
    assert modification.status_code == 400

    first_submit = await async_client.post(f"/api/v1/testing/attempts/{attempt_id}/submit", headers=candidate_headers)
    second_submit = await async_client.post(f"/api/v1/testing/attempts/{attempt_id}/submit", headers=candidate_headers)
    assert first_submit.status_code == second_submit.status_code == 200
    assert second_submit.json()["data"] == first_submit.json()["data"]


@pytest.mark.asyncio
async def test_first_start_locks_assessment_before_searching_for_attempt():
    from app.services.assessment_service import AssessmentService

    class CheckedLock(Exception):
        pass

    class Database:
        async def scalar(self, statement):
            assert statement._for_update_arg is not None, "First-start must lock the assessment row"
            assert "assessments" in str(statement)
            raise CheckedLock

    with pytest.raises(CheckedLock):
        await AssessmentService.start_assessment(Database(), uuid.uuid4(), SimpleNamespace(id=uuid.uuid4()))


# These service tests use an outer transaction on the explicitly guarded pytest DB;
# service commits release savepoints, and fixture teardown rolls back all test data.
@pytest_asyncio.fixture
async def assessment_case():
    async with async_engine.connect() as connection:
        transaction = await connection.begin()
        try:
            async with AsyncSession(bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint") as db:
                profile_id = await db.scalar(select(CandidateProfile.id).limit(1))
                assert profile_id, "An isolated seeded candidate profile is required"
                suffix = str(uuid.uuid4())
                industry = Industry(name=f"zz_test_assessment_{suffix}", slug=f"zz-test-{suffix}", is_active=True)
                db.add(industry)
                await db.flush()
                role = JobRole(industry_id=industry.id, title="Test Database Engineer", is_active=True)
                other_role = JobRole(industry_id=industry.id, title="Test Marketing Manager", is_active=True)
                skill = Skill(name=f"zz_test_SQL_{suffix}", is_active=True)
                db.add_all([role, other_role, skill])
                await db.flush()
                profile = SimpleNamespace(
                    id=profile_id, target_role=role.title, key_skills=["Python"],
                    candidate_type="working_professional", total_experience_months=36,
                )
                yield db, profile, industry, role, other_role, skill
        finally:
            await transaction.rollback()


async def add_bank_question(db, industry, role, *, question_type=QuestionType.MCQ_SINGLE, topic="SQL"):
    question = Question(
        industry_id=industry.id, job_role_id=role.id, subject="Database Systems", topic=topic,
        question_text=f"Explain the database behavior in test {uuid.uuid4()}.",
        question_type=question_type, difficulty=DifficultyLevel.INTERMEDIATE, interview_round="Technical",
        options=([
            {"id": "A", "text": "Correct", "is_correct": True},
            {"id": "B", "text": "Distractor", "is_correct": False},
            *([{"id": "C", "text": "Also correct", "is_correct": True}] if question_type == QuestionType.MCQ_MULTIPLE else []),
        ] if question_type in {QuestionType.MCQ_SINGLE, QuestionType.MCQ_MULTIPLE} else []),
        expected_answer="A grounded answer.", approval_status=ApprovalStatus.APPROVED,
        workflow_status="published", is_archived=False,
    )
    db.add(question)
    await db.flush()
    return question


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid", ["industry", "inactive_role", "wrong_industry_role", "skill"])
async def test_full_bank_configuration_rejects_invalid_taxonomy_before_bank_query(assessment_case, monkeypatch, invalid):
    db, profile, industry, role, other_role, skill = assessment_case
    await add_bank_question(db, industry, role)
    config = dict(industry_id=industry.id, job_role_id=role.id, num_questions=1)
    if invalid == "industry":
        industry.is_active = False
    elif invalid == "inactive_role":
        role.is_active = False
    elif invalid == "wrong_industry_role":
        foreign = Industry(name=f"zz_test_foreign_{uuid.uuid4()}", slug=str(uuid.uuid4()), is_active=True)
        db.add(foreign)
        await db.flush()
        role.industry_id = foreign.id
    else:
        skill.is_active = False
        config["skill_id"] = skill.id
    await db.flush()

    def no_provider():
        pytest.fail("Invalid taxonomy must be rejected before invoking any AI provider")

    monkeypatch.setattr(assessment_service, "get_ai_provider", no_provider)
    with pytest.raises(HTTPException) as error:
        await assessment_service.AssessmentService.configure_and_create_assessment(db, AssessmentConfigureRequest(**config), profile)
    assert error.value.status_code == 422


@pytest.mark.asyncio
async def test_profile_target_role_limits_full_bank_and_persists_resolved_role(assessment_case):
    db, profile, industry, role, other_role, skill = assessment_case
    await add_bank_question(db, industry, other_role)
    wanted = await add_bank_question(db, industry, role)
    profile.target_role = f"  {role.title.upper()}  "
    configured = await assessment_service.AssessmentService.configure_and_create_assessment(
        db, AssessmentConfigureRequest(industry_id=industry.id, num_questions=1, randomize_questions=False), profile,
    )
    linked = (await db.scalars(select(AssessmentQuestion.question_id).where(AssessmentQuestion.assessment_id == configured.id))).all()
    assert linked == [wanted.id]
    assert configured.job_role_id == role.id


@pytest.mark.asyncio
@pytest.mark.parametrize("free_text", [False, True])
async def test_generation_resolves_role_skill_topics_and_persists_real_item_labels(assessment_case, monkeypatch, free_text):
    db, profile, industry, role, other_role, skill = assessment_case
    if free_text:
        profile.target_role = "Specialist in uncommon database systems"
    topics = ["SQL", "Transactions"]
    prompts = []

    class Provider:
        def is_available(self):
            return True

        async def generate_structured(self, prompt, response_schema, **kwargs):
            prompts.append(prompt)
            return AIResponse(provider_name="test-double", structured_data={"questions": [
                {
                    "question_type": "short_answer", "difficulty": "intermediate",
                    "question_text": f"Explain practical database {topic} behavior.",
                    "subject": "Database Systems", "topic": topic,
                    "expected_answer": "Explain the relevant database principle.", "options": [],
                } for topic in topics
            ]})

    monkeypatch.setattr(assessment_service, "get_ai_provider", lambda: Provider())
    configured = await assessment_service.AssessmentService.configure_and_create_assessment(
        db, AssessmentConfigureRequest(
            industry_id=industry.id, skill_id=skill.id, topics=topics, subject="Database Systems",
            question_types=["short_answer"], difficulty="intermediate", num_questions=2,
        ), profile,
    )
    assert f'"required_skill": "{skill.name}"' in prompts[0]
    assert '"requested_topics": ["SQL", "Transactions"]' in prompts[0]
    assert f'"job_role": "{profile.target_role}"' in prompts[0]
    linked = (await db.scalars(select(Question).join(AssessmentQuestion).where(AssessmentQuestion.assessment_id == configured.id).order_by(AssessmentQuestion.order_index))).all()
    assert [item.topic for item in linked] == topics
    assert all(item.subject == "Database Systems" for item in linked)
    assert all(item.job_role_id == (None if free_text else role.id) for item in linked)
    for item in linked:
        await db.refresh(item, ["skills"])
        assert [entry.id for entry in item.skills] == [skill.id]


@pytest.mark.asyncio
@pytest.mark.parametrize(("kind", "payload"), [
    (QuestionType.MCQ_SINGLE, {"selected_options": ["NO_SUCH_ID"]}),
    (QuestionType.MCQ_SINGLE, {"selected_options": ["A", "B"]}),
    (QuestionType.MCQ_SINGLE, {"text_response": "A text answer"}),
    (QuestionType.SHORT_ANSWER, {"selected_options": ["A"]}),
])
async def test_save_answer_rejects_ids_and_question_type_shape(assessment_case, kind, payload):
    db, profile, industry, role, other_role, skill = assessment_case
    question = await add_bank_question(db, industry, role, question_type=kind)
    configured = await assessment_service.AssessmentService.configure_and_create_assessment(
        db, AssessmentConfigureRequest(industry_id=industry.id, num_questions=1), profile,
    )
    started = await assessment_service.AssessmentService.start_assessment(db, configured.id, profile)
    with pytest.raises(HTTPException) as error:
        await assessment_service.AssessmentService.save_answer(
            db, started.attempt_id, profile.id, CandidateAnswerSaveRequest(question_id=question.id, **payload),
        )
    assert error.value.status_code == 422
    assert not (await db.scalars(select(CandidateAnswer).where(CandidateAnswer.assessment_attempt_id == started.attempt_id))).all()


@pytest.mark.asyncio
@pytest.mark.parametrize(("selected", "penalty", "expected", "correct"), [
    (["A", "C"], 2, 10.0, True), (["B"], 2, -2.0, False),
    (["A"], 2, -2.0, False), (["A", "B", "C"], 2, -2.0, False),
    (["A"], 0, 7.5, False), ([], 2, 0.0, False),
])
async def test_multiple_choice_negative_marking_and_repeat_result_timing(assessment_case, selected, penalty, expected, correct):
    db, profile, industry, role, other_role, skill = assessment_case
    question = await add_bank_question(db, industry, role, question_type=QuestionType.MCQ_MULTIPLE)
    configured = await assessment_service.AssessmentService.configure_and_create_assessment(
        db, AssessmentConfigureRequest(industry_id=industry.id, num_questions=1, negative_marking_points=penalty), profile,
    )
    started = await assessment_service.AssessmentService.start_assessment(db, configured.id, profile)
    await assessment_service.AssessmentService.save_answer(
        db, started.attempt_id, profile.id, CandidateAnswerSaveRequest(question_id=question.id, selected_options=selected),
    )
    attempt = await db.get(AssessmentAttempt, started.attempt_id)
    attempt.started_at -= timedelta(seconds=30)
    await db.commit()
    first = await assessment_service.AssessmentService.submit_assessment(db, started.attempt_id, profile.id)
    repeated = await assessment_service.AssessmentService.submit_assessment(db, started.attempt_id, profile.id)
    fetched = await assessment_service.AssessmentService.get_result(db, started.attempt_id, profile.id)
    assert first.total_score == expected
    assert first.correct_count == int(correct)
    assert first.unanswered_count == int(not selected)
    assert first.incorrect_count == int(bool(selected) and not correct)
    assert first.time_spent_seconds >= 30
    assert first.completed_at is not None
    assert repeated.model_dump() == fetched.model_dump() == first.model_dump()


@pytest.mark.asyncio
async def test_subjective_correct_answer_counts_towards_difficulty_breakdown(assessment_case, monkeypatch):
    db, profile, industry, role, other_role, skill = assessment_case
    question = await add_bank_question(db, industry, role, question_type=QuestionType.SHORT_ANSWER)
    monkeypatch.setattr(assessment_service.AssessmentService, "_evaluate_subjective_answer", AsyncMock(return_value=(8.0, {}, [], "Grounded feedback")))
    configured = await assessment_service.AssessmentService.configure_and_create_assessment(
        db, AssessmentConfigureRequest(industry_id=industry.id, num_questions=1), profile,
    )
    started = await assessment_service.AssessmentService.start_assessment(db, configured.id, profile)
    await assessment_service.AssessmentService.save_answer(
        db, started.attempt_id, profile.id, CandidateAnswerSaveRequest(question_id=question.id, text_response="A grounded explanation"),
    )
    result = await assessment_service.AssessmentService.submit_assessment(db, started.attempt_id, profile.id)
    assert result.correct_count == 1
    assert result.difficulty_breakdown["intermediate"] == {"correct": 1, "total": 1, "evaluated": 1, "marks_awarded": 8.0}
    assert result.topic_breakdown["SQL"]["correct"] == 1


@pytest.mark.asyncio
async def test_concurrent_first_starts_reuse_one_attempt_and_concurrent_submits_reuse_result(
    async_client: AsyncClient, candidate_headers: dict,
):
    profile = (await async_client.get("/api/v1/candidates/profile", headers=candidate_headers)).json()["data"]
    configured = await configure_assessment_for_candidate(async_client, candidate_headers, profile["industry_id"])
    starts = await asyncio.gather(*[
        async_client.post(f"/api/v1/testing/{configured['id']}/start", headers=candidate_headers)
        for _ in range(3)
    ])
    assert all(response.status_code == 200 for response in starts), [response.text for response in starts]
    attempt_ids = {response.json()["data"]["attempt_id"] for response in starts}
    assert len(attempt_ids) == 1
    attempt_id = attempt_ids.pop()
    async with AsyncSessionLocal() as db:
        count = await db.scalar(select(func.count(AssessmentAttempt.id)).where(
            AssessmentAttempt.assessment_id == uuid.UUID(configured["id"]),
            AssessmentAttempt.status == AttemptStatus.IN_PROGRESS,
        ))
        assert count == 1
        attempt = await db.get(AssessmentAttempt, uuid.UUID(attempt_id))
        attempt.started_at -= timedelta(seconds=30)
        await db.commit()
    submitted = await asyncio.gather(*[
        async_client.post(f"/api/v1/testing/attempts/{attempt_id}/submit", headers=candidate_headers)
        for _ in range(3)
    ])
    assert all(response.status_code == 200 for response in submitted), [response.text for response in submitted]
    results = [response.json()["data"] for response in submitted]
    assert results[0]["time_spent_seconds"] >= 30
    assert results[0]["completed_at"] is not None
    assert all(result == results[0] for result in results)


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [
    {"selected_options": ["A", " a "]},
    {"selected_options": ["UNKNOWN"]},
    {"selected_options": ["A"], "text_response": "Also text"},
])
async def test_submit_rejects_invalid_legacy_answers_without_finalizing(assessment_case, payload):
    db, profile, industry, role, other_role, skill = assessment_case
    question = await add_bank_question(db, industry, role)
    configured = await assessment_service.AssessmentService.configure_and_create_assessment(
        db, AssessmentConfigureRequest(industry_id=industry.id, num_questions=1), profile,
    )
    started = await assessment_service.AssessmentService.start_assessment(db, configured.id, profile)
    db.add(CandidateAnswer(assessment_attempt_id=started.attempt_id, question_id=question.id, **payload))
    await db.commit()
    with pytest.raises(HTTPException) as error:
        await assessment_service.AssessmentService.submit_assessment(db, started.attempt_id, profile.id)
    assert error.value.status_code == 422
    attempt = await db.get(AssessmentAttempt, started.attempt_id)
    assert attempt.status == AttemptStatus.IN_PROGRESS
    assert attempt.completed_at is None
    assert await db.scalar(select(func.count(AssessmentResult.id)).where(AssessmentResult.assessment_attempt_id == started.attempt_id)) == 0


@pytest.mark.asyncio
async def test_save_canonical_option_ids_and_clear_answers_for_review(assessment_case):
    db, profile, industry, role, other_role, skill = assessment_case
    question = await add_bank_question(db, industry, role)
    configured = await assessment_service.AssessmentService.configure_and_create_assessment(
        db, AssessmentConfigureRequest(industry_id=industry.id, num_questions=1), profile,
    )
    started = await assessment_service.AssessmentService.start_assessment(db, configured.id, profile)
    await assessment_service.AssessmentService.save_answer(
        db, started.attempt_id, profile.id, CandidateAnswerSaveRequest(question_id=question.id, selected_options=[" a "]),
    )
    resumed = await assessment_service.AssessmentService.start_assessment(db, configured.id, profile)
    assert resumed.attempt_id == started.attempt_id
    assert resumed.saved_answers[0]["selected_options"] == ["A"]
    await assessment_service.AssessmentService.save_answer(
        db, started.attempt_id, profile.id, CandidateAnswerSaveRequest(question_id=question.id, text_response="   ", is_marked_for_review=True),
    )
    resumed = await assessment_service.AssessmentService.start_assessment(db, configured.id, profile)
    assert resumed.saved_answers[0]["selected_options"] == []
    assert resumed.saved_answers[0]["text_response"] is None
    assert resumed.saved_answers[0]["is_marked_for_review"] is True
