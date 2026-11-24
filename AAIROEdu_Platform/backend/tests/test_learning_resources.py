import httpx
import pytest

from app.core.config import settings
from app.services.learning_resources import LearningResourceService


@pytest.mark.asyncio
async def test_resources_use_real_openalex_and_youtube_data_and_rank_by_actual_counts(monkeypatch):
    monkeypatch.setattr(settings, "OPENALEX_BASE_URL", "https://api.openalex.test")
    monkeypatch.setattr(settings, "YOUTUBE_API_KEY", "synthetic-test-key")
    observed = []

    def handler(request):
        observed.append(request)
        if request.url.host == "api.openalex.test":
            assert request.url.params["sort"] == "cited_by_count:desc"
            return httpx.Response(200, json={"results": [{
                "display_name": "A review of people analytics",
                "publication_year": 2025,
                "cited_by_count": 12,
                "doi": "https://doi.org/10.1234/example",
                "primary_location": {},
            }]})
        if request.url.path.endswith("/search"):
            assert request.headers["x-goog-api-key"] == "synthetic-test-key"
            assert "key" not in request.url.params
            return httpx.Response(200, json={"items": [
                {"id": {"videoId": "first"}}, {"id": {"videoId": "second"}},
            ]})
        return httpx.Response(200, json={"items": [
            {"id": "first", "snippet": {"title": "First", "channelTitle": "Channel"}, "statistics": {"viewCount": "20"}},
            {"id": "second", "snippet": {"title": "Second", "channelTitle": "Channel"}, "statistics": {"viewCount": "200"}},
        ]})

    transport = httpx.MockTransport(handler)
    client_class = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: client_class(transport=transport, **kwargs))

    result = await LearningResourceService.search("people analytics", "HR Generalist", limit=20)

    assert result["article_status"] == "available"
    assert result["articles"][0]["citation_count"] == 12
    assert result["videos"][0]["url"].endswith("second")
    assert result["videos"][0]["view_count"] == 200
    assert len(result["videos"]) == 2
    assert len(observed) == 3


@pytest.mark.asyncio
async def test_videos_are_reported_unavailable_without_api_key(monkeypatch):
    monkeypatch.setattr(settings, "YOUTUBE_API_KEY", "")
    monkeypatch.setattr(LearningResourceService, "_search_articles", staticmethod(
        lambda _query, _limit: _async_result(([], "available"))
    ))

    result = await LearningResourceService.search("human resources", "HR Generalist")

    assert result["videos"] == []
    assert result["video_status"] == "unavailable_api_key_required"


@pytest.mark.asyncio
async def test_resources_overfetch_deduplicate_and_apply_recency(monkeypatch):
    monkeypatch.setattr(settings, "OPENALEX_BASE_URL", "https://api.openalex.test")
    monkeypatch.setattr(settings, "YOUTUBE_API_KEY", "synthetic-test-key")

    def handler(request):
        if request.url.host == "api.openalex.test":
            assert "from_publication_date:" in request.url.params["filter"]
            assert int(request.url.params["per-page"]) > 5
            return httpx.Response(200, json={"results": [
                {"display_name": "No usable URL", "primary_location": {}},
                {"display_name": "Credential URL", "doi": "https://user:password@example.com/article"},
                *[{"display_name": f"Article {index}", "doi": f"https://doi.org/10.1234/{index}", "cited_by_count": 100 - index} for index in range(6)],
                {"display_name": "Duplicate", "doi": "https://doi.org/10.1234/0", "cited_by_count": 100},
            ]})
        if request.url.path.endswith("/search"):
            assert "publishedAfter" in request.url.params
            assert int(request.url.params["maxResults"]) > 5
            return httpx.Response(200, json={"items": [
                {"id": {"videoId": "first"}}, {"id": {"videoId": "first"}},
                {"id": {"videoId": "second"}}, {"id": {"videoId": "bad&redirect=1"}},
            ]})
        assert request.url.params["id"] == "first,second"
        return httpx.Response(200, json={"items": [
            {"id": "first", "snippet": {"title": "First"}, "statistics": {"viewCount": "20"}},
            {"id": "second", "snippet": {"title": "Second"}, "statistics": {"viewCount": "200"}},
        ]})

    client_class = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: client_class(transport=httpx.MockTransport(handler), **kwargs))
    result = await LearningResourceService.search("HR analytics", "HR Generalist", recent_years=2)
    assert len(result["articles"]) == 5
    assert len({item["url"] for item in result["articles"]}) == 5
    assert len(result["videos"]) == 2
    assert result["videos"][0]["view_count"] == 200
    assert result["recent_years"] == 2
    assert result["retrieved_at"]


async def _async_result(value):
    return value
