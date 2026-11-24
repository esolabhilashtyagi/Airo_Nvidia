"""
Live Multi-Source Web Scraper for Interview Intelligence Platform.
Performs real-time, live web collection of authentic interview questions from public developer
discussions, HackerNews Algolia real-time index, and engineering interview archives without paid APIs.
Enforces hard REJECT for noise, strict HTML/markdown stripping, atomicity, and accurate metadata attribution.
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
from core.logging import logger

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

# Domains that publish blog articles rather than raw interview question threads
BLOG_DOMAINS = [
    "medium.com", "businessinsider.com", "qz.com", "blogspot.com",
    "impactinterview.com", "wordpress.com", "alexgolec.dev", "javarevisited"
]


class LiveWebScraper:
    def __init__(self):
        self.db = get_db_repository()
        self.mm = get_model_manager()
        self.nlp = FallbackNLPModel()
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

        # First pass: parse with BeautifulSoup to clean markup, details/summary, etc.
        try:
            soup = BeautifulSoup(raw_text, "html.parser")
            # Decompose tags that are purely decorative or structural noise
            for tag in soup(["script", "style", "img", "svg"]):
                tag.decompose()
            clean = soup.get_text(" ", strip=True)
        except Exception:
            clean = re.sub(r"<[^>]+?>", " ", raw_text)

        clean = html.unescape(clean)
        # Strip markdown links [text](url) -> text
        clean = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", clean)
        # Strip markdown images ![alt](url)
        clean = re.sub(r"!\[[^\]]*\]\([^\)]+\)", " ", clean)
        # Strip markdown anchor links [text](#anchor)
        clean = re.sub(r"\[([^\]]+)\]\(#[^\)]+\)", r"\1", clean)
        # Strip code backticks
        clean = re.sub(r"`{1,3}", "", clean)
        # Collapse whitespace
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
        # Drop fragments under 8 words (or fewer than 35 characters)
        words = t.split()
        if len(words) < 8 or len(t) < 35 or len(t) > 700:
            return False

        t_low = t.lower()

        # Reject conversational garbage, forum rants, and article titles
        for pat in GARBAGE_PATTERNS:
            if re.search(pat, t_low):
                return False

        # Must have an action verb or end with '?'
        action_verbs = [
            "given ", "implement ", "design ", "explain ", "how do you ", "how would you ",
            "write a ", "find the ", "what is the ", "describe a ", "suppose you have ",
            "you are given ", "create a ", "calculate ", "reverse ", "solve ", "construct ",
            "can you ", "why does ", "optimize ", "walk through ", "compare "
        ]
        has_action = any(t_low.startswith(p) or f" {p}" in t_low for p in action_verbs)
        has_qmark = t.endswith("?")

        # Must contain at least one technical domain word
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

        # Split into sentences or lines
        sentences = re.split(r"(?<=[.!?\n])\s+", clean_text)

        for s in sentences:
            s_clean = s.strip()
            if not s_clean:
                continue

            if s_clean.startswith(">") or s_clean.startswith("&gt;"):
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
        Executes live web scraping across public developer indexes for the specified company/query.
        Enforces strict company attribution and craft role derivation.
        """
        is_all = not company or company.strip().lower() in ["all", "all companies", "all mncs", "all startups", ""]
        comp_target = "Google" if is_all else company.strip()

        # Build clean search queries targeting genuine question posts
        search_terms = []
        if keyword:
            search_terms.append(f"{comp_target} {keyword} coding interview")

        if is_all:
            for c in ["Google", "Amazon", "Meta", "NVIDIA", "Microsoft", "Stripe", "Databricks", "OpenAI", "Uber"][:6]:
                search_terms.append(f"{c} coding round question")
                search_terms.append(f"{c} system design question")
        else:
            search_terms.extend([
                f"{comp_target} coding interview question",
                f"{comp_target} system design interview question",
                f"{comp_target} online assessment OA question",
                f"{comp_target} machine coding interview",
            ])

        extracted_raw_records = []
        hits_per_page = 50 if (limit and limit <= 100) else 100
        pages_to_crawl = max(1, min(max_pages, 8))

        async with httpx.AsyncClient(headers=self.headers, timeout=15.0) as client:
            # 1. Real-time HackerNews Search API (Public, Zero auth)
            for term in search_terms:
                if limit and len(extracted_raw_records) >= limit * 3:
                    break
                for page in range(pages_to_crawl):
                    if limit and len(extracted_raw_records) >= limit * 3:
                        break
                    try:
                        url = f"https://hn.algolia.com/api/v1/search?query={term}&tags=comment&hitsPerPage={hits_per_page}&page={page}"
                        res = await client.get(url)
                        if res.status_code == 200:
                            hits = res.json().get("hits", [])
                            if not hits:
                                break
                            for h in hits:
                                raw_body = h.get("comment_text") or ""
                                clean_body = self._clean_html_and_markdown(raw_body)
                                if len(clean_body) >= 50:
                                    post_id = h.get("objectID")
                                    story_url = h.get("story_url") or ""

                                    # Reject blog post discussions
                                    if any(bd in story_url.lower() for bd in BLOG_DOMAINS):
                                        continue

                                    hit_url = f"https://news.ycombinator.com/item?id={post_id}"
                                    extracted_raw_records.append({
                                        "title": f"{comp_target} Technical Discussion",
                                        "text": clean_body,
                                        "url": hit_url,
                                        "platform": "HackerNews Public Live Index",
                                        "is_archive": False,
                                        "explicit_company": comp_target if comp_target.lower() in clean_body.lower() else None,
                                    })
                    except Exception as e:
                        logger.warning(f"Live web scrape query '{term}' p.{page} encountered: {e}")
                        break

            # 2. Ingest from high-yield GitHub Open Interview Repositories if batch is requested
            for arch in GITHUB_ARCHIVES:
                try:
                    res = await client.get(arch["url"])
                    if res.status_code == 200 and len(res.text) > 500:
                        extracted_raw_records.append({
                            "title": arch["platform"],
                            "text": res.text[:60000],
                            "url": arch["url"],
                            "platform": arch["platform"],
                            "is_archive": True,
                            "archive_domain": arch["archive_domain"],
                            "explicit_company": None,
                        })
                except Exception as e:
                    logger.warning(f"Archive fetch for {arch['url']} failed: {e}")

        # Parse questions from all collected documents
        candidate_questions = []
        seen_hashes = set()

        for rec in extracted_raw_records:
            qs = self._extract_questions_from_text(rec["text"], comp_target)
            for q in qs:
                q_text = q["question_text"]
                q_hash = get_dedup_hash(q_text)
                if q_hash in seen_hashes:
                    continue
                seen_hashes.add(q_hash)

                cls = self.nlp.classify_question(q_text)

                # Strict metadata attribution: NEVER stamp target company onto generic GitHub archives!
                if rec.get("is_archive"):
                    if not is_all and comp_target.lower() in q_text.lower():
                        assigned_company = comp_target
                    else:
                        assigned_company = rec.get("archive_domain", "Core Systems & Algorithms")
                else:
                    assigned_company = rec.get("explicit_company") or (comp_target if comp_target.lower() in q_text.lower() else "Core Technical Practice")

                assigned_role = self._infer_role_from_category(cls["category"], role)

                candidate_questions.append({
                    "company_name": assigned_company,
                    "job_role": assigned_role,
                    "question_text": q_text,
                    "question_category": cls["category"],
                    "difficulty": q["difficulty"],
                    "round_number": q["round_number"],
                    "interview_round": q["interview_round"],
                    "source_platform": rec["platform"],
                    "original_url": rec["url"],
                    "confidence_score": 0.95,
                    "skills_tested": [cls["category"], "Problem Solving"],
                })

                if limit and len(candidate_questions) >= limit:
                    break
            if limit and len(candidate_questions) >= limit:
                break

        # Bulk insert into database with canonical number-masked deduplication
        stored_count = 0
        if candidate_questions:
            stored_count = self.db.bulk_insert_questions(candidate_questions, batch_size=250)

        return {
            "company": comp_target,
            "scraped_sources_count": len(extracted_raw_records),
            "extracted_questions_count": len(candidate_questions),
            "stored_in_database": stored_count,
            "questions": candidate_questions[:50],
        }
