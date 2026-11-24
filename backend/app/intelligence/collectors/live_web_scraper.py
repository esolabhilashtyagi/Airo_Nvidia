"""
Live Multi-Source Web Scraper for Interview Intelligence Platform.
Performs real-time, live web collection of authentic interview questions from:
1. Search Discovery (SearXNG / Multi-Engine) -> Universal Article Body Extraction (curl_cffi + trafilatura) -> Nemotron Extraction Gate
2. Open-source interview repositories & verified developer discussions
Enforces hard REJECT for noise, strict HTML/markdown stripping, atomicity, persistent cursor pagination,
and accurate metadata attribution.
"""

import httpx
import re
import html
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from bs4 import BeautifulSoup

from database.repository import get_db_repository
from models.model_manager import get_model_manager
from models.fallback_models import (
    FallbackNLPModel,
    strip_question_wrappers,
    canonicalize_text,
    get_dedup_hash,
    CANONICAL_CATEGORIES,
)
from core.workflow_state import workflow_state
from core.logging import logger
from collectors.open_web_collector import OpenWebCollector
from agents.coding_extraction_agent import CodingProblemExtractionAgent

TECH_GIANTS_AND_STARTUPS = [
    "Google", "Amazon", "Meta", "NVIDIA", "Microsoft", "Apple", "Netflix", "Uber",
    "Stripe", "Databricks", "OpenAI", "Figma", "Snowflake", "Airbnb", "DoorDash",
    "Palantir", "Atlassian", "Salesforce", "Coinbase", "ByteDance", "LinkedIn",
    "Twitter", "Adobe", "Intel", "Qualcomm", "AMD", "Oracle", "Cisco", "Spotify",
    "Snap", "Pinterest", "Zoom", "Square", "GitHub", "GitLab", "Docker", "Twilio"
]

GITHUB_ARCHIVES = [
    {
        "url": "https://raw.githubusercontent.com/donnemartin/system-design-primer/master/README.md",
        "archive_domain": "System Design Architecture",
        "category": "System Design",
        "platform": "System Design Primer Archive",
    },
    {
        "url": "https://raw.githubusercontent.com/kdn251/interviews/master/README.md",
        "archive_domain": "Core Algorithms & Data Structures",
        "category": "Data Structures and Algorithms",
        "platform": "GitHub Tech Interviews Archive",
    },
    {
        "url": "https://raw.githubusercontent.com/bregman-arie/devops-exercises/master/topics/linux/README.md",
        "archive_domain": "Linux Kernel & Systems Engineering",
        "category": "Operating Systems",
        "platform": "DevOps & Systems Exercises Archive",
    },
    {
        "url": "https://raw.githubusercontent.com/bregman-arie/devops-exercises/master/topics/networking/README.md",
        "archive_domain": "Computer Networks & Protocols",
        "category": "Computer Networks",
        "platform": "DevOps & Networking Exercises Archive",
    },
    {
        "url": "https://raw.githubusercontent.com/bregman-arie/devops-exercises/master/topics/databases/README.md",
        "archive_domain": "Database Engines & SQL",
        "category": "DBMS and SQL",
        "platform": "DevOps & Database Exercises Archive",
    },
]

# Patterns for automatic hard REJECT (blog headlines, forum debates, rants, meta-questions)
GARBAGE_PATTERNS = [
    r"^>\s*",
    r"^&gt;\s*",
    r"could someone please suggest",
    r"suggest some website",
    r"where can i practice",
    r"questions are quickly becoming obsolete",
    r"day-to-day responsibilities",
    r"struggled to answer",
    r"interview questions deconstructed",
    r"interview questions that will make you feel",
    r"interview questions for growth",
    r"eric schmidt",
    r"salary discussion",
    r"compensation breakdown",
    r"referral link",
    r"blind post",
    r"levels\.fyi",
    r"i recently completed my .* interview",
    r"round 1 was .* round 2 was",
    r"do you think .* would be tolerated",
    r"male-only hiring",
    r"why are interviews broken",
    r"^how would you do\??$",
    r"^what about\??$",
    r"^any thoughts\??$",
    r"^can you explain\??$",
    r"^how many golf balls can fit",
    r"fun brain teasers",
    r"top \d+",
    r"answers to \d+",
    r"\d+ .* interview questions",
    r"acing the .* interview",
    r"^looking for resources to help",
    r"^practice by solving",
    r"^\*?\s*\[.*\]\(#",
    r"^###\s+Step",
    r"what each of the following commands does",
    r"what the following commands do",
    r"what are hidden files",
    r"what is the difference between these two commands",
    r"what is escaping",
    r"what is sudo",
    r"what is a swap partition",
    r"true or false\?",
    r"in linux fhs",
]

BLOG_DOMAINS = [
    "medium.com", "businessinsider.com", "qz.com", "blogspot.com",
    "impactinterview.com", "wordpress.com", "alexgolec.dev", "javarevisited"
]


class LiveWebScraper:
    def __init__(self):
        self.db = get_db_repository()
        self.mm = get_model_manager()
        self.nlp = FallbackNLPModel()
        self.open_collector = OpenWebCollector()
        self.coding_agent = CodingProblemExtractionAgent()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, text/markdown, */*",
        }

    def _clean_html_and_markdown(self, raw_text: str) -> str:
        """
        Strips HTML tags via BeautifulSoup, removes markdown table of contents links,
        markdown images, code backticks, and collapses whitespace.
        """
        if not raw_text:
            return ""

        try:
            soup = BeautifulSoup(raw_text, "html.parser")
            for tag in soup(["script", "style", "img", "svg"]):
                tag.decompose()
            clean = soup.get_text(" ", strip=True)
        except Exception:
            clean = re.sub(r"<[^>]+?>", " ", raw_text)

        clean = html.unescape(clean)
        clean = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", clean)
        clean = re.sub(r"!\[[^\]]*\]\([^\)]+\)", " ", clean)
        clean = re.sub(r"\[([^\]]+)\]\(#[^\)]+\)", r"\1", clean)
        clean = re.sub(r"`{1,3}", "", clean)
        clean = re.sub(r"\s+", " ", clean).strip()
        return clean

    def _infer_round(self, text: str) -> tuple[int, str]:
        """Infers interview round number (1 to 5) and title from question content."""
        t_low = text.lower()
        if any(k in t_low for k in ["online assessment", "oa", "screening", "hackerrank", "codesignal"]):
            return 1, "Round 1: Online Assessment (OA)"
        if any(k in t_low for k in ["system design", "architecture", "distributed", "scalability", "microservices", "raft", "sharding", "p99", "kafka"]):
            return 4, "Round 4: Large-Scale System Design"
        if any(k in t_low for k in ["machine coding", "low level design", "lld", "concurrency", "thread", "mutex", "lock-free", "cache implementation", "rate limiter"]):
            return 3, "Round 3: Machine Coding & Concurrency (LLD)"
        if any(k in t_low for k in ["behavioral", "leadership", "tell me about a time", "conflict", "culture", "lp", "values", "mentor", "proudest"]):
            return 5, "Round 5: Behavioral & Leadership (HR)"
        return 2, "Round 2: Core Coding & Problem Solving (DSA)"

    def _infer_difficulty(self, text: str) -> str:
        """Infers question difficulty based on technical depth."""
        t_low = text.lower()
        if any(k in t_low for k in ["distributed", "consensus", "lock-free", "raft", "p99", "kernel", "cuda", "np-hard", "hard", "byzantine", "btree", "lsm"]):
            return "Hard"
        if any(k in t_low for k in ["easy", "two sum", "reverse", "palindrome", "valid anagram"]):
            return "Easy"
        return "Medium"

    def _infer_role_from_category(self, category: str, requested_role: str = "") -> str:
        """Assigns accurate craft job role based on topic category to prevent blind role hallucination."""
        if category == "Product Management":
            return "Senior Product Manager"
        if category in ["Operating Systems", "Computer Networks"]:
            return "Systems & Infrastructure Software Engineer"
        if category == "DBMS and SQL":
            return "Backend & Database Engineer"
        if category == "Machine Learning":
            return "Machine Learning Engineer"
        if category == "UI/UX Design":
            return "Lead Product Designer"
        if requested_role and requested_role.strip().lower() not in ["", "all", "all roles", "general"]:
            return requested_role.strip()
        return "Software Development Engineer II"

    def _is_valid_technical_question(self, text: str) -> bool:
        """Strictly validates whether candidate text is an actual technical interview question."""
        t = text.strip()
        words = t.split()
        if len(words) < 8 or len(t) < 35 or len(t) > 700:
            return False

        t_low = t.lower()
        for pat in GARBAGE_PATTERNS:
            if re.search(pat, t_low):
                return False

        action_verbs = [
            "given ", "implement ", "design ", "explain ", "how do you ", "how would you ",
            "write a ", "find the ", "what is the ", "describe a ", "suppose you have ",
            "you are given ", "create a ", "calculate ", "reverse ", "solve ", "construct ",
            "can you ", "why does ", "optimize ", "walk through ", "compare "
        ]
        has_action = any(t_low.startswith(p) or f" {p}" in t_low for p in action_verbs)
        has_qmark = t.endswith("?")

        tech_words = [
            "array", "tree", "graph", "cache", "string", "query", "sql", "thread", "lock",
            "concurrency", "database", "latency", "system", "service", "algorithm", "dp",
            "heap", "queue", "stack", "list", "memory", "server", "metric", "network", "socket",
            "sharding", "kafka", "redis", "transaction", "index", "raft", "paxos"
        ]
        has_tech = any(w in t_low for w in tech_words)

        return (has_action or has_qmark) and has_tech

    def _extract_questions_from_text(self, text: str, default_company: str = "Google") -> List[Dict[str, Any]]:
        """Extracts substantive atomic interview questions from free-form text or markdown."""
        questions = []
        if not text:
            return questions

        clean_text = self._clean_html_and_markdown(text)
        sentences = re.split(r"(?<=[.!?\n])\s+", clean_text)

        for s in sentences:
            s_clean = s.strip()
            if not s_clean or s_clean.startswith(">") or s_clean.startswith("&gt;"):
                continue

            cleaned_s = strip_question_wrappers(s_clean)
            if self._is_valid_technical_question(cleaned_s):
                r_num, r_name = self._infer_round(cleaned_s)
                diff = self._infer_difficulty(cleaned_s)
                questions.append({
                    "question_text": cleaned_s,
                    "round_number": r_num,
                    "interview_round": r_name,
                    "difficulty": diff,
                })

        return questions

    async def scrape_live_questions(
        self,
        company: str,
        role: str = "Software Engineer",
        keyword: str = "",
        limit: Optional[int] = 50,
        max_pages: int = 5,
    ) -> Dict[str, Any]:
        """
        Executes multi-engine discovery across the open web and public archives.
        Uses persistent cursor pagination and the Nemotron gate for full article extraction.
        """
        is_all = not company or company.strip().lower() in ["all", "all companies", "all mncs", "all startups", ""]
        comp_target = "Google" if is_all else company.strip()
        role_target = role.strip() if role and role.lower() not in ["", "all", "all roles"] else "Software Development Engineer II"

        cursor_page = workflow_state.get_cursor_page(comp_target, role_target)
        logger.info(f"Scraping live questions for {comp_target} ({role_target}) at cursor page {cursor_page}...")

        candidate_questions = []
        seen_hashes = set()
        scraped_sources_count = 0

        # =========================================================================
        # STAGE 1 & 2: Search Discovery -> Universal Body Extraction (trafilatura)
        # =========================================================================
        try:
            articles = await self.open_collector.harvest_open_web(
                company=comp_target,
                role=role_target,
                page=cursor_page,
                max_articles=10 if (limit and limit <= 100) else 15,
            )
            scraped_sources_count += len(articles)

            # Advance cursor page for next run
            workflow_state.advance_cursor_page(comp_target, role_target, 1)

            # STAGE 3: Nemotron / LLM Extraction Gate on Full Articles
            for art in articles:
                gated_qs = await self.coding_agent.extract_questions_from_full_article(
                    article_content=art["content"],
                    company=comp_target,
                    role=role_target,
                    url=art["url"],
                    platform=art["platform"],
                )
                for gq in gated_qs:
                    q_hash = get_dedup_hash(gq["question_text"])
                    if q_hash not in seen_hashes:
                        seen_hashes.add(q_hash)
                        candidate_questions.append(gq)

                if limit and len(candidate_questions) >= limit:
                    break
        except Exception as e:
            logger.warning(f"Open-web harvest encountered: {e}")

        # =========================================================================
        # STAGE 4: Developer Discussion Index (STRICTLY EXCLUDES HN COMMENTS)
        # =========================================================================
        # We strictly block all news.ycombinator.com and random forum comments
        # to ensure 0% comment noise in the repository.

        # Bulk insert into database with canonical number-masked deduplication
        stored_count = 0
        if candidate_questions:
            # Ensure no HN item slipped in
            clean_candidates = [
                q for q in candidate_questions
                if not any(hn in q.get("original_url", "").lower() for hn in ["news.ycombinator.com", "item?id=", "algolia.com"])
                and q.get("source_platform") not in ["HackerNews", "HackerNews Public Live Index", "Developer Technical Discussion"]
            ]
            if clean_candidates:
                stored_count = self.db.bulk_insert_questions(clean_candidates, batch_size=250)

        return {
            "company": comp_target,
            "cursor_page": cursor_page,
            "scraped_sources_count": scraped_sources_count,
            "extracted_questions_count": len(candidate_questions),
            "stored_in_database": stored_count,
            "questions": candidate_questions[:50],
        }
