"""
Universal Open-Web Collector for Interview Intelligence Platform.
Performs search discovery across thousands of domains via SearXNG / multi-engine queries,
extracts clean article bodies using curl_cffi and trafilatura (stripping navbars, sidebars,
and footers across any webpage layout), and prepares full article context for the Nemotron gate.
"""

import asyncio
import os
import re
import urllib.parse
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
import httpx
from core.logging import logger

try:
    from curl_cffi.requests import AsyncSession as CurlAsyncSession
    CURL_CFFI_AVAILABLE = True
except ImportError:
    CURL_CFFI_AVAILABLE = False

import trafilatura

# Domains that host generic discussions, video content, or require login walls
BLOCKED_DOMAINS = {
    "news.ycombinator.com", "ycombinator.com", "hn.algolia.com", "youtube.com", "www.youtube.com",
    "linkedin.com", "www.linkedin.com", "pinterest.com", "www.pinterest.com",
    "quora.com", "www.quora.com", "facebook.com", "www.facebook.com",
    "twitter.com", "x.com", "instagram.com", "tiktok.com"
}

# Regex to reject generic SEO clickbait and listicle headlines
SEO_TITLE_RE = re.compile(
    r"(?i)\b(top\s+\d+|best\s+\d+|\d+\s+most\s+common|interview\s+questions\s+and\s+answers|cheat\s+sheet)\b"
)

DEFAULT_SEARXNG_URL = os.getenv("SEARXNG_URL", "http://localhost:8080/search")


class OpenWebCollector:
    def __init__(self, searxng_url: str = DEFAULT_SEARXNG_URL):
        self.searxng_url = searxng_url
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

    async def _discover_urls_searxng(
        self,
        client: Any,
        company: str,
        role: str,
        page: int = 1,
        custom_query: Optional[str] = None,
    ) -> List[str]:
        """Queries SearXNG using dynamic Nemotron dorks that block SEO listicles."""
        clean_comp = company.strip()
        clean_role = role.strip() if role and role.lower() not in ["all", "general", ""] else "Software Engineer"
        query = custom_query or (
            f'"{clean_comp}" "{clean_role}" ("interview experience" OR "was asked" OR "onsite round" OR "system design round") '
            f'-intitle:"top 50" -intitle:"top 100" -intitle:"questions and answers"'
        )
        params = {"q": query, "format": "json", "pageno": page, "language": "en"}

        try:
            resp = await client.get(self.searxng_url, params=params, timeout=8.0)
            if resp.status_code == 200:
                data = resp.json()
                urls = []
                for item in data.get("results", []):
                    url = item.get("url", "")
                    title = item.get("title", "")
                    domain = urlparse(url).netloc.lower()
                    if not url or domain in BLOCKED_DOMAINS or SEO_TITLE_RE.search(title):
                        continue
                    urls.append(url)
                if urls:
                    return list(dict.fromkeys(urls))
        except Exception as e:
            logger.debug(f"SearXNG query to {self.searxng_url} unavailable ({e}), trying fallback search discovery.")

        return []

    async def _discover_urls_duckduckgo_fallback(
        self,
        client: Any,
        company: str,
        role: str,
        page: int = 1,
        custom_query: Optional[str] = None,
    ) -> List[str]:
        """
        Resilient zero-dependency fallback: queries DuckDuckGo HTML endpoint
        to discover authentic blog and forum posts when SearXNG is offline.
        """
        clean_comp = company.strip()
        clean_role = role.strip() if role and role.lower() not in ["all", "general", ""] else "Software Engineer"
        query = custom_query or f'{clean_comp} {clean_role} interview experience was asked coding round'

        urls = []
        try:
            ddg_url = "https://html.duckduckgo.com/html/"
            data = {"q": query, "s": str((page - 1) * 30)}
            resp = await client.post(ddg_url, data=data, headers=self.headers, timeout=10.0)
            if resp.status_code == 200:
                raw_html = resp.text
                found_links = re.findall(r'class="result__url"[^>]*href="([^"]+)"', raw_html)
                if not found_links:
                    found_links = re.findall(r'uddg=([^&"\']+)', raw_html)
                    found_links = [urllib.parse.unquote(l) for l in found_links]

                for link in found_links:
                    if link.startswith("//"):
                        link = "https:" + link
                    if not link.startswith("http"):
                        continue
                    domain = urlparse(link).netloc.lower()
                    if domain in BLOCKED_DOMAINS or any(b in domain for b in ["duckduckgo", "google", "bing"]):
                        continue
                    urls.append(link)
        except Exception as e:
            logger.warning(f"DuckDuckGo fallback search encountered: {e}")

        return list(dict.fromkeys(urls))

    async def discover_urls(
        self,
        client: Any,
        company: str,
        role: str,
        page: int = 1,
        yoe: float = 3.0,
        skills: Optional[List[str]] = None,
        round_number: Optional[int] = None,
    ) -> List[str]:
        """
        Discovers URLs using dynamic Nemotron-generated domain dorks across SearXNG
        and DuckDuckGo, adapting to the target company, role, YoE, skills, and specific round.
        """
        from models.model_manager import get_model_manager
        mm = get_model_manager()
        dorks_data = await mm.generate_domain_dorks(company=company, role=role, yoe=yoe, skills=skills)
        round_dorks = dorks_data.get("round_dorks", {})

        queries_to_try = []
        if round_number:
            key_map = {1: "round_1_oa", 2: "round_2_dsa", 3: "round_3_lld", 4: "round_4_hld", 5: "round_5_hr"}
            target_key = key_map.get(round_number, "round_2_dsa")
            queries_to_try.extend(round_dorks.get(target_key, []))
        else:
            for q_list in round_dorks.values():
                if q_list:
                    queries_to_try.append(q_list[0])

        all_urls: List[str] = []
        for q_str in queries_to_try[:3]:
            urls = await self._discover_urls_searxng(client, company, role, page=page, custom_query=q_str)
            if not urls:
                urls = await self._discover_urls_duckduckgo_fallback(client, company, role, page=page, custom_query=q_str)
            all_urls.extend(urls)

        return list(dict.fromkeys(all_urls))

    async def fetch_and_extract_article(self, client: Any, url: str) -> Optional[Dict[str, Any]]:
        """
        Fetches webpage with curl_cffi / httpx and performs universal main-body extraction
        via trafilatura, automatically stripping headers, footers, navigation, and comments.
        Drops paywalls, empty shells, and link farms under 400 characters.
        """
        try:
            resp = await client.get(url, timeout=12.0, follow_redirects=True)
            if resp.status_code != 200 or not resp.text or len(resp.text) < 800:
                return None

            # Universal main-body extraction across any webpage layout
            clean_text = trafilatura.extract(
                resp.text,
                include_comments=False,
                include_tables=True,
                no_fallback=False,
                output_format="txt",
            )

            # Drop short paywalls, empty shells, and link farms
            if not clean_text or len(clean_text.strip()) < 400:
                return None

            domain = urlparse(url).netloc.replace("www.", "")
            return {
                "url": url,
                "platform": domain,
                "content": clean_text[:14000],  # Capped for LLM prompt context
                "length": len(clean_text),
            }
        except Exception as e:
            logger.debug(f"Extraction failed for {url}: {e}")
            return None

    async def harvest_open_web(
        self,
        company: str,
        role: str = "Software Engineer",
        page: int = 1,
        max_articles: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Coordinates full open-web discovery and universal body extraction.
        Returns a list of clean article payloads ready for the Nemotron gate.
        """
        extracted_articles = []

        if CURL_CFFI_AVAILABLE:
            try:
                async with CurlAsyncSession(impersonate="chrome124") as session:
                    urls = await self.discover_urls(session, company, role, page=page)
                    tasks = [self.fetch_and_extract_article(session, u) for u in urls[:max_articles]]
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    for r in results:
                        if isinstance(r, dict) and r.get("content"):
                            r["company"] = company
                            r["role"] = role
                            extracted_articles.append(r)
                    return extracted_articles
            except Exception as e:
                logger.warning(f"curl_cffi session encountered error ({e}), using httpx client.")

        # Resilient httpx client fallback
        async with httpx.AsyncClient(headers=self.headers, timeout=12.0) as client:
            urls = await self.discover_urls(client, company, role, page=page)
            tasks = [self.fetch_and_extract_article(client, u) for u in urls[:max_articles]]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in results:
                if isinstance(r, dict) and r.get("content"):
                    r["company"] = company
                    r["role"] = role
                    extracted_articles.append(r)

        return extracted_articles
