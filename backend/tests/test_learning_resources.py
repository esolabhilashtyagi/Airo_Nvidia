import httpx
import pytest
from types import SimpleNamespace

from app.core.config import settings
from app.services.learning_resources import LearningResourceService


@pytest.mark.asyncio
async def test_resources_use_grounded_website_articles_and_rank_youtube_by_actual_counts(monkeypatch):
    monkeypatch.setattr(settings, "YOUTUBE_API_KEY", "synthetic-test-key")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    observed = []
    async def grounded_articles(*_args):
        return ([{"title": "A review of people analytics", "url": "https://engineering.example.org/people-analytics", "source": "Web search", "publication_year": None, "citation_count": 0}], "available")
    monkeypatch.setattr(LearningResourceService, "_search_grounded_articles", staticmethod(grounded_articles))

    def handler(request):
        observed.append(request)
        if request.url.path.endswith("/search"):
            assert request.headers["x-goog-api-key"] == "synthetic-test-key"
            assert "key" not in request.url.params
            return httpx.Response(200, json={"items": [
                {"id": {"videoId": "first123456"}}, {"id": {"videoId": "second12345"}},
            ]})
        return httpx.Response(200, json={"items": [
            {"id": "first123456", "snippet": {"title": "First", "channelTitle": "Channel"}, "statistics": {"viewCount": "20"}},
            {"id": "second12345", "snippet": {"title": "Second", "channelTitle": "Channel"}, "statistics": {"viewCount": "200"}},
        ]})

    transport = httpx.MockTransport(handler)
    client_class = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: client_class(transport=transport, **kwargs))

    result = await LearningResourceService.search("people analytics", "HR Generalist", limit=20)

    assert result["article_status"] == "available"
    assert result["articles"][0]["url"] == "https://engineering.example.org/people-analytics"
    assert result["videos"][0]["url"].endswith("second12345")
    assert result["videos"][0]["view_count"] == 200
    assert len(result["videos"]) == 2
    assert len(observed) == 2


@pytest.mark.asyncio
async def test_failed_youtube_api_search_falls_back_to_grounded_video_results(monkeypatch):
    monkeypatch.setattr(settings, "YOUTUBE_API_KEY", "synthetic-test-key")
    # Resource web grounding uses its configured key regardless of the app's
    # selected generation provider.
    monkeypatch.setattr(settings, "AI_PROVIDER", "nvidia")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "zz_test_synthetic_key")
    async def unavailable_api(*_args):
        return [], "unavailable"
    async def grounded(*_args):
        return ([{"title": "Verified system design lesson", "url": "https://www.youtube.com/watch?v=video123",
                  "channel": "", "published_at": None, "view_count": None, "source": "Web search"}], "available_grounded")
    monkeypatch.setattr(LearningResourceService, "_search_grounded_articles", staticmethod(lambda *_args: _async_result(([], "unavailable_not_configured"))))
    monkeypatch.setattr(LearningResourceService, "_search_videos", staticmethod(unavailable_api))
    monkeypatch.setattr(LearningResourceService, "_search_grounded_videos", staticmethod(grounded))
    monkeypatch.setattr(LearningResourceService, "_hydrate_video_statistics", staticmethod(lambda items: _async_result(items)))

    result = await LearningResourceService.search("system design", "Backend Engineer")

    assert result["video_status"] == "available_grounded"
    assert result["videos"][0]["url"] == "https://www.youtube.com/watch?v=video123"


@pytest.mark.asyncio
async def test_videos_are_reported_unavailable_without_api_key(monkeypatch):
    monkeypatch.setattr(settings, "YOUTUBE_API_KEY", "")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    monkeypatch.setattr(LearningResourceService, "_search_grounded_articles", staticmethod(
        lambda _query, _limit, _recent_years=None: _async_result(([], "unavailable_not_configured"))
    ))

    result = await LearningResourceService.search("human resources", "HR Generalist")

    assert result["videos"] == []
    assert result["video_status"] == "unavailable_api_key_required"


@pytest.mark.asyncio
async def test_grounded_search_supplies_verified_source_urls_when_external_indexes_are_unavailable(monkeypatch):
    monkeypatch.setattr(settings, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "zz_test_synthetic_key")
    monkeypatch.setattr(settings, "YOUTUBE_API_KEY", "")
    async def unavailable(*_args):
        return [], "unavailable"
    async def videos_require_key(*_args):
        return [], "unavailable_api_key_required"
    monkeypatch.setattr(LearningResourceService, "_search_videos", staticmethod(videos_require_key))
    chunks = [
        SimpleNamespace(web=SimpleNamespace(uri="https://docs.example.org/guide", title="Official guide")),
        SimpleNamespace(web=SimpleNamespace(uri="https://www.youtube.com/watch?v=video123", title="A practical lesson")),
        SimpleNamespace(web=SimpleNamespace(uri="https://youtu.be/short456", title="Another verified lesson")),
        SimpleNamespace(web=SimpleNamespace(uri="https://scholar.google.com/scholar?q=database", title="Google Scholar")),
        SimpleNamespace(web=SimpleNamespace(uri="https://doi.org/10.1234/example", title="DOI resolver")),
        SimpleNamespace(web=SimpleNamespace(uri="https://youtube.com/results?search_query=database", title="YouTube search")),
        SimpleNamespace(web=SimpleNamespace(uri="javascript:alert(1)", title="Unsafe")),
    ]
    response = SimpleNamespace(candidates=[SimpleNamespace(grounding_metadata=SimpleNamespace(grounding_chunks=chunks))])
    class Models:
        def generate_content(self, **kwargs):
            if "website articles" in kwargs["contents"]:
                assert "Google Scholar" in kwargs["contents"]
                assert "official documentation" in kwargs["contents"]
            return response
    class Client:
        def __init__(self, **_kwargs):
            self.models = Models()
    monkeypatch.setattr("app.services.learning_resources.genai.Client", Client)

    result = await LearningResourceService.search("database indexes", "Backend Engineer")

    assert result["article_status"] == "available"
    assert [item["url"] for item in result["articles"]] == ["https://docs.example.org/guide"]
    assert result["video_status"] == "available_grounded"
    assert [item["url"] for item in result["videos"]] == [
        "https://www.youtube.com/watch?v=video123", "https://www.youtube.com/watch?v=short456",
    ]
    assert result["videos"][0]["view_count"] is None


@pytest.mark.asyncio
async def test_resources_cap_results_deduplicate_and_apply_recency(monkeypatch):
    monkeypatch.setattr(settings, "YOUTUBE_API_KEY", "synthetic-test-key")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")

    def handler(request):
        if request.url.path.endswith("/search"):
            assert "publishedAfter" in request.url.params
            assert int(request.url.params["maxResults"]) > 5
            return httpx.Response(200, json={"items": [
                {"id": {"videoId": "first123456"}}, {"id": {"videoId": "first123456"}},
                {"id": {"videoId": "second12345"}}, {"id": {"videoId": "bad&redirect=1"}},
            ]})
        assert request.url.params["id"] == "first123456,second12345"
        return httpx.Response(200, json={"items": [
            {"id": "first123456", "snippet": {"title": "First"}, "statistics": {"viewCount": "20"}},
            {"id": "second12345", "snippet": {"title": "Second"}, "statistics": {"viewCount": "200"}},
        ]})

    client_class = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: client_class(transport=httpx.MockTransport(handler), **kwargs))
    grounded = [
        {"title": f"Article {index}", "url": f"https://blog.example.org/{index}", "source": "Web search"}
        for index in range(7)
    ] + [{"title": "Scholar", "url": "https://scholar.google.com/scholar?q=hr", "source": "Web search"}]
    monkeypatch.setattr(LearningResourceService, "_search_grounded_articles", staticmethod(lambda *_args: _async_result((grounded, "available"))))
    result = await LearningResourceService.search("HR analytics", "HR Generalist", recent_years=2)
    assert len(result["articles"]) == 5
    assert len({item["url"] for item in result["articles"]}) == 5
    assert len(result["videos"]) == 2
    assert result["videos"][0]["view_count"] == 200
    assert result["recent_years"] == 2
    assert result["retrieved_at"]


def test_youtube_grounding_accepts_short_and_shorts_urls_and_canonicalizes_ids():
    assert LearningResourceService._youtube_video_id("https://youtu.be/video12345") == "video12345"
    assert LearningResourceService._youtube_video_id("https://www.youtube.com/shorts/video12345") == "video12345"
    assert LearningResourceService._youtube_video_id("https://www.youtube.com/channel/video12345") is None


def test_grounding_chunk_extraction_accepts_python_sdk_objects_and_camel_case_payloads():
    raw_chunk = {"web": {"uri": "https://docs.example.org/article", "title": "Grounded article"}}
    response = {"candidates": [{"groundingMetadata": {"groundingChunks": [raw_chunk]}}]}

    assert LearningResourceService._grounding_web_chunks(response) == [raw_chunk]


@pytest.mark.asyncio
async def test_grounded_and_live_video_sources_are_merged_and_ranked_by_verified_views(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    async def articles(*_args):
        return [], "unavailable_not_configured"
    async def live_videos(*_args):
        return ([{"title": "Live result", "url": "https://www.youtube.com/watch?v=live1234567", "channel": "Live",
                  "published_at": None, "view_count": 100, "source": "YouTube Data API"}], "available")
    async def grounded_videos(*_args):
        return ([{"title": "Grounded result", "url": "https://youtu.be/ground12345", "channel": "", "published_at": None,
                  "view_count": None, "source": "Google Search"}], "available_grounded")
    async def hydrated(items):
        return [{**items[0], "view_count": 500, "channel": "Grounded channel"}]
    monkeypatch.setattr(LearningResourceService, "_search_grounded_articles", staticmethod(articles))
    monkeypatch.setattr(LearningResourceService, "_search_videos", staticmethod(live_videos))
    monkeypatch.setattr(LearningResourceService, "_search_grounded_videos", staticmethod(grounded_videos))
    monkeypatch.setattr(LearningResourceService, "_hydrate_video_statistics", staticmethod(hydrated))

    result = await LearningResourceService.search("distributed systems", "Backend Engineer")

    assert result["video_status"] == "available"
    assert [video["view_count"] for video in result["videos"]] == [500, 100]
    assert result["videos"][0]["url"] == "https://www.youtube.com/watch?v=ground12345"


@pytest.mark.asyncio
async def test_grounded_articles_never_fill_with_scholar_or_doi_results(monkeypatch):
    grounded = [{"title": f"Article {index}", "url": f"https://blog.example.org/{index}", "source": "Google Search"} for index in range(4)]
    async def grounded_search(*_args):
        return [*grounded, {"title": "Scholar", "url": "https://scholar.google.com/scholar?q=x"}, {"title": "DOI", "url": "https://doi.org/10.1234/x"}], "available"
    monkeypatch.setattr(LearningResourceService, "_search_grounded_articles", staticmethod(grounded_search))

    articles, status = await LearningResourceService._search_articles_with_fallback("algorithms", 5)

    assert status == "available"
    assert len(articles) == 4
    assert all("scholar.google" not in article["url"] and "doi.org" not in article["url"] for article in articles)


async def _async_result(value):
    return value
