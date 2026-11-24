from types import SimpleNamespace
from unittest.mock import AsyncMock
import uuid

import pytest

from app.integrations.ai.base import AIResponse
from app.services.testing_suggestions import TestingSuggestionService


class Rows:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class FakeDB:
    def __init__(self, pairs=(), performance=()):
        self.results = iter([Rows(pairs), Rows(performance)])

    async def execute(self, *args, **kwargs):
        return next(self.results)


def profile():
    return SimpleNamespace(
        id=uuid.uuid4(), industry_id=uuid.uuid4(), industry=SimpleNamespace(name="Human Resources"),
        current_role="Software Engineer", target_role="HR Generalist", key_skills=["Python"],
        total_experience_months=36, education_history=[], career_goals="Move into employee relations",
    )


@pytest.mark.asyncio
async def test_subject_suggestions_are_model_inferred_without_invented_taxonomy_ids(monkeypatch):
    provider = SimpleNamespace(is_available=lambda: True, generate_structured=AsyncMock(return_value=AIResponse(
        provider_name="nvidia", is_success=True, structured_data={"suggestions": [
            {"subject": "Human Resources", "topic": "Employee Relations", "rationale": "Practice handling workplace conflict before changing careers."},
        ]},
    )))
    monkeypatch.setattr("app.services.testing_suggestions.get_ai_provider", lambda: provider)
    result = await TestingSuggestionService.suggest(FakeDB(), profile(), subject="Human Resources")
    item = result["suggestions"][0]
    assert item["subject_id"] is None and item["topic_id"] is None
    assert item["source"] == "ai_inferred"
    assert item["understanding_percentage"] is None
    assert item["evaluated_sample_count"] == 0
    prompt = provider.generate_structured.await_args.args[0]
    assert "Software Engineer" in prompt and "HR Generalist" in prompt
    assert "Move into employee relations" in prompt


@pytest.mark.asyncio
async def test_invalid_model_subject_and_links_fall_back_to_real_catalog(monkeypatch):
    subject_id, topic_id = uuid.uuid4(), uuid.uuid4()
    provider = SimpleNamespace(is_available=lambda: True, generate_structured=AsyncMock(return_value=AIResponse(
        provider_name="nvidia", is_success=True, structured_data={"suggestions": [
            {"subject": "Wrong subject", "topic": "Invented topic", "rationale": "Follow https://unverified.example"},
        ]},
    )))
    monkeypatch.setattr("app.services.testing_suggestions.get_ai_provider", lambda: provider)
    result = await TestingSuggestionService.suggest(
        FakeDB([(subject_id, "Human Resources", topic_id, "Employee Relations")], [("employee relations", 40, 3)]),
        profile(), subject="Human Resources",
    )
    assert result["ai_status"] == "unavailable"
    item = result["suggestions"][0]
    assert item["topic"] == "Employee Relations"
    assert item["topic_id"] == str(topic_id)
    assert item["source"] == "taxonomy"
    assert item["understanding_percentage"] == 40
    assert item["evaluated_sample_count"] == 3


@pytest.mark.asyncio
async def test_offline_empty_catalog_does_not_fabricate_suggestions(monkeypatch):
    monkeypatch.setattr("app.services.testing_suggestions.get_ai_provider", lambda: SimpleNamespace(is_available=lambda: False))
    result = await TestingSuggestionService.suggest(FakeDB(), profile())
    assert result["suggestions"] == []
    assert result["ai_status"] == "unavailable"


@pytest.mark.asyncio
async def test_testing_suggestions_requires_authentication(async_client):
    response = await async_client.get("/api/v1/testing/suggestions?subject=Human+Resources")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_testing_suggestions_authenticated_endpoint(async_client, candidate_headers, monkeypatch):
    suggest = AsyncMock(return_value={"suggestions": [], "ai_status": "unavailable"})
    monkeypatch.setattr(TestingSuggestionService, "suggest", suggest)
    response = await async_client.get("/api/v1/testing/suggestions?subject=Python", headers=candidate_headers)
    assert response.status_code == 200
    assert suggest.await_args.kwargs["subject"] == "Python"
