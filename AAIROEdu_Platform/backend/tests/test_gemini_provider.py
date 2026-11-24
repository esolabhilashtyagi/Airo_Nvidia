from types import SimpleNamespace

import pytest
from google.genai import types
from pydantic import BaseModel, Field, ValidationError

from app.integrations.ai.gemini_provider import GeminiProvider


def test_gemini_three_generation_config_uses_thinking_level_not_temperature():
    provider = GeminiProvider()
    provider.model_name = "gemini-3.8-flash"

    config = provider._generation_config("coach rules", 0.2, 512)

    assert config.max_output_tokens == 512
    assert config.system_instruction == "coach rules"
    assert config.temperature is None
    assert config.thinking_config.thinking_level == types.ThinkingLevel.LOW


def test_legacy_gemini_generation_config_keeps_temperature():
    provider = GeminiProvider()
    provider.model_name = "gemini-2.5-flash"

    config = provider._generation_config(None, 0.25, 256)

    assert config.temperature == 0.25
    assert config.thinking_config is None


def test_structured_generation_requests_json_matching_the_pydantic_schema():
    class Output(BaseModel):
        result: str

    provider = GeminiProvider()
    provider.model_name = "gemini-3.8-flash"
    config = provider._generation_config(None, 0.2, 4096, Output)

    assert config.response_mime_type == "application/json"
    assert config.response_schema is None
    assert config.response_json_schema["properties"]["result"]["type"] == "string"


def test_provider_schema_drops_bounds_but_pydantic_still_enforces_them():
    class Output(BaseModel):
        scores: list[int] = Field(min_length=1, max_length=20)
        score: int = Field(ge=0, le=100)

    provider = GeminiProvider()
    provider.model_name = "gemini-3.8-flash"
    config = provider._generation_config(None, 0.2, 4096, Output)
    schema = config.response_json_schema
    scores_schema = schema["properties"]["scores"]
    score_schema = schema["properties"]["score"]

    assert "minItems" not in scores_schema and "maxItems" not in scores_schema
    assert "minimum" not in score_schema and "maximum" not in score_schema
    with pytest.raises(ValidationError):
        Output.model_validate({"scores": [], "score": 101})

    from app.services.resume_service import AIResumeAnalysis

    resume_provider_schema = provider._generation_config(None, 0.2, 4096, AIResumeAnalysis).response_json_schema
    resume_original_schema = AIResumeAnalysis.model_json_schema()
    assert _contains_schema_bounds(resume_original_schema)
    assert not _contains_schema_bounds(resume_provider_schema)
def _contains_schema_bounds(value):
    bound_keys = {"minItems", "maxItems", "minimum", "maximum", "minLength", "maxLength"}
    if isinstance(value, dict):
        return bool(bound_keys.intersection(value)) or any(_contains_schema_bounds(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_schema_bounds(item) for item in value)
    return False


@pytest.mark.asyncio
async def test_empty_provider_response_is_not_reported_as_success(monkeypatch):
    provider = GeminiProvider()
    provider.model_name = "gemini-3.8-flash"
    provider._client = SimpleNamespace(models=SimpleNamespace(
        generate_content=lambda **_: SimpleNamespace(text=None, usage_metadata=None, candidates=[]),
    ))
    monkeypatch.setattr(provider, "is_available", lambda: True)

    response = await provider.generate_text("give me a short answer")

    assert not response.is_success
    assert response.raw_text is None
    assert "no text content" in response.error_message


@pytest.mark.asyncio
async def test_non_retryable_provider_error_stops_without_logging_response_payload(monkeypatch, caplog):
    class NotFound(Exception):
        code = 404
        status = "NOT_FOUND"

        def __str__(self):
            return "provider payload must not be exposed"

    calls = 0

    def fail(**_):
        nonlocal calls
        calls += 1
        raise NotFound()

    provider = GeminiProvider()
    provider.model_name = "gemini-3.8-flash"
    provider.max_retries = 2
    provider._client = SimpleNamespace(models=SimpleNamespace(generate_content=fail))
    monkeypatch.setattr(provider, "is_available", lambda: True)

    response = await provider.generate_text("short request")

    assert not response.is_success
    assert calls == 1
    assert "HTTP 404 (NOT_FOUND)" in response.error_message
    assert "provider payload" not in caplog.text


def test_usage_tracker_estimates_configured_rates_and_marks_unknown_cost_unavailable(caplog):
    from app.integrations.ai.usage_tracker import UsageTracker

    tracker = UsageTracker()
    assert tracker.calculate_cost('gemini-3.8-flash', 1_000_000, 1_000_000) == 4.5
    assert tracker.calculate_cost('unlisted-model', 1_000_000, 1_000_000) is None
    assert 'No pricing estimate configured' in caplog.text


def test_structured_validation_diagnostics_do_not_include_candidate_values(caplog):
    from app.integrations.ai.response_validator import ResponseValidator

    class Output(BaseModel):
        score: int

    private_value = "zz_test_private_candidate_name"
    validated, error = ResponseValidator.validate_pydantic(
        '{"score":"' + private_value + '"}', Output,
    )

    assert validated is None
    assert error and "score" in error
    assert private_value not in error
    assert private_value not in caplog.text
