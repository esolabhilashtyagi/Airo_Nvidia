import uuid

import pytest
from httpx import AsyncClient

from app.integrations.ai.base import AIResponse
from app.core.config import settings
from app.integrations.ai.gemini_provider import GeminiProvider
from app.services import question_service


class StructuredDraftProvider:
    def __init__(self, result: AIResponse, available: bool = True):
        self.result = result
        self.available = available
        self.prompt = ""

    def is_available(self) -> bool:
        return self.available

    async def generate_structured(self, prompt, response_schema):
        self.prompt = prompt
        return self.result


def valid_draft(question_text: str) -> AIResponse:
    return AIResponse(is_success=True, provider_name="test-double", model_name="test-only", structured_data={
        "question_text": question_text,
        "expected_answer": "An acceptable response explains the concept and supports it with evidence.",
        "explanation": "Editorial review is required before publication.",
        "options": [],
        "evaluation_rubric": {"clarity": "Explain the reasoning clearly."},
    })


async def draft_brief(async_client: AsyncClient, candidate_headers: dict, admin_headers: dict) -> dict:
    profile = (await async_client.get("/api/v1/candidates/profile", headers=candidate_headers)).json()["data"]
    taxonomy = (await async_client.get(
        f"/api/v1/question-taxonomy?industry_id={profile['industry_id']}", headers=candidate_headers,
    )).json()["data"]
    assert taxonomy["job_roles"]
    if not taxonomy["skills"]:
        skill = await async_client.post("/api/v1/question-taxonomy/manage", headers=admin_headers, json={
            "kind": "skill", "name": f"Draft verification skill {uuid.uuid4()}", "category": "test",
        })
        assert skill.status_code == 201, skill.text
        taxonomy["skills"] = [skill.json()["data"]]
    return {
        "industry_id": profile["industry_id"],
        "job_role_id": taxonomy["job_roles"][0]["id"],
        "job_role_ids": [taxonomy["job_roles"][0]["id"]],
        "skill_ids": [taxonomy["skills"][0]["id"]],
        "question_type": "descriptive",
        "subject": "Provider Integration",
        "topic": "Structured Draft Validation",
        "difficulty": "intermediate",
        "interview_round": "Technical",
    }


@pytest.mark.asyncio
async def test_ai_question_draft_uses_taxonomy_context_and_stays_pending(
    async_client: AsyncClient, candidate_headers: dict, admin_headers: dict, monkeypatch,
):
    brief = await draft_brief(async_client, candidate_headers, admin_headers)
    taxonomy = (await async_client.get(
        f"/api/v1/question-taxonomy?industry_id={brief['industry_id']}", headers=candidate_headers,
    )).json()["data"]
    role = next(item for item in taxonomy["job_roles"] if item["id"] == brief["job_role_id"])
    skill = next(item for item in taxonomy["skills"] if item["id"] == brief["skill_ids"][0])
    question_text = f"Describe a structured review approach {uuid.uuid4()}?"
    provider = StructuredDraftProvider(valid_draft(question_text))
    monkeypatch.setattr(question_service, "get_ai_provider", lambda: provider)

    response = await async_client.post("/api/v1/questions/manage/ai-draft", headers=admin_headers, json=brief)

    assert response.status_code == 201, response.text
    created = response.json()["data"]
    assert created["source_provenance"] == "ai_generated"
    assert created["workflow_status"] == "pending_review"
    assert created["approval_status"] == "pending"
    assert role["title"] in provider.prompt
    assert skill["name"] in provider.prompt
    industry_rows = (await async_client.get("/api/v1/industries")).json()["data"]
    industry = next(item for item in industry_rows if item["id"] == brief["industry_id"])
    assert industry["name"] in provider.prompt
    assert (await async_client.get(f"/api/v1/questions/{created['id']}", headers=candidate_headers)).status_code == 404

    duplicate = await async_client.post("/api/v1/questions/manage/ai-draft", headers=admin_headers, json=brief)
    assert duplicate.status_code == 409
    matches = await async_client.get(
        f"/api/v1/questions/manage?search={question_text.replace(' ', '%20')}", headers=admin_headers,
    )
    assert sum(item["question_text"] == question_text for item in matches.json()["data"]) == 1


@pytest.mark.asyncio
async def test_ai_question_draft_reports_unavailable_and_rejects_malformed_output(
    async_client: AsyncClient, candidate_headers: dict, admin_headers: dict, monkeypatch,
):
    brief = await draft_brief(async_client, candidate_headers, admin_headers)
    forbidden = await async_client.post("/api/v1/questions/manage/ai-draft", headers=candidate_headers, json=brief)
    assert forbidden.status_code == 403

    unavailable_provider = StructuredDraftProvider(AIResponse(is_success=False), available=False)
    monkeypatch.setattr(question_service, "get_ai_provider", lambda: unavailable_provider)
    unavailable = await async_client.post("/api/v1/questions/manage/ai-draft", headers=admin_headers, json=brief)
    assert unavailable.status_code == 503
    assert "no AI provider is configured" in unavailable.json()["error"]["message"]

    malformed_provider = StructuredDraftProvider(AIResponse(is_success=True, structured_data={
        "question_text": "short", "expected_answer": "", "options": [],
    }))
    monkeypatch.setattr(question_service, "get_ai_provider", lambda: malformed_provider)
    malformed = await async_client.post("/api/v1/questions/manage/ai-draft", headers=admin_headers, json=brief)
    assert malformed.status_code == 502
    assert "no question was saved" in malformed.json()["error"]["message"]

    failed_provider = StructuredDraftProvider(AIResponse(
        is_success=False, error_message="Gemini API request timed out after retries",
    ))
    monkeypatch.setattr(question_service, "get_ai_provider", lambda: failed_provider)
    failed = await async_client.post("/api/v1/questions/manage/ai-draft", headers=admin_headers, json=brief)
    assert failed.status_code == 502
    assert "failed or timed out" in failed.json()["error"]["message"]
    assert "no question was saved" in failed.json()["error"]["message"]


@pytest.mark.asyncio
async def test_configured_application_reports_real_gemini_unavailable_without_a_key(
    async_client: AsyncClient, admin_headers: dict, monkeypatch,
):
    if settings.GEMINI_API_KEY.strip():
        pytest.skip("Environment has a Gemini key; live integration verification is handled separately")
    provider = GeminiProvider()
    assert provider.model_name == settings.GEMINI_MODEL
    assert not provider.is_available()
    monkeypatch.setattr(question_service, "get_ai_provider", lambda: provider)
    response = await async_client.post("/api/v1/questions/manage/ai-draft", headers=admin_headers, json={
        "industry_id": str(uuid.uuid4()), "question_type": "descriptive",
        "subject": "Unavailable provider test", "topic": "No key configured",
    })
    assert response.status_code == 503
    assert "no AI provider is configured" in response.json()["error"]["message"]
