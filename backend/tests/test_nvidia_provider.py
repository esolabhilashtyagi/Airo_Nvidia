import asyncio
import json
import time

import httpx
import pytest
from pydantic import BaseModel

from app.integrations.ai.nvidia_provider import NvidiaProvider


def configure_provider(monkeypatch, *, key="test-token", base="https://integrate.api.nvidia.com/v1"):
    from app.core.config import settings

    monkeypatch.setattr(settings, "NVIDIA_API_KEY", key)
    monkeypatch.setattr(settings, "NVIDIA_MODEL", "nvidia/nemotron-3.5-lightning-30b-a3b")
    monkeypatch.setattr(settings, "NVIDIA_BASE_URL", base)
    monkeypatch.setattr(settings, "AI_REQUEST_TIMEOUT_SECONDS", 1)
    monkeypatch.setattr(settings, "AI_MAX_RETRIES", 0)
    return NvidiaProvider()


def mock_client(monkeypatch, handler):
    client_class = httpx.AsyncClient
    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: client_class(transport=transport, **kwargs),
    )


@pytest.mark.asyncio
async def test_text_generation_uses_nvidia_chat_completions_without_logging_secrets(monkeypatch, caplog):
    provider = configure_provider(monkeypatch)
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        seen["payload"] = request.read().decode()
        return httpx.Response(200, json={
            "choices": [{"message": {"content": "Generated from the provider"}}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 5},
        })

    mock_client(monkeypatch, handler)
    response = await provider.generate_text("synthetic prompt", "system", max_tokens=77)

    assert response.is_success
    assert response.raw_text == "Generated from the provider"
    assert response.provider_name == "nvidia"
    assert response.model_name == "nvidia/nemotron-3.5-lightning-30b-a3b"
    assert response.usage.total_tokens == 17
    assert response.usage.estimated_cost_usd is None
    assert seen["url"].endswith("/v1/chat/completions")
    assert seen["auth"] == "Bearer test-token"
    assert json.loads(seen["payload"])["max_tokens"] == 77
    assert "test-token" not in caplog.text
    assert "synthetic prompt" not in caplog.text
    assert response.raw_text not in caplog.text


@pytest.mark.asyncio
async def test_structured_generation_validates_json_locally(monkeypatch):
    class Result(BaseModel):
        title: str

    provider = configure_provider(monkeypatch)
    mock_client(monkeypatch, lambda _: httpx.Response(200, json={
        "choices": [{"message": {"content": '{"title":"Grounded result"}'}}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 2},
    }))

    response = await provider.generate_structured("synthetic", Result)

    assert response.is_success
    assert response.structured_data == {"title": "Grounded result"}


@pytest.mark.asyncio
async def test_provider_errors_do_not_expose_response_payload(monkeypatch, caplog):
    provider = configure_provider(monkeypatch)
    mock_client(monkeypatch, lambda _: httpx.Response(
        401, text="private candidate prompt and provider diagnostic"
    ))

    response = await provider.generate_text("synthetic")

    assert not response.is_success
    assert "HTTP 401" in response.error_message
    assert "private candidate" not in response.error_message
    assert "private candidate" not in caplog.text


def test_self_hosted_endpoint_can_be_configured_without_hosted_key(monkeypatch):
    provider = configure_provider(monkeypatch, key="", base="http://nvidia-nim:8000/v1")
    assert provider.is_available()


def test_hosted_nvidia_endpoint_requires_key(monkeypatch):
    provider = configure_provider(monkeypatch, key="")
    assert not provider.is_available()


def test_provider_factory_selects_explicit_nvidia_and_never_falls_back(monkeypatch):
    from app.core.config import settings
    from app.integrations.ai import provider_factory

    monkeypatch.setattr(settings, "AI_PROVIDER", "nvidia")
    monkeypatch.setattr(settings, "NVIDIA_API_KEY", "")
    monkeypatch.setattr(settings, "NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
    monkeypatch.setattr(provider_factory, "_cached_provider", None)

    provider = provider_factory.get_ai_provider()

    assert isinstance(provider, NvidiaProvider)
    assert not provider.is_available()


@pytest.mark.parametrize("base", [
    " HTTPS://INTEGRATE.API.NVIDIA.COM:443/v1/ ",
    "https://integrate.api.nvidia.com/v1/other",
    "https://integrate.api.nvidia.com:8443/v1",
    "http://integrate.api.nvidia.com/v1",
    "https://integrate.api.nvidia.com./v1",
])
def test_hosted_endpoint_variants_cannot_bypass_key_requirement(monkeypatch, base):
    assert not configure_provider(monkeypatch, key="", base=base).is_available()
    assert configure_provider(monkeypatch, key="test-token", base=base).is_available()


@pytest.mark.asyncio
async def test_provider_normalizes_url_before_sending(monkeypatch):
    provider = configure_provider(
        monkeypatch, base=" HTTPS://INTEGRATE.API.NVIDIA.COM:443/v1/ "
    )
    seen = []

    def handler(request):
        seen.append(str(request.url))
        return httpx.Response(200, json={
            "choices": [{"message": {"content": "Synthetic result"}}],
        })

    mock_client(monkeypatch, handler)
    assert (await provider.generate_text("synthetic")).is_success
    assert seen == ["https://integrate.api.nvidia.com/v1/chat/completions"]


@pytest.mark.asyncio
async def test_non_retryable_error_reports_actual_attempts(monkeypatch, caplog):
    provider = configure_provider(monkeypatch)
    provider.max_retries = 3
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(400, text="synthetic-private-output test-token")

    mock_client(monkeypatch, handler)
    response = await provider.generate_text("synthetic-private-prompt")
    assert not response.is_success
    assert "after 1 attempt(s): HTTP 400" in response.error_message
    assert len(requests) == 1
    assert "synthetic-private" not in caplog.text
    assert "test-token" not in caplog.text


@pytest.mark.asyncio
async def test_overall_timeout_interrupts_a_request(monkeypatch):
    provider = configure_provider(monkeypatch)
    provider.timeout = 0.05

    async def handler(request):
        await asyncio.sleep(0.2)
        return httpx.Response(200, json={
            "choices": [{"message": {"content": "Too late"}}],
        })

    mock_client(monkeypatch, handler)
    started = time.monotonic()
    response = await provider.generate_text("synthetic")
    assert not response.is_success
    assert "after 1 attempt(s)" in response.error_message
    assert "timeout" in response.error_message.lower()
    assert time.monotonic() - started < 0.18


@pytest.mark.asyncio
async def test_overall_timeout_includes_retry_backoff(monkeypatch):
    provider = configure_provider(monkeypatch)
    provider.timeout = 0.05
    provider.max_retries = 2
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(503)

    mock_client(monkeypatch, handler)
    started = time.monotonic()
    response = await provider.generate_text("synthetic")
    assert not response.is_success
    assert "after 1 attempt(s)" in response.error_message
    assert "timeout" in response.error_message.lower()
    assert len(requests) == 1
    assert time.monotonic() - started < 0.18


@pytest.mark.asyncio
async def test_overall_timeout_does_not_reset_between_retries(monkeypatch):
    provider = configure_provider(monkeypatch)
    provider.timeout = 0.05
    provider.max_retries = 2
    requests = []
    real_sleep = asyncio.sleep

    async def skip_backoff(delay):
        await real_sleep(0)

    async def handler(request):
        requests.append(request)
        await real_sleep(0.035)
        if len(requests) == 1:
            return httpx.Response(503)
        return httpx.Response(200, json={
            "choices": [{"message": {"content": "Too late"}}],
        })

    mock_client(monkeypatch, handler)
    monkeypatch.setattr(asyncio, "sleep", skip_backoff)
    response = await provider.generate_text("synthetic")
    assert not response.is_success
    assert "after 2 attempt(s)" in response.error_message
    assert "timeout" in response.error_message.lower()
    assert len(requests) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("structured", [False, True])
@pytest.mark.parametrize("mode", ["json_object", "prompt"])
@pytest.mark.parametrize("rejection", ["length", "content_filter", "refusal", "refusal_part", "refusal_finish"])
async def test_incomplete_or_refused_output_is_rejected_even_if_schema_valid(
    monkeypatch, caplog, structured, mode, rejection
):
    from app.core.config import settings

    class Result(BaseModel):
        title: str

    monkeypatch.setattr(settings, "NVIDIA_STRUCTURED_OUTPUT_MODE", mode)
    provider = configure_provider(monkeypatch)
    provider.max_retries = 2
    message = {"content": '{"title":"synthetic-private-output"}'}
    choice = {"message": message, "finish_reason": "stop"}
    if rejection == "refusal":
        message["refusal"] = "synthetic-private-refusal test-token"
    elif rejection == "refusal_part":
        message["content"] = [
            {"type": "text", "text": '{"title":"synthetic-private-output"}'},
            {"type": "refusal", "refusal": "synthetic-private-refusal test-token"},
        ]
    else:
        choice["finish_reason"] = rejection
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"choices": [choice]})

    mock_client(monkeypatch, handler)
    response = (
        await provider.generate_structured("synthetic", Result)
        if structured else await provider.generate_text("synthetic")
    )
    assert not response.is_success
    assert response.structured_data is None
    assert response.raw_text is None
    assert len(requests) == 1
    assert "synthetic-private" not in (response.error_message + caplog.text)
    assert "test-token" not in (response.error_message + caplog.text)


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["json_object", "prompt"])
@pytest.mark.parametrize("content, success", [('{"title":"Synthetic"}', True), ('{}', False)])
async def test_structured_output_modes_always_validate_locally(monkeypatch, mode, content, success):
    from app.core.config import settings

    class Result(BaseModel):
        title: str

    monkeypatch.setattr(settings, "NVIDIA_STRUCTURED_OUTPUT_MODE", mode)
    provider = configure_provider(monkeypatch, key="", base="http://127.0.0.1:8000/v1")
    seen = []

    def handler(request):
        payload = json.loads(request.read())
        seen.append(payload)
        assert request.headers.get("authorization") is None
        if mode == "prompt" and "response_format" in payload:
            return httpx.Response(400)
        return httpx.Response(200, json={
            "choices": [{"finish_reason": "stop", "message": {"content": content}}],
        })

    mock_client(monkeypatch, handler)
    response = await provider.generate_structured("synthetic", Result)
    assert response.is_success is success
    assert len(seen) == 1
    assert "JSON Schema" in seen[0]["messages"][0]["content"]
    if mode == "json_object":
        assert seen[0]["response_format"] == {"type": "json_object"}
    else:
        assert "response_format" not in seen[0]
    if not success:
        assert "title (missing)" in response.error_message


@pytest.mark.asyncio
async def test_json_object_rejection_does_not_automatically_fall_back(monkeypatch):
    from app.core.config import settings

    class Result(BaseModel):
        title: str

    monkeypatch.setattr(settings, "NVIDIA_STRUCTURED_OUTPUT_MODE", "json_object")
    provider = configure_provider(monkeypatch)
    provider.max_retries = 2
    seen = []

    def handler(request):
        seen.append(json.loads(request.read()))
        return httpx.Response(400)

    mock_client(monkeypatch, handler)
    response = await provider.generate_structured("synthetic", Result)
    assert not response.is_success
    assert "after 1 attempt(s)" in response.error_message
    assert len(seen) == 1
    assert seen[0]["response_format"] == {"type": "json_object"}


@pytest.mark.asyncio
async def test_empty_json_object_is_valid_for_empty_schema(monkeypatch):
    class EmptyResult(BaseModel):
        pass

    provider = configure_provider(monkeypatch)
    mock_client(monkeypatch, lambda _: httpx.Response(200, json={
        "choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}],
    }))
    response = await provider.generate_structured("synthetic", EmptyResult)
    assert response.is_success
    assert response.structured_data == {}


@pytest.mark.parametrize("raw", ["{}", "```json\n{}\n```"])
def test_validator_distinguishes_empty_object_from_absent_json(raw):
    from app.integrations.ai.response_validator import ResponseValidator

    class DefaultResult(BaseModel):
        title: str = "default"

    validated, error = ResponseValidator.validate_pydantic(raw, DefaultResult)
    assert error is None
    assert validated.title == "default"
    validated, error = ResponseValidator.validate_pydantic("not JSON", DefaultResult)
    assert validated is None
    assert "parseable JSON" in error
