import json
import pytest
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock
from httpx import AsyncClient
from sqlalchemy import func, select
from app.integrations.ai.base import AIResponse
from app.models.assessment import Assessment, AssessmentAttempt, AssessmentQuestion, AttemptStatus, CandidateAnswer
from app.models.candidate import CandidateProfile
from app.models.question import ApprovalStatus, DifficultyLevel, Question, QuestionPracticeLog, QuestionType, SourceProvenance
from app.models.taxonomy import Industry
from app.services import assessment_service
from app.core.database import AsyncSessionLocal
from app.core.config import settings
from app.models.user import User, UserRole
from app.integrations.ai.gemini_provider import GeminiProvider
from app.services import question_service


@pytest.mark.asyncio
async def test_question_bank_and_practice(async_client: AsyncClient, candidate_headers: dict):
    # 1. List questions
    q_res = await async_client.get("/api/v1/questions", headers=candidate_headers)
    assert q_res.status_code == 200
    data = q_res.json()["data"]
    assert len(data) > 0
    first_q = data[0]
    # Candidate list responses must never reveal answer keys or correct MCQ flags.
    assert first_q["expected_answer"] is None
    assert first_q["explanation"] is None
    assert all("is_correct" not in option for option in first_q["options"])

    detail_res = await async_client.get(f"/api/v1/questions/{first_q['id']}", headers=candidate_headers)
    assert detail_res.status_code == 200
    assert detail_res.json()["data"]["expected_answer"] is None

    # 2. Toggle Bookmark
    bm_res = await async_client.post(f"/api/v1/questions/{first_q['id']}/bookmark", headers=candidate_headers)
    assert bm_res.status_code == 200
    assert "is_bookmarked" in bm_res.json()["data"]

    # 3. Practice question
    prac_res = await async_client.post(
        f"/api/v1/questions/{first_q['id']}/practice",
        headers=candidate_headers,
        json={"user_response": "B"}
    )
    assert prac_res.status_code == 200
    prac_data = prac_res.json()["data"]
    assert "is_correct" in prac_data
    assert "feedback" in prac_data
    assert "expected_answer" in prac_data
    assert prac_data["evaluation_status"] in {"evaluated", "unavailable"}


@pytest.mark.asyncio
async def test_question_revision_review_and_publish_lifecycle(async_client: AsyncClient, admin_headers: dict, candidate_headers: dict):
    industries = await async_client.get("/api/v1/industries")
    industry_id = industries.json()["data"][0]["id"]
    created = await async_client.post("/api/v1/questions", headers=admin_headers, json={
        "question_text": "How would you trace a production performance regression?",
        "question_type": "descriptive", "industry_id": industry_id,
        "subject": "Production Systems", "topic": "Performance Analysis",
        "difficulty": "intermediate", "interview_round": "Technical",
        "source_provenance": "editorially_reviewed", "expected_answer": "Inspect traces and compare baselines.",
    })
    assert created.status_code == 201, created.text
    question_id = created.json()["data"]["id"]
    assert created.json()["data"]["workflow_status"] == "pending_review"
    assert (await async_client.get(f"/api/v1/questions/{question_id}", headers=candidate_headers)).status_code == 404

    approved = await async_client.post(f"/api/v1/questions/manage/{question_id}/review", headers=admin_headers,
        json={"decision": "approved", "comment": "Reviewed"})
    assert approved.status_code == 200
    assert approved.json()["data"]["workflow_status"] == "approved"
    assert (await async_client.get(f"/api/v1/questions/{question_id}", headers=candidate_headers)).status_code == 404

    published = await async_client.post(f"/api/v1/questions/manage/{question_id}/publish", headers=admin_headers)
    assert published.status_code == 200
    assert published.json()["data"]["workflow_status"] == "published"
    candidate_view = await async_client.get(f"/api/v1/questions/{question_id}", headers=candidate_headers)
    assert candidate_view.status_code == 200
    assert candidate_view.json()["data"]["expected_answer"] is None

    revised = await async_client.patch(f"/api/v1/questions/manage/{question_id}", headers=admin_headers,
        json={"question_text": "How would you investigate a production performance regression?"})
    assert revised.status_code == 200
    assert revised.json()["data"]["version_number"] == 2
    assert revised.json()["data"]["workflow_status"] == "pending_review"
    assert (await async_client.get(f"/api/v1/questions/{question_id}", headers=candidate_headers)).json()["data"]["question_text"] == "How would you trace a production performance regression?"

    category_name = f"Lifecycle Test Category {uuid.uuid4()}"
    category = await async_client.post("/api/v1/question-taxonomy/manage", headers=admin_headers, json={
        "kind": "category", "name": category_name, "industry_id": industry_id,
    })
    assert category.status_code == 201, category.text
    record_id = category.json()["data"]["id"]
    listing = await async_client.get(f"/api/v1/question-taxonomy/manage/category?search={category_name.replace(' ', '%20')}", headers=admin_headers)
    assert listing.status_code == 200
    assert any(item["id"] == record_id for item in listing.json()["data"])
    deactivated = await async_client.delete(f"/api/v1/question-taxonomy/manage/category/{record_id}", headers=admin_headers)
    assert deactivated.status_code == 200
    assert deactivated.json()["data"]["is_active"] is False


@pytest.mark.asyncio
async def test_explicit_draft_submission_and_archival_candidate_visibility(
    async_client: AsyncClient, admin_headers: dict, candidate_headers: dict,
):
    industry_id = (await async_client.get("/api/v1/industries")).json()["data"][0]["id"]
    question_text = f"Draft workflow acceptance {uuid.uuid4()}: explain an evidence-based triage step."
    payload = {
        "question_text": question_text, "question_type": "short_answer", "industry_id": industry_id,
        "subject": "Workflow Testing", "topic": "Question Review", "difficulty": "intermediate",
        "interview_round": "Technical", "source_provenance": "editorially_reviewed",
        "expected_answer": "State a measurable diagnostic action.", "workflow_status": "draft",
    }
    candidate_create = await async_client.post("/api/v1/questions", headers=candidate_headers, json=payload)
    assert candidate_create.status_code == 403
    created = await async_client.post("/api/v1/questions", headers=admin_headers, json=payload)
    assert created.status_code == 201, created.text
    question_id = created.json()["data"]["id"]
    assert created.json()["data"]["workflow_status"] == "draft"
    assert (await async_client.get(f"/api/v1/questions/{question_id}", headers=candidate_headers)).status_code == 404
    candidate_submit = await async_client.post(f"/api/v1/questions/manage/{question_id}/submit", headers=candidate_headers)
    assert candidate_submit.status_code == 403

    submitted = await async_client.post(f"/api/v1/questions/manage/{question_id}/submit", headers=admin_headers)
    assert submitted.status_code == 200
    assert submitted.json()["data"]["workflow_status"] == "pending_review"
    approved = await async_client.post(f"/api/v1/questions/manage/{question_id}/review", headers=admin_headers,
        json={"decision": "approved"})
    assert approved.status_code == 200
    published = await async_client.post(f"/api/v1/questions/manage/{question_id}/publish", headers=admin_headers)
    assert published.status_code == 200
    assert (await async_client.get(f"/api/v1/questions/{question_id}", headers=candidate_headers)).status_code == 200

    archived = await async_client.delete(f"/api/v1/questions/manage/{question_id}", headers=admin_headers)
    assert archived.status_code == 204
    assert (await async_client.get(f"/api/v1/questions/{question_id}", headers=candidate_headers)).status_code == 404


@pytest.mark.asyncio
async def test_content_manager_question_permissions_and_admin_only_taxonomy_deactivation(
    async_client: AsyncClient,
):
    email = f"content-manager-{uuid.uuid4()}@example.com"
    password = "SecureContentManager123!"
    registration = await async_client.post("/api/v1/auth/register", json={
        "email": email, "password": password, "full_name": "Content Manager Test",
    })
    assert registration.status_code == 201
    async with AsyncSessionLocal() as db:
        user = await db.scalar(select(User).where(User.email == email))
        assert user is not None
        user.role = UserRole.CONTENT_MANAGER
        await db.commit()
    login = await async_client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    manager_headers = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}

    assert (await async_client.get("/api/v1/questions/manage", headers=manager_headers)).status_code == 200
    industry_id = (await async_client.get("/api/v1/industries")).json()["data"][0]["id"]
    create = await async_client.post("/api/v1/questions", headers=manager_headers, json={
        "question_text": f"Content manager question {uuid.uuid4()}: describe a safe review step.",
        "question_type": "short_answer", "industry_id": industry_id,
        "subject": "Permissions", "topic": "Review workflow", "difficulty": "intermediate",
        "interview_round": "Technical", "source_provenance": "editorially_reviewed",
        "expected_answer": "Describe the review and evidence.",
    })
    assert create.status_code == 201, create.text
    question_id = create.json()["data"]["id"]
    approved = await async_client.post(f"/api/v1/questions/manage/{question_id}/review", headers=manager_headers,
        json={"decision": "approved"})
    assert approved.status_code == 200
    assert (await async_client.post(f"/api/v1/questions/manage/{question_id}/publish", headers=manager_headers)).status_code == 200

    category = await async_client.post("/api/v1/question-taxonomy/manage", headers=manager_headers, json={
        "kind": "category", "name": f"Manager managed category {uuid.uuid4()}", "industry_id": industry_id,
    })
    assert category.status_code == 201, category.text
    denied_deactivation = await async_client.delete(
        f"/api/v1/question-taxonomy/manage/category/{category.json()['data']['id']}", headers=manager_headers,
    )
    assert denied_deactivation.status_code == 403


@pytest.mark.asyncio
async def test_question_combined_taxonomy_filters_pagination_sort_and_bookmark_persistence(
    async_client: AsyncClient, candidate_headers: dict, admin_headers: dict,
):
    profile = (await async_client.get("/api/v1/candidates/profile", headers=candidate_headers)).json()["data"]
    taxonomy = (await async_client.get(
        f"/api/v1/question-taxonomy?industry_id={profile['industry_id']}", headers=candidate_headers,
    )).json()["data"]
    assert taxonomy["job_roles"]
    industry_id = profile["industry_id"]
    suffix = str(uuid.uuid4())

    async def create_taxonomy(payload: dict) -> dict:
        response = await async_client.post("/api/v1/question-taxonomy/manage", headers=admin_headers, json=payload)
        assert response.status_code == 201, response.text
        return response.json()["data"]

    category = await create_taxonomy({"kind": "category", "name": f"Combined category {suffix}", "industry_id": industry_id})
    subject = await create_taxonomy({"kind": "subject", "name": f"Combined subject {suffix}", "industry_id": industry_id})
    topic = await create_taxonomy({"kind": "topic", "name": f"Combined topic {suffix}", "parent_id": subject["id"]})
    skill = await create_taxonomy({"kind": "skill", "name": f"Combined skill {suffix}"})
    company = await create_taxonomy({"kind": "company", "name": f"Combined company {suffix}", "industry_id": industry_id})
    level = await create_taxonomy({"kind": "experience_level", "name": f"Combined level {suffix}"})
    round_name = f"Combined round {suffix}"
    interview_round = await create_taxonomy({"kind": "interview_round", "name": round_name, "industry_id": industry_id})
    prefix = f"Combined taxonomy acceptance {suffix}"

    created_ids = []
    for index in range(2):
        created = await async_client.post("/api/v1/questions", headers=admin_headers, json={
            "question_text": f"{prefix}: explain analysis step {index + 1}.",
            "question_type": "short_answer", "industry_id": industry_id,
            "industry_category_id": category["id"], "job_role_id": taxonomy["job_roles"][0]["id"],
            "job_role_ids": [taxonomy["job_roles"][0]["id"]], "skill_ids": [skill["id"]],
            "company_ids": [company["id"]], "subject_id": subject["id"], "topic_id": topic["id"],
            "subject": subject["name"], "topic": topic["name"],
            "experience_level_id": level["id"], "experience_level": level["name"],
            "interview_round_id": interview_round["id"], "interview_round": round_name,
            "difficulty": "intermediate", "source_provenance": "editorially_reviewed",
            "expected_answer": "Explain a measurable way to validate the result.",
        })
        assert created.status_code == 201, created.text
        question_id = created.json()["data"]["id"]
        approved = await async_client.post(f"/api/v1/questions/manage/{question_id}/review", headers=admin_headers,
            json={"decision": "approved"})
        assert approved.status_code == 200
        published = await async_client.post(f"/api/v1/questions/manage/{question_id}/publish", headers=admin_headers)
        assert published.status_code == 200
        created_ids.append(question_id)

    filters = {
        "industry_id": industry_id, "industry_category_id": category["id"],
        "job_role_id": taxonomy["job_roles"][0]["id"], "skill_id": skill["id"],
        "company_id": company["id"], "subject_id": subject["id"], "topic_id": topic["id"],
        "experience_level_id": level["id"], "interview_round": round_name,
        "question_type": "short_answer", "difficulty": "intermediate", "search": prefix,
        "sort_by": "created_at", "sort_order": "asc", "limit": 1,
    }
    page_one = await async_client.get("/api/v1/questions", headers=candidate_headers, params={**filters, "page": 1})
    page_two = await async_client.get("/api/v1/questions", headers=candidate_headers, params={**filters, "page": 2})
    assert page_one.status_code == page_two.status_code == 200
    assert page_one.json()["meta"]["total"] == 2
    assert page_one.json()["meta"]["total_pages"] == 2
    first_id = page_one.json()["data"][0]["id"]
    second_id = page_two.json()["data"][0]["id"]
    assert {first_id, second_id} == set(created_ids)
    bookmarked = await async_client.post(f"/api/v1/questions/{first_id}/bookmark", headers=candidate_headers)
    assert bookmarked.status_code == 200
    bookmarked_page = await async_client.get("/api/v1/questions", headers=candidate_headers,
        params={**filters, "bookmarked": "true", "limit": 10, "page": 1})
    assert bookmarked_page.status_code == 200
    assert [row["id"] for row in bookmarked_page.json()["data"]] == [first_id]


@pytest.mark.asyncio
async def test_objective_practice_scoring_is_exact_deterministic_and_answer_key_safe(
    async_client: AsyncClient, admin_headers: dict, candidate_headers: dict,
):
    industry_id = (await async_client.get("/api/v1/industries")).json()["data"][0]["id"]
    created = await async_client.post("/api/v1/questions", headers=admin_headers, json={
        "question_text": f"Objective scoring acceptance {uuid.uuid4()}: which option is correct?",
        "question_type": "mcq_single", "industry_id": industry_id,
        "subject": "Scoring", "topic": "Deterministic evaluation", "difficulty": "beginner",
        "interview_round": "General", "source_provenance": "editorially_reviewed",
        "expected_answer": "Option A is correct.",
        "options": [
            {"id": "A", "text": "Correct choice", "is_correct": True},
            {"id": "B", "text": "Incorrect choice", "is_correct": False},
        ],
    })
    assert created.status_code == 201, created.text
    question_id = created.json()["data"]["id"]
    assert (await async_client.get(f"/api/v1/questions/{question_id}", headers=candidate_headers)).status_code == 404
    assert (await async_client.post(f"/api/v1/questions/manage/{question_id}/review", headers=admin_headers,
        json={"decision": "approved"})).status_code == 200
    assert (await async_client.post(f"/api/v1/questions/manage/{question_id}/publish", headers=admin_headers)).status_code == 200

    candidate_view = await async_client.get(f"/api/v1/questions/{question_id}", headers=candidate_headers)
    assert candidate_view.status_code == 200
    assert candidate_view.json()["data"]["expected_answer"] is None
    assert all("is_correct" not in option for option in candidate_view.json()["data"]["options"])
    invalid = await async_client.post(f"/api/v1/questions/{question_id}/practice", headers=candidate_headers,
        json={"user_response": "C"})
    assert invalid.status_code == 422

    correct = await async_client.post(f"/api/v1/questions/{question_id}/practice", headers=candidate_headers,
        json={"user_response": "a"})
    wrong = await async_client.post(f"/api/v1/questions/{question_id}/practice", headers=candidate_headers,
        json={"user_response": "B"})
    assert correct.status_code == wrong.status_code == 200
    assert correct.json()["data"]["evaluation_status"] == "evaluated"
    assert correct.json()["data"]["evaluation_provenance"] == "deterministic"
    assert correct.json()["data"]["is_correct"] is True
    assert correct.json()["data"]["score_percentage"] == 100
    assert wrong.json()["data"]["is_correct"] is False
    assert wrong.json()["data"]["score_percentage"] == 0


@pytest.mark.asyncio
async def test_subjective_answer_is_saved_without_a_fabricated_score_when_gemini_is_unavailable(
    async_client: AsyncClient, admin_headers: dict, candidate_headers: dict, monkeypatch,
):
    if settings.GEMINI_API_KEY.strip():
        pytest.skip("Environment has Gemini configured; this case verifies the no-key behavior")
    monkeypatch.setattr(question_service, "get_ai_provider", GeminiProvider)
    industry_id = (await async_client.get("/api/v1/industries")).json()["data"][0]["id"]
    created = await async_client.post("/api/v1/questions", headers=admin_headers, json={
        "question_text": f"Subjective unavailable acceptance {uuid.uuid4()}: describe your reasoning.",
        "question_type": "descriptive", "industry_id": industry_id,
        "subject": "Subjective evaluation", "topic": "Unavailable provider", "difficulty": "intermediate",
        "interview_round": "General", "source_provenance": "editorially_reviewed",
        "expected_answer": "Provide a reasoned response.",
    })
    assert created.status_code == 201, created.text
    question_id = created.json()["data"]["id"]
    assert (await async_client.post(f"/api/v1/questions/manage/{question_id}/review", headers=admin_headers,
        json={"decision": "approved"})).status_code == 200
    assert (await async_client.post(f"/api/v1/questions/manage/{question_id}/publish", headers=admin_headers)).status_code == 200
    answer_text = f"Saved subjective answer {uuid.uuid4()}"
    result = await async_client.post(f"/api/v1/questions/{question_id}/practice", headers=candidate_headers,
        json={"user_response": answer_text})
    assert result.status_code == 200
    assert result.json()["data"]["evaluation_status"] == "unavailable"
    assert result.json()["data"]["evaluation_provenance"] == "none"
    assert result.json()["data"]["score_percentage"] is None
    history = await async_client.get("/api/v1/questions/history", headers=candidate_headers, params={"limit": 100})
    saved = next(item for item in history.json()["data"] if item["question_id"] == question_id)
    assert saved["user_response"] == answer_text
    assert saved["score_percentage"] is None


async def quiz_candidate(client):
    email = f"zz_test_quiz_{uuid.uuid4()}@example.com"
    password = "ZzTestQuiz123!"
    registered = await client.post("/api/v1/auth/register", json={
        "email": email, "password": password, "full_name": "zz_test Synthetic Quiz Candidate",
    })
    assert registered.status_code == 201, registered.text
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    headers = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}
    profile_response = await client.get("/api/v1/candidates/profile", headers=headers)
    assert profile_response.status_code == 200, profile_response.text
    profile_id = uuid.UUID(profile_response.json()["data"]["id"])
    async with AsyncSessionLocal() as db:
        industry = await db.scalar(select(Industry).where(Industry.is_active.is_(True)).order_by(Industry.id).limit(1))
        assert industry is not None
        profile = await db.get(CandidateProfile, profile_id)
        profile.industry_id = industry.id
        profile.target_role = "Software Engineer"
        profile.total_experience_months = 24
        profile.key_skills = ["Python", "PostgreSQL"]
        await db.commit()
        return headers, profile_id, industry.id


async def quiz_bank_question(db, industry_id, topic, **overrides):
    values = dict(
        id=uuid.uuid4(), industry_id=industry_id, subject="zz_test Quiz SQL", topic=topic,
        question_text=f"zz_test {uuid.uuid4()}: how are atomic database updates committed?",
        question_type=QuestionType.MCQ_SINGLE, difficulty=DifficultyLevel.BEGINNER,
        interview_round="Practice", source_provenance=SourceProvenance.EDITORIALLY_REVIEWED,
        approval_status=ApprovalStatus.APPROVED, workflow_status="published",
        expected_answer="All changes commit or roll back together.", explanation="Atomicity prevents partial changes.",
        evaluation_rubric={"concepts": ["atomicity"]},
        options=[{"id": "A", "text": "Commit or roll back together", "is_correct": True},
                 {"id": "B", "text": "Always apply partial changes", "is_correct": False}],
    )
    values.update(overrides)
    question = Question(**values)
    db.add(question)
    await db.flush()
    question.root_question_id = question.id
    return question


def quiz_provider_payload(topic="zz_test Quiz"):
    return {"questions": [
        {"question_type": "mcq_single", "difficulty": "beginner", "subject": topic, "topic": topic,
         "question_text": "Which property prevents partially committed database changes?",
         "expected_answer": "Atomicity", "explanation": "Atomicity makes a transaction indivisible.",
         "evaluation_rubric": {"concepts": ["atomicity"]},
         "options": [{"id": "A", "text": "Atomicity", "is_correct": True},
                     {"id": "B", "text": "Partial writes", "is_correct": False}]},
        {"question_type": "short_answer", "difficulty": "beginner", "subject": topic, "topic": topic,
         "question_text": "Explain why a transaction should roll back after a failure.",
         "expected_answer": "Rollback avoids partially applied changes.",
         "explanation": "Atomic changes preserve consistency.",
         "evaluation_rubric": {"concepts": ["rollback", "atomicity"]}, "options": []},
    ]}


@pytest.mark.asyncio
async def test_authenticated_quiz_persists_keys_for_saved_answers_and_is_tenant_isolated(async_client, monkeypatch):
    headers, profile_id, industry_id = await quiz_candidate(async_client)
    other_headers, _, _ = await quiz_candidate(async_client)
    topic = f"zz_test_generated_quiz_{uuid.uuid4()}"
    payload = quiz_provider_payload(topic)
    provider = type("MockProvider", (), {})()
    provider.is_available = lambda: True
    provider.generate_structured = AsyncMock(return_value=AIResponse(provider_name="test-double", structured_data=payload))
    provider.generate_text = AsyncMock(return_value=AIResponse(provider_name="test-double", raw_text=json.dumps({
        "score_awarded": 100, "accuracy_score": 10, "completeness_score": 10, "conceptual_clarity_score": 10,
        "strengths": ["Atomicity"], "gaps": [], "detailed_feedback": "Correct rollback reasoning.",
    })))
    monkeypatch.setattr(assessment_service, "get_ai_provider", lambda: provider)
    unauthenticated = await async_client.post("/api/v1/testing/quiz", json={"topic": topic, "num_questions": 2})
    assert unauthenticated.status_code in (401, 403)
    response = await async_client.post("/api/v1/testing/quiz", headers=headers, json={"topic": topic, "num_questions": 2})
    assert response.status_code == 200, response.text
    quiz = response.json()["data"]
    assert quiz["understanding_percentage"] is None and quiz["sample_count"] == 0
    assert quiz["suggested_difficulty"] == "beginner" and quiz["experience_band"] == "2-5 years"
    assert quiz["generated_count"] == 2 and quiz["based_on_approved"] == 0
    assert len({item["id"] for item in quiz["questions"]}) == 2
    assert (datetime.fromisoformat(quiz["ends_at"]) - datetime.fromisoformat(quiz["started_at"])).total_seconds() == 360
    assert all(item["expected_answer"] is None and item["source_provenance"] == "ai_generated_unreviewed"
               and all("is_correct" not in option for option in item["options"]) for item in quiz["questions"])
    assert "Atomicity makes" not in response.text and "concepts" not in response.text
    prompt = provider.generate_structured.await_args.args[0]
    assert "Software Engineer" in prompt and "Python" in prompt and "PostgreSQL" in prompt
    assert "2-5 years" in prompt
    assessment_id, attempt_id = quiz["assessment_id"], quiz["attempt_id"]
    async with AsyncSessionLocal() as db:
        assessment = await db.get(Assessment, uuid.UUID(assessment_id))
        attempt = await db.get(AssessmentAttempt, uuid.UUID(attempt_id))
        assert assessment.candidate_profile_id == attempt.candidate_profile_id == profile_id
        assert assessment.industry_id == industry_id and assessment.duration_minutes == 6
        links = (await db.scalars(select(AssessmentQuestion).where(AssessmentQuestion.assessment_id == assessment.id)
                                  .order_by(AssessmentQuestion.order_index))).all()
        assert [str(link.question_id) for link in links] == [item["id"] for item in quiz["questions"]]
        for index, item in enumerate(quiz["questions"]):
            stored = await db.get(Question, uuid.UUID(item["id"]))
            assert stored.expected_answer == payload["questions"][index]["expected_answer"]
            assert stored.options == payload["questions"][index]["options"]
            assert stored.evaluation_rubric == payload["questions"][index]["evaluation_rubric"]
            assert stored.workflow_status == "draft" and stored.approval_status == ApprovalStatus.PENDING
            assert "assessment_only" in stored.tags
    resumed = await async_client.post(f"/api/v1/testing/{assessment_id}/start", headers=headers)
    assert resumed.status_code == 200, resumed.text
    assert resumed.json()["data"]["attempt_id"] == attempt_id
    assert all(item["evaluation_rubric"] == {} for item in resumed.json()["data"]["questions"])
    assert (await async_client.post(f"/api/v1/testing/{assessment_id}/start", headers=other_headers)).status_code == 404
    for item in quiz["questions"]:
        for candidate in (headers, other_headers):
            assert (await async_client.get(f"/api/v1/questions/{item['id']}", headers=candidate)).status_code == 404
            assert (await async_client.post(f"/api/v1/questions/{item['id']}/practice", headers=candidate,
                                           json={"user_response": "A"})).status_code == 404
        answer = {"question_id": item["id"], "selected_options": ["A"]} if item["options"] else {
            "question_id": item["id"], "text_response": "Rollback avoids partially applied changes."}
        assert (await async_client.post(f"/api/v1/testing/attempts/{attempt_id}/save-answer", headers=other_headers,
                                       json=answer)).status_code == 404
        saved = await async_client.post(f"/api/v1/testing/attempts/{attempt_id}/save-answer", headers=headers, json=answer)
        assert saved.status_code == 200 and saved.json()["data"]["saved"] is True, saved.text
        assert "expected_answer" not in saved.text
    assert (await async_client.get(f"/api/v1/testing/attempts/{attempt_id}/results", headers=other_headers)).status_code == 404
    assert (await async_client.post(f"/api/v1/testing/attempts/{attempt_id}/submit", headers=other_headers)).status_code == 404
    submitted = await async_client.post(f"/api/v1/testing/attempts/{attempt_id}/submit", headers=headers)
    assert submitted.status_code == 200, submitted.text
    result = submitted.json()["data"]
    assert result["percentage"] == 100 and result["correct_count"] == 2
    assert [item["expected_answer"] for item in result["question_feedback"]] == [item["expected_answer"] for item in payload["questions"]]
    provider.generate_text.assert_awaited_once()
    assert "Rollback avoids partially applied changes." in provider.generate_text.await_args.kwargs["prompt"]
    fetched = await async_client.get(f"/api/v1/testing/attempts/{attempt_id}/results", headers=headers)
    assert fetched.status_code == 200 and fetched.json()["data"] == result
    assert (await async_client.get(f"/api/v1/testing/attempts/{attempt_id}/results", headers=other_headers)).status_code == 404
    other_history = await async_client.get("/api/v1/testing/history", headers=other_headers)
    assert all(item["id"] != attempt_id for item in other_history.json()["data"])
    async with AsyncSessionLocal() as db:
        answers = (await db.scalars(select(CandidateAnswer).where(CandidateAnswer.assessment_attempt_id == uuid.UUID(attempt_id)))).all()
        assert len(answers) == 2 and all(answer.score_awarded == 10 for answer in answers)


@pytest.mark.asyncio
@pytest.mark.parametrize(("score", "difficulty"), [(None, "beginner"), (20, "beginner"), (60, "intermediate"), (90, "advanced")])
async def test_quiz_filters_exact_topic_and_valid_deterministic_scores_before_recent_limit(
    async_client, monkeypatch, score, difficulty,
):
    headers, profile_id, industry_id = await quiz_candidate(async_client)
    _, other_id, _ = await quiz_candidate(async_client)
    topic = f"zz_test_Exact_%_SQL_{uuid.uuid4()}"
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        selected = await quiz_bank_question(db, industry_id, topic.upper(), difficulty=DifficultyLevel(difficulty))
        wrong_difficulty = await quiz_bank_question(db, industry_id, topic,
            difficulty=DifficultyLevel.ADVANCED if difficulty != "advanced" else DifficultyLevel.BEGINNER)
        unapproved = await quiz_bank_question(db, industry_id, topic, difficulty=DifficultyLevel(difficulty), approval_status=ApprovalStatus.PENDING)
        archived = await quiz_bank_question(db, industry_id, topic, difficulty=DifficultyLevel(difficulty), is_archived=True)
        private = await quiz_bank_question(db, industry_id, topic, difficulty=DifficultyLevel(difficulty), tags=["assessment_only"])
        unrelated = await quiz_bank_question(db, industry_id, topic + " extra")
        for index in range(25):
            db.add(QuestionPracticeLog(candidate_profile_id=profile_id, question_id=selected.id, user_response="A",
                score_percentage=score if index < 20 else 100 - score, evaluation_status="evaluated",
                evaluation_provenance="deterministic", created_at=now - timedelta(days=1, minutes=index)))
        # More than 20 newer unrelated/invalid rows must not crowd out the actual topic sample.
        for index in range(25):
            db.add(QuestionPracticeLog(candidate_profile_id=profile_id, question_id=unrelated.id, user_response="A",
                score_percentage=100, evaluation_status="evaluated", evaluation_provenance="deterministic",
                created_at=now - timedelta(minutes=index)))
        for provenance, status, invalid_score in [("ai", "evaluated", 100), ("none", "evaluated", 100),
                ("deterministic", "unavailable", 100), ("deterministic", "evaluated", None),
                ("deterministic", "evaluated", -1), ("deterministic", "evaluated", 101)]:
            db.add(QuestionPracticeLog(candidate_profile_id=profile_id, question_id=selected.id, user_response="A",
                score_percentage=invalid_score, evaluation_status=status, evaluation_provenance=provenance, created_at=now))
        db.add(QuestionPracticeLog(candidate_profile_id=other_id, question_id=selected.id, user_response="A",
            score_percentage=100, evaluation_status="evaluated", evaluation_provenance="deterministic", created_at=now))
        await db.commit()
        selected_id = str(selected.id)
    generator = AsyncMock(side_effect=AssertionError("The eligible bank must fill this quiz"))
    monkeypatch.setattr(assessment_service.AssessmentService, "generate_assessment_questions", generator)
    response = await async_client.post("/api/v1/testing/quiz", headers=headers, json={"topic": topic.lower(), "num_questions": 1})
    assert response.status_code == 200, response.text
    quiz = response.json()["data"]
    assert quiz["understanding_percentage"] == score and quiz["sample_count"] == 20
    assert quiz["suggested_difficulty"] == difficulty
    assert [item["id"] for item in quiz["questions"]] == [selected_id]
    assert quiz["based_on_approved"] == 1 and quiz["generated_count"] == 0
    assert quiz["questions"][0]["source_provenance"] == "published_question_bank"
    generator.assert_not_awaited()


@pytest.mark.asyncio
async def test_practice_cannot_reveal_active_quiz_bank_keys_and_does_not_leak_other_tenants(async_client, monkeypatch):
    headers, _, industry_id = await quiz_candidate(async_client)
    other_headers, _, _ = await quiz_candidate(async_client)
    topic = f"zz_test_practice_quiz_{uuid.uuid4()}"
    async with AsyncSessionLocal() as db:
        question = await quiz_bank_question(db, industry_id, topic)
        question_id = str(question.id)
        await db.commit()
    generator = AsyncMock(side_effect=AssertionError("This quiz is bank-only"))
    monkeypatch.setattr(assessment_service.AssessmentService, "generate_assessment_questions", generator)
    response = await async_client.post("/api/v1/testing/quiz", headers=headers, json={"topic": topic, "num_questions": 1})
    assert response.status_code == 200, response.text
    quiz = response.json()["data"]
    blocked = await async_client.post(f"/api/v1/questions/{question_id}/practice", headers=headers, json={"user_response": "B"})
    assert blocked.status_code == 409 and "All changes commit" not in blocked.text
    other = await async_client.post(f"/api/v1/questions/{question_id}/practice", headers=other_headers, json={"user_response": "A"})
    assert other.status_code == 200 and other.json()["data"]["score_percentage"] == 100
    assert (await async_client.post(f"/api/v1/testing/attempts/{quiz['attempt_id']}/submit", headers=headers)).status_code == 200
    allowed = await async_client.post(f"/api/v1/questions/{question_id}/practice", headers=headers, json={"user_response": "A"})
    assert allowed.status_code == 200
    # Correct practice now suggests advanced; keep a matching bank item for the new session.
    async with AsyncSessionLocal() as db:
        question = await db.get(Question, uuid.UUID(question_id))
        question.difficulty = DifficultyLevel.ADVANCED
        await db.commit()
    second = await async_client.post("/api/v1/testing/quiz", headers=headers, json={"topic": topic, "num_questions": 1})
    assert second.status_code == 200, second.text
    expired_id = second.json()["data"]["attempt_id"]
    async with AsyncSessionLocal() as db:
        attempt = await db.get(AssessmentAttempt, uuid.UUID(expired_id))
        attempt.started_at = datetime.now(timezone.utc) - timedelta(minutes=6)
        assert attempt.status == AttemptStatus.IN_PROGRESS
        await db.commit()
    expired_practice = await async_client.post(f"/api/v1/questions/{question_id}/practice", headers=headers, json={"user_response": "A"})
    assert expired_practice.status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize("workflow", ["draft", "approved", "published", "archived"])
async def test_assessment_only_tags_block_management_exposure_and_promotion(async_client, admin_headers, workflow):
    headers, _, industry_id = await quiz_candidate(async_client)
    topic = f"zz_test_private_management_{uuid.uuid4()}"
    async with AsyncSessionLocal() as db:
        public = await quiz_bank_question(db, industry_id, topic + " public")
        private = await quiz_bank_question(db, industry_id, topic, tags=["ai_generated", "assessment_only"],
            workflow_status=workflow, approval_status=ApprovalStatus.APPROVED,
            is_archived=workflow == "archived", version_number=2)
        private.root_question_id = public.id  # Even a private revision attached to a public root is hidden.
        await db.commit()
        question_id, public_id = str(private.id), str(public.id)
    managed = await async_client.get("/api/v1/questions/manage", headers=admin_headers, params={"search": topic})
    assert managed.status_code == 200, managed.text
    assert [item["id"] for item in managed.json()["data"]] == [public_id]
    assert managed.json()["meta"]["total"] == 1
    assert (await async_client.get(f"/api/v1/questions/{question_id}", headers=headers)).status_code == 404
    bank = await async_client.get("/api/v1/questions", headers=headers, params={"search": topic})
    assert all(item["id"] != question_id for item in bank.json()["data"])
    assert (await async_client.post(f"/api/v1/questions/{question_id}/bookmark", headers=headers)).status_code == 404
    assert (await async_client.post(f"/api/v1/questions/{question_id}/practice", headers=headers, json={"user_response": "A"})).status_code == 404
    for action, body in [("submit", None), ("review", {"decision": "approved"}), ("publish", None)]:
        denied = await async_client.post(f"/api/v1/questions/manage/{question_id}/{action}", headers=admin_headers, json=body)
        assert denied.status_code == 404, denied.text
        assert "All changes commit" not in denied.text
    update = await async_client.patch(f"/api/v1/questions/manage/{question_id}", headers=admin_headers, json={"tags": []})
    assert update.status_code == 404, update.text
    assert (await async_client.get(f"/api/v1/questions/manage/{question_id}/versions", headers=admin_headers)).status_code == 404
    versions = await async_client.get(f"/api/v1/questions/manage/{public_id}/versions", headers=admin_headers)
    assert versions.status_code == 200 and [item["id"] for item in versions.json()["data"]] == [public_id]
    for root in (question_id, public_id):
        restore = await async_client.post(f"/api/v1/questions/manage/{root}/restore/{question_id}", headers=admin_headers)
        assert restore.status_code == 404, restore.text
    async with AsyncSessionLocal() as db:
        private = await db.get(Question, uuid.UUID(question_id))
        assert private.workflow_status == workflow and "assessment_only" in private.tags


@pytest.mark.asyncio
@pytest.mark.parametrize("output", [None, {"questions": []}, {"questions": quiz_provider_payload()["questions"][:1]}])
async def test_invalid_or_unavailable_quiz_provider_never_persists_partial_sessions(async_client, monkeypatch, output):
    headers, profile_id, _ = await quiz_candidate(async_client)
    provider = type("MockProvider", (), {})()
    provider.is_available = lambda: output is not None
    provider.generate_structured = AsyncMock(return_value=AIResponse(provider_name="test-double", structured_data=output))
    monkeypatch.setattr(assessment_service, "get_ai_provider", lambda: provider)
    topic = f"zz_test_invalid_quiz_{uuid.uuid4()}"
    response = await async_client.post("/api/v1/testing/quiz", headers=headers, json={"topic": topic, "num_questions": 2})
    assert response.status_code == 503, response.text
    async with AsyncSessionLocal() as db:
        assert await db.scalar(select(func.count(Assessment.id)).where(Assessment.candidate_profile_id == profile_id)) == 0
        assert await db.scalar(select(func.count(Question.id)).where(Question.topic == topic)) == 0
