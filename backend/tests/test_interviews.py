import pytest
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from httpx import AsyncClient
from app.services import interview_service


class UnavailableProvider:
    def is_available(self) -> bool:
        return False


def test_final_interview_report_pairs_saved_and_refined_answers_after_completion():
    interview_id = uuid.uuid4()
    interview = SimpleNamespace(
        id=interview_id,
        completed_at=datetime.now(timezone.utc),
        questions=[SimpleNamespace(
            order_index=1,
            question_text="How would you approach the problem?",
            response=SimpleNamespace(candidate_answer="I would test the failure path.")
        )],
    )
    evaluation = SimpleNamespace(
        id=uuid.uuid4(), mock_interview_id=interview_id, overall_score=80,
        technical_score=80, domain_score=80, communication_score=80, structure_score=80,
        evaluation_status="evaluated", evaluation_provenance="ai", key_strengths=[],
        improvement_areas=[], detailed_feedback={},
        question_evaluations=[{"question_number": 1, "refined_answer": "I would define and test failure paths."}],
    )

    report = interview_service.InterviewService._report(interview, evaluation)

    assert len(report.responses) == 1
    assert report.responses[0].question == "How would you approach the problem?"
    assert report.responses[0].candidate_answer == "I would test the failure path."
    assert report.responses[0].refined_answer == "I would define and test failure paths."


@pytest.mark.asyncio
async def test_mock_interview_uses_gemini_questions_when_bank_has_no_match(async_client: AsyncClient, candidate_headers: dict, monkeypatch):
    class GeneratedQuestionProvider:
        def is_available(self) -> bool:
            return True

        async def generate_structured(self, **kwargs):
            return type("Response", (), {
                "is_success": True,
                "structured_data": {"questions": [
                    {"question_text": "How would you design a reliable service for this role?"},
                    {"question_text": "Describe how you would investigate a production performance issue."},
                ]},
            })()

    monkeypatch.setattr(interview_service, "get_ai_provider", lambda: GeneratedQuestionProvider())
    candidate = (await async_client.get("/api/v1/candidates/profile", headers=candidate_headers)).json()["data"]
    unique_round = f"zz_test_round_{uuid.uuid4().hex}"
    started = await async_client.post("/api/v1/interviews/setup", headers=candidate_headers, json={
        "industry_id": candidate["industry_id"], "job_role": "zz_test Platform Engineer",
        "interview_round": unique_round, "number_of_questions": 2, "duration_minutes": 20, "mode": "text",
    })

    assert started.status_code == 201, started.text
    session = started.json()["data"]
    assert session["ai_status"] == "ai_generated"
    assert session["interviewer_message"] == "How would you design a reliable service for this role?"
    resumed = await async_client.get(f"/api/v1/interviews/{session['id']}", headers=candidate_headers)
    assert resumed.status_code == 200
    assert resumed.json()["data"]["ai_status"] == "ai_generated"
    assert resumed.json()["data"]["interviewer_message"] == session["interviewer_message"]

    answered = await async_client.post(f"/api/v1/interviews/{session['id']}/respond", headers=candidate_headers, json={
        "candidate_answer": "I would define availability goals, add health checks, and test recovery paths.",
    })
    assert answered.status_code == 200, answered.text
    assert answered.json()["data"]["ai_status"] == "ai_generated"
    assert answered.json()["data"]["interviewer_message"] == "Describe how you would investigate a production performance issue."


@pytest.mark.asyncio
async def test_mock_interview_lifecycle(async_client: AsyncClient, candidate_headers: dict, admin_headers: dict, monkeypatch):
    monkeypatch.setattr(interview_service, "get_ai_provider", lambda: UnavailableProvider())
    candidate = (await async_client.get("/api/v1/candidates/profile", headers=candidate_headers)).json()["data"]
    industry = (await async_client.get("/api/v1/industries")).json()["data"]
    selected_industry = next(item for item in industry if item["id"] == candidate["industry_id"])
    role = next((item for item in selected_industry["job_roles"] if item["title"].lower() == "software engineer"), None)
    run_id = uuid.uuid4()
    for suffix in ("a", "b"):
        create = await async_client.post("/api/v1/questions", headers=admin_headers, json={
            "question_text": f"Interview lifecycle test {run_id} question {suffix}: explain a design decision.",
            "question_type": "short_answer", "industry_id": candidate["industry_id"],
            "job_role_id": role["id"] if role else None, "subject": "Interview testing",
            "topic": f"Interview test {suffix}", "difficulty": "intermediate",
            "interview_round": "Technical", "expected_answer": "Describe the trade-offs and evidence.",
            "source_provenance": "editorially_reviewed", "approval_status": "pending"
        })
        assert create.status_code == 201
        question_id = create.json()["data"]["id"]
        approved = await async_client.post(f"/api/v1/questions/manage/{question_id}/review", headers=admin_headers, json={"decision": "approved"})
        assert approved.status_code == 200
        # Approval is a review decision; candidate interview pools only include
        # content explicitly published by an administrator.
        if suffix == "a":
            unpublished_setup = await async_client.post(
                "/api/v1/interviews/setup", headers=candidate_headers,
                json={"job_role": "Software Engineer", "interview_round": "Technical",
                      "duration_minutes": 20, "number_of_questions": 1, "mode": "text"},
            )
            assert unpublished_setup.status_code == 201
            # There may be other published seed content in the test database;
            # the approved-but-unpublished draft itself must never be selected.
            assert unpublished_setup.json()["data"]["interviewer_message"] != create.json()["data"]["question_text"]
        published = await async_client.post(f"/api/v1/questions/manage/{question_id}/publish", headers=admin_headers)
        assert published.status_code == 200
    # 1. Setup Mock Interview
    setup_res = await async_client.post(
        "/api/v1/interviews/setup",
        headers=candidate_headers,
        json={
            "job_role": "Software Engineer",
            "target_company": "Google",
            "interview_round": "Technical",
            "difficulty": "Intermediate",
            "duration_minutes": 20,
            "number_of_questions": 2,
            "mode": "text"
        }
    )
    assert setup_res.status_code == 201
    interview = setup_res.json()["data"]
    interview_id = interview["id"]
    assert "interviewer_message" in interview
    assert interview["current_question_index"] == 1
    resumed_res = await async_client.get(f"/api/v1/interviews/{interview_id}", headers=candidate_headers)
    assert resumed_res.status_code == 200
    assert resumed_res.json()["data"]["current_question_id"] == interview["current_question_id"]

    # 2. Respond to Question 1
    respond_res = await async_client.post(
        f"/api/v1/interviews/{interview_id}/respond",
        headers=candidate_headers,
        json={
            "candidate_answer": "I have 3 years of experience building Python and React applications, with a focus on asynchronous microservices, PostgreSQL query performance, and Docker containers.",
            "duration_seconds": 45
        }
    )
    assert respond_res.status_code == 200
    next_data = respond_res.json()["data"]
    assert next_data["id"] == interview_id
    assert next_data["current_question_index"] == 2
    assert next_data["ai_status"] == "question_bank"
    next_res = await async_client.post(f"/api/v1/interviews/{interview_id}/respond", headers=candidate_headers, json={"candidate_answer": "I compared the alternatives, documented the trade-offs, and verified performance with measurements."})
    assert next_res.status_code == 200
    next_data = next_res.json()["data"]
    assert next_data["mock_interview_id"] == interview_id
    assert next_data["evaluation_status"] == "unavailable"
    assert next_data["overall_score"] is None
    assert next_data["detailed_feedback"]

    # 3. Conclude Interview & View Report
    conclude_res = await async_client.post(
        f"/api/v1/interviews/{interview_id}/conclude",
        headers=candidate_headers
    )
    assert conclude_res.status_code == 200
    report = conclude_res.json()["data"]
    assert report["evaluation_status"] == "unavailable"
    assert report["overall_score"] is None
    assert report["mock_interview_id"] == interview_id
    assert "key_strengths" in report
    assert "improvement_areas" in report
