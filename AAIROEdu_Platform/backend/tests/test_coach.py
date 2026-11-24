import pytest
import json
from httpx import AsyncClient
from uuid import uuid4
from app.services import coach_service
from app.integrations.ai.base import AIResponse


class UnavailableProvider:
    def is_available(self) -> bool:
        return False


class RecordingCoachProvider:
    def __init__(self, raw_text: str):
        self.raw_text = raw_text
        self.prompt = ""

    def is_available(self) -> bool:
        return True

    async def generate_text(self, prompt: str, **_kwargs) -> AIResponse:
        self.prompt = prompt
        return AIResponse(raw_text=self.raw_text, provider_name="test-only", model_name="test-only")


@pytest.mark.asyncio
async def test_coach_skill_gap_and_chat(async_client: AsyncClient, candidate_headers: dict, admin_headers: dict, monkeypatch):
    monkeypatch.setattr(coach_service, "get_ai_provider", lambda: UnavailableProvider())
    # Own the content prerequisite rather than depend on the shared demo profile's
    # current role or on general modules substituting for target-role guidance.
    profile = (await async_client.get("/api/v1/candidates/profile", headers=candidate_headers)).json()["data"]
    role_name = f"zz_test_coach_role_{uuid4().hex}"
    role = await async_client.post("/api/v1/question-taxonomy/manage", headers=admin_headers, json={
        "kind": "job_role", "name": role_name, "industry_id": profile["industry_id"],
    })
    assert role.status_code == 201, role.text
    module = await async_client.post("/api/v1/modules/manage", headers=admin_headers, json={
        "industry_id": profile["industry_id"], "title": f"zz_test_coach_module_{uuid4().hex}",
        "description": "Synthetic target-role learning for the coach API regression.",
        "job_role_ids": [role.json()["data"]["id"]],
    })
    assert module.status_code == 201, module.text
    module_id = module.json()["data"]["id"]
    lesson = await async_client.post(f"/api/v1/modules/manage/{module_id}/lessons", headers=admin_headers, json={
        "title": "Synthetic coach lesson", "content": "Target-role learning and practice.",
    })
    assert lesson.status_code == 201, lesson.text
    published = await async_client.patch(f"/api/v1/modules/manage/{module_id}", headers=admin_headers, json={
        "is_published": True,
    })
    assert published.status_code == 200, published.text
    saved_profile = await async_client.post("/api/v1/candidates/onboarding/step", headers=candidate_headers, json={
        "step": 6, "target_role": role_name,
    })
    assert saved_profile.status_code == 200, saved_profile.text
    # 1. Skill Gap Analysis
    sg_res = await async_client.get("/api/v1/coach/skill-gap", headers=candidate_headers)
    assert sg_res.status_code == 200
    sg = sg_res.json()["data"]
    assert "strong_skills" in sg
    assert "learning_priorities" in sg
    assert sg["ai_status"] in {"unavailable", "insufficient_profile"}
    assert sg["strong_skills"] == []
    assert sg["missing_skills"] == []

    # 2. Generate Roadmap
    road_res = await async_client.post("/api/v1/coach/roadmap/generate", headers=candidate_headers)
    assert road_res.status_code == 200
    roadmap = road_res.json()["data"]
    assert "tasks" in roadmap
    assert len(roadmap["tasks"]) > 0
    assert all(task["module_id"] for task in roadmap["tasks"])
    assert any(task["module_id"] == module_id for task in roadmap["tasks"])
    assert all(not task["is_completed"] for task in roadmap["tasks"])

    # 3. Chat with Coach
    chat_res = await async_client.post(
        "/api/v1/coach/chat",
        headers=candidate_headers,
        json={"message": "How do I best structure my answers for system design interviews?"}
    )
    assert chat_res.status_code == 200
    chat_data = chat_res.json()["data"]
    assert "reply" in chat_data
    assert chat_data["ai_status"] == "unavailable"
    assert chat_data["reply"] is None
    conversation = await async_client.get(f"/api/v1/coach/conversations/{chat_data['conversation_id']}", headers=candidate_headers)
    assert conversation.status_code == 200
    assert [message["message_text"] for message in conversation.json()["data"]["messages"]] == [
        "How do I best structure my answers for system design interviews?"
    ]

    registered = await async_client.post("/api/v1/auth/register", json={
        "email": f"coach-isolation-{uuid4()}@example.com",
        "password": "DifferentPass123!",
        "full_name": "Other Candidate",
    })
    assert registered.status_code == 201
    other_login = await async_client.post("/api/v1/auth/login", json={
        "email": registered.json()["data"]["email"],
        "password": "DifferentPass123!",
    })
    assert other_login.status_code == 200
    other_headers = {"Authorization": f"Bearer {other_login.json()['data']['access_token']}"}
    other_view = await async_client.get(f"/api/v1/coach/conversations/{chat_data['conversation_id']}", headers=other_headers)
    assert other_view.status_code == 404


@pytest.mark.asyncio
async def test_roadmap_matches_profile_role_and_skills_and_refreshes_after_profile_change(
    async_client: AsyncClient, candidate_headers: dict, admin_headers: dict,
):
    profile = (await async_client.get("/api/v1/candidates/profile", headers=candidate_headers)).json()["data"]
    role_name = f"Roadmap role {uuid4()}"
    skill_name = f"Roadmap skill {uuid4()}"
    other_role_name = f"Other roadmap role {uuid4()}"
    role = await async_client.post("/api/v1/question-taxonomy/manage", headers=admin_headers, json={
        "kind": "job_role", "name": role_name, "industry_id": profile["industry_id"],
    })
    skill = await async_client.post("/api/v1/question-taxonomy/manage", headers=admin_headers, json={
        "kind": "skill", "name": skill_name,
    })
    other_role = await async_client.post("/api/v1/question-taxonomy/manage", headers=admin_headers, json={
        "kind": "job_role", "name": other_role_name, "industry_id": profile["industry_id"],
    })
    assert role.status_code == skill.status_code == other_role.status_code == 201

    saved_profile = await async_client.post("/api/v1/candidates/onboarding/step", headers=candidate_headers, json={
        "step": 6, "target_role": role_name, "key_skills": [skill_name],
    })
    assert saved_profile.status_code == 200, saved_profile.text

    async def publish_module(title: str, role_id: str):
        created = await async_client.post("/api/v1/modules/manage", headers=admin_headers, json={
            "industry_id": profile["industry_id"], "title": title,
            "description": "Roadmap role and skill filter regression.",
            "job_role_ids": [role_id], "skill_ids": [skill.json()["data"]["id"]],
        })
        assert created.status_code == 201, created.text
        module_id = created.json()["data"]["id"]
        lesson = await async_client.post(f"/api/v1/modules/manage/{module_id}/lessons", headers=admin_headers, json={
            "title": "Roadmap lesson", "content": "Published lesson for deterministic roadmap selection.",
        })
        assert lesson.status_code == 201, lesson.text
        published = await async_client.patch(f"/api/v1/modules/manage/{module_id}", headers=admin_headers, json={
            "is_published": True,
        })
        assert published.status_code == 200, published.text
        return module_id

    matching_id = await publish_module(f"Matching roadmap module {uuid4()}", role.json()["data"]["id"])
    excluded_id = await publish_module(f"Excluded roadmap module {uuid4()}", other_role.json()["data"]["id"])

    generated = await async_client.post("/api/v1/coach/roadmap/generate", headers=candidate_headers)
    assert generated.status_code == 200, generated.text
    roadmap = generated.json()["data"]
    assert "self-reported skills" in roadmap["description"]
    assert "deterministic" in roadmap["description"]
    assert any(task["module_id"] == matching_id for task in roadmap["tasks"])
    assert all(task["module_id"] != excluded_id for task in roadmap["tasks"])

    old_task = next(task for task in roadmap["tasks"] if task["module_id"] == matching_id)
    completed = await async_client.post(f"/api/v1/modules/roadmap/tasks/{old_task['id']}/toggle", headers=candidate_headers)
    assert completed.status_code == 200, completed.text
    await async_client.post("/api/v1/candidates/onboarding/step", headers=candidate_headers, json={
        "step": 6, "target_role": other_role_name, "key_skills": [skill_name],
    })
    refreshed = await async_client.post("/api/v1/coach/roadmap/generate", headers=candidate_headers)
    assert refreshed.status_code == 200, refreshed.text
    assert refreshed.json()["data"]["id"] != roadmap["id"]
    assert all(task["module_id"] != matching_id for task in refreshed.json()["data"]["tasks"])


@pytest.mark.asyncio
async def test_skill_analysis_uses_published_requirements_and_saved_practice_provenance(
    async_client: AsyncClient, candidate_headers: dict, admin_headers: dict, monkeypatch,
):
    profile = (await async_client.get("/api/v1/candidates/profile", headers=candidate_headers)).json()["data"]
    role_name = f"Evidence role {uuid4()}"
    skill_name = f"Evidence skill {uuid4()}"
    role = await async_client.post("/api/v1/question-taxonomy/manage", headers=admin_headers, json={
        "kind": "job_role", "name": role_name, "industry_id": profile["industry_id"],
    })
    skill = await async_client.post("/api/v1/question-taxonomy/manage", headers=admin_headers, json={
        "kind": "skill", "name": skill_name,
    })
    assert role.status_code == skill.status_code == 201
    role_id = role.json()["data"]["id"]
    skill_id = skill.json()["data"]["id"]
    saved_profile = await async_client.post("/api/v1/candidates/onboarding/step", headers=candidate_headers, json={
        "step": 6, "target_role": role_name, "key_skills": [skill_name],
    })
    assert saved_profile.status_code == 200, saved_profile.text

    question = await async_client.post("/api/v1/questions", headers=admin_headers, json={
        "question_text": f"Which option best demonstrates {skill_name}?",
        "question_type": "mcq_single", "industry_id": profile["industry_id"],
        "job_role_id": role_id, "job_role_ids": [role_id], "skill_ids": [skill_id],
        "subject": "Evidence-backed coaching", "topic": "Saved question performance",
        "difficulty": "intermediate", "interview_round": "Technical",
        "options": [
            {"id": "A", "text": "The correct evidence-backed option", "is_correct": True},
            {"id": "B", "text": "An unsupported option", "is_correct": False},
        ], "source_provenance": "editorially_reviewed",
    })
    assert question.status_code == 201, question.text
    question_id = question.json()["data"]["id"]
    assert (await async_client.post(f"/api/v1/questions/manage/{question_id}/review", headers=admin_headers,
        json={"decision": "approved"})).status_code == 200
    assert (await async_client.post(f"/api/v1/questions/manage/{question_id}/publish", headers=admin_headers)).status_code == 200
    practice = await async_client.post(f"/api/v1/questions/{question_id}/practice", headers=candidate_headers,
        json={"user_response": "A"})
    assert practice.status_code == 200, practice.text
    assert practice.json()["data"]["evaluation_provenance"] == "deterministic"

    provider = RecordingCoachProvider(json.dumps({
        "strong_skills": [skill_name], "weak_skills": [], "missing_skills": [],
        "technical_gaps": [], "domain_gaps": [],
        "skill_evidence": {skill_name: "saved objective practice evidence"},
        "learning_priorities": [], "coach_summary": "This recommendation uses the saved evidence.",
    }))
    monkeypatch.setattr(coach_service, "get_ai_provider", lambda: provider)
    response = await async_client.get("/api/v1/coach/skill-gap", headers=candidate_headers)
    assert response.status_code == 200, response.text
    result = response.json()["data"]
    assert result["ai_status"] == "ai_generated"
    assert "saved evaluated question practice" in result["evidence_sources"]
    assert "published module and question skill taxonomy" in result["evidence_sources"]
    assert "Saved question practice score 100% (deterministic)" in result["skill_evidence"][skill_name]
    assert "Self-reported by candidate" in result["skill_evidence"][skill_name]
    assert skill_name in provider.prompt
    assert '"evaluation_provenance": "deterministic"' in provider.prompt
