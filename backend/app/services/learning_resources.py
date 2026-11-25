"""Real external learning-resource search with explicit source/ranking metadata."""

import asyncio
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus, urlsplit
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

    @staticmethod
    async def _search_devto_blogs(query: str, limit: int = 3) -> list[dict[str, Any]]:
        """Fetch live engineering blog articles from Dev.to's public API."""
        # Extract the most specific alphanumeric tag/keyword for Dev.to
        tokens = [t for t in re.findall(r"[a-zA-Z0-9]+", query.lower()) if len(t) > 2]
        tag = tokens[0] if tokens else "programming"
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                response = await client.get(
                    "https://dev.to/api/articles",
                    params={"tag": tag, "per_page": max(limit * 2, 6), "top": 30},
                )
                if response.status_code != 200 or not response.json():
                    response = await client.get(
                        "https://dev.to/api/articles",
                        params={"per_page": limit, "top": 7},
                    )
                response.raise_for_status()
                items = response.json() or []
            blogs = []
            for art in items[:limit]:
                url = art.get("url")
                if not isinstance(url, str) or not url.startswith("https://"):
                    continue
                mins = art.get("reading_time_minutes")
                blogs.append({
                    "title": str(art.get("title") or "Engineering Article")[:200],
                    "url": url,
                    "source": "Dev.to",
                    "resource_type": "blog",
                    "metadata": f"{mins} min read" if mins else "Article",
                })
            return blogs
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            logger.info("Dev.to blog search unavailable (%s)", type(exc).__name__)
            return []

    @staticmethod
    def _parse_view_count(views_text: str) -> int:
        if not views_text:
            return 0
        txt = views_text.lower().replace(",", "").strip()
        m = re.search(r"(\d+(?:\.\d+)?)\s*([kmb])?", txt)
        if not m:
            return 0
        num = float(m.group(1))
        suffix = m.group(2)
        if suffix == "k":
            num *= 1_000
        elif suffix == "m":
            num *= 1_000_000
        elif suffix == "b":
            num *= 1_000_000_000
        return int(num)

    @staticmethod
    async def _search_youtube_web(query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Fetch top YouTube videos with view counts directly from YouTube search results."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }
        try:
            async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                response = await client.get(
                    "https://www.youtube.com/results",
                    params={"search_query": query},
                    headers=headers,
                )
                response.raise_for_status()
                html = response.text
            match = re.search(r"var ytInitialData = (\{.*?\});</script>", html) or re.search(
                r"ytInitialData\s*=\s*(\{.*?\});", html
            )
            if not match:
                return []
            data = json.loads(match.group(1))
            sections = (
                data.get("contents", {})
                .get("twoColumnSearchResultsRenderer", {})
                .get("primaryContents", {})
                .get("sectionListRenderer", {})
                .get("contents", [])
            )
            videos: list[dict[str, Any]] = []
            seen_ids: set[str] = set()
            for sec in sections:
                for item in sec.get("itemSectionRenderer", {}).get("contents", []):
                    vr = item.get("videoRenderer")
                    if not vr:
                        continue
                    vid_id = vr.get("videoId")
                    if not isinstance(vid_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", vid_id) or vid_id in seen_ids:
                        continue
                    title = "".join(run.get("text", "") for run in vr.get("title", {}).get("runs", [])).strip()
                    views_text = (vr.get("viewCountText", {}).get("simpleText") or "").strip()
                    channel = "".join(run.get("text", "") for run in vr.get("ownerText", {}).get("runs", [])).strip()
                    view_count = LearningResourceService._parse_view_count(views_text)
                    if not title or not views_text or view_count <= 0:
                        continue
                    seen_ids.add(vid_id)
                    videos.append({
                        "title": title[:200],
                        "url": f"https://www.youtube.com/watch?v={vid_id}",
                        "channel": channel[:120] or "YouTube",
                        "view_count": view_count,
                        "views_label": views_text,
                        "source": channel[:120] or "YouTube",
                    })
            videos.sort(key=lambda v: v["view_count"], reverse=True)
            return videos[:limit]
        except (httpx.HTTPError, ValueError, TypeError, KeyError) as exc:
            logger.info("YouTube web search unavailable (%s)", type(exc).__name__)
            return []

    @staticmethod
    async def search_subtopic_resources(
        subtopic_title: str,
        broad_topic: str,
        target_role: str = "",
        search_query: str = "",
    ) -> dict[str, list[dict[str, Any]]]:
        """Fetch Blogs/Articles, Courses, and Top 5 high-view YouTube Videos for a subtopic."""
        effective_query = (search_query or f"{subtopic_title} {broad_topic}").strip()
        encoded = quote_plus(effective_query)

        devto_task = LearningResourceService._search_devto_blogs(subtopic_title, limit=2)
        openalex_task = LearningResourceService._search_articles(effective_query, limit=2)
        youtube_api_task = LearningResourceService._search_videos(f"{effective_query} tutorial", limit=5)

        devto_blogs, (openalex_articles, _), (yt_api_videos, yt_status) = await asyncio.gather(
            devto_task, openalex_task, youtube_api_task
        )

        yt_videos = yt_api_videos
        if not yt_videos or yt_status != "available":
            yt_videos = await LearningResourceService._search_youtube_web(f"{effective_query} tutorial", limit=5)

        blogs: list[dict[str, Any]] = list(devto_blogs)
        for art in openalex_articles:
            blogs.append({
                "title": art["title"],
                "url": art["url"],
                "source": art.get("source", "OpenAlex"),
                "resource_type": "blog",
                "metadata": f"{art.get('publication_year', '')} · {art.get('citation_count', 0)} citations".strip(" ·"),
            })
        if not blogs:
            blogs.append({
                "title": f"{subtopic_title} — Technical Guides & Articles",
                "url": f"https://www.freecodecamp.org/news/search/?query={encoded}",
                "source": "freeCodeCamp News",
                "resource_type": "blog",
                "metadata": "Curated technical blogs",
            })

        courses: list[dict[str, Any]] = [
            {
                "title": f"{subtopic_title} — Structured Courses",
                "url": f"https://www.coursera.org/search?query={encoded}",
                "source": "Coursera",
                "resource_type": "course",
                "metadata": "Guided course track",
            },
            {
                "title": f"{subtopic_title} — OpenCourseWare & Labs",
                "url": f"https://ocw.mit.edu/search/?q={encoded}",
                "source": "MIT OpenCourseWare",
                "resource_type": "course",
                "metadata": "University lectures & notes",
            },
        ]

        videos: list[dict[str, Any]] = []
        for vid in yt_videos[:5]:
            views_meta = vid.get("views_label") or (f"{vid.get('view_count', 0):,} views" if vid.get("view_count") else "YouTube")
            videos.append({
                "title": vid["title"],
                "url": vid["url"],
                "source": vid.get("channel") or "YouTube",
                "resource_type": "video",
                "metadata": views_meta,
            })
        if not videos:
            videos.append({
                "title": f"{subtopic_title} — Top YouTube Tutorials",
                "url": f"https://www.youtube.com/results?search_query={quote_plus(effective_query + ' full explanation')}",
                "source": "YouTube",
                "resource_type": "video",
                "metadata": "Video tutorials",
            })

        return {"blogs": blogs[:3], "courses": courses[:2], "videos": videos[:5]}
