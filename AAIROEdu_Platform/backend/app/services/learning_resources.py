"""Real external learning-resource search with explicit source/ranking metadata."""

import asyncio
import logging
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger("aairo.learning_resources")


class LearningResourceService:
    @staticmethod
    async def search(topic: str, target_role: str, limit: int = 5, recent_years: int | None = None) -> dict[str, Any]:
        count = max(1, min(limit, 5))
        query = " ".join(part.strip() for part in (topic, target_role) if part and part.strip())
        if recent_years is not None:
            recent_years = max(1, min(recent_years, 10))
        articles_result, videos_result = await asyncio.gather(
            LearningResourceService._search_articles(query, count, recent_years) if recent_years else LearningResourceService._search_articles(query, count),
            LearningResourceService._search_videos(query, count, recent_years) if recent_years else LearningResourceService._search_videos(query, count),
        )
        articles, article_status = articles_result
        videos, video_status = videos_result
        return {
            "topic": topic,
            "target_role": target_role,
            "articles": articles,
            "article_status": article_status,
            "videos": videos,
            "video_status": video_status,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "recent_years": recent_years,
            "ranking_notes": {
                "articles": "Up to five OpenAlex research articles ranked by citations, not editorial quality or views. Research results may require paid access.",
                "videos": "Up to five videos ranked by current view counts within YouTube search matches, not all videos globally. Views do not establish teaching quality.",
            },
        }

    @staticmethod
    async def _search_articles(query: str, limit: int, recent_years: int | None = None) -> tuple[list[dict[str, Any]], str]:
        article_filter = "type:article"
        if recent_years:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=365 * recent_years)).date().isoformat()
            article_filter += f",from_publication_date:{cutoff}"
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(
                    f"{settings.OPENALEX_BASE_URL.rstrip('/')}/works",
                    params={
                        "search": query,
                        "filter": article_filter,
                        "sort": "cited_by_count:desc",
                        "per-page": min(50, limit * 5),
                        "select": "id,display_name,publication_year,cited_by_count,doi,primary_location",
                    },
                )
                response.raise_for_status()
                results = response.json().get("results", [])
            items = []
            seen_urls = set()
            for work in results:
                location = work.get("primary_location") or {}
                landing = location.get("landing_page_url")
                doi = work.get("doi")
                url = doi if isinstance(doi, str) and doi.startswith("https://") else landing
                if not isinstance(url, str):
                    continue
                parsed_url = urlsplit(url)
                if parsed_url.scheme not in {"https", "http"} or not parsed_url.hostname or parsed_url.username or parsed_url.password or url in seen_urls:
                    continue
                seen_urls.add(url)
                items.append({
                    "title": str(work.get("display_name") or "Untitled article")[:500],
                    "url": url,
                    "publication_year": work.get("publication_year"),
                    "citation_count": int(work.get("cited_by_count") or 0),
                    "source": "OpenAlex",
                })
            items.sort(key=lambda item: item["citation_count"], reverse=True)
            return items[:limit], "available"
        except (httpx.HTTPError, ValueError, TypeError, AttributeError) as exc:
            logger.info("OpenAlex article search unavailable (%s)", type(exc).__name__)
            return [], "unavailable"

    @staticmethod
    async def _search_videos(query: str, limit: int, recent_years: int | None = None) -> tuple[list[dict[str, Any]], str]:
        api_key = settings.YOUTUBE_API_KEY.strip()
        if not api_key:
            return [], "unavailable_api_key_required"
        params = {"part": "snippet", "type": "video", "order": "viewCount", "q": query, "maxResults": min(50, limit * 3)}
        if recent_years:
            params["publishedAfter"] = (datetime.now(timezone.utc) - timedelta(days=365 * recent_years)).isoformat().replace("+00:00", "Z")
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                search_response = await client.get(
                    "https://www.googleapis.com/youtube/v3/search",
                    params=params,
                    headers={"X-Goog-Api-Key": api_key},
                )
                search_response.raise_for_status()
                search_items = search_response.json().get("items", [])
                video_ids = list(dict.fromkeys(
                    item.get("id", {}).get("videoId")
                    for item in search_items
                    if isinstance(item.get("id", {}).get("videoId"), str) and re.fullmatch(r"[A-Za-z0-9_-]+", item["id"]["videoId"])
                ))
                if not video_ids:
                    return [], "available"
                details_response = await client.get(
                    "https://www.googleapis.com/youtube/v3/videos",
                    params={"part": "snippet,statistics", "id": ",".join(video_ids)},
                    headers={"X-Goog-Api-Key": api_key},
                )
                details_response.raise_for_status()
                details = {item.get("id"): item for item in details_response.json().get("items", [])}
            ranked = []
            for video_id in video_ids:
                item = details.get(video_id)
                if not item:
                    continue
                snippet = item.get("snippet") or {}
                stats = item.get("statistics") or {}
                ranked.append({
                    "title": str(snippet.get("title") or "Untitled video")[:500],
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "channel": str(snippet.get("channelTitle") or "")[:200],
                    "published_at": snippet.get("publishedAt"),
                    "view_count": int(stats.get("viewCount") or 0),
                    "source": "YouTube Data API",
                })
            ranked.sort(key=lambda item: item["view_count"], reverse=True)
            return ranked[:limit], "available"
        except (httpx.HTTPError, ValueError, TypeError, AttributeError) as exc:
            # Do not log request URLs or response bodies; credentials are sent in
            # a header and provider errors may contain sensitive diagnostics.
            logger.info("YouTube video search unavailable (%s)", type(exc).__name__)
            return [], "unavailable"
