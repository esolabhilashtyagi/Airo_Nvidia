"""
Unit tests for Universal Open-Web Extraction and Nemotron Gating Pipeline.
"""

import pytest
import trafilatura
from collectors.open_web_collector import OpenWebCollector, SEO_TITLE_RE, BLOCKED_DOMAINS
from core.workflow_state import workflow_state
from agents.coding_extraction_agent import CodingProblemExtractionAgent
from models.fallback_models import CANONICAL_CATEGORIES


def test_open_web_collector_regex_filters():
    # Verify SEO title filter blocks listicles
    assert SEO_TITLE_RE.search("Top 50 Google SDE Interview Questions")
    assert SEO_TITLE_RE.search("10 Most Common System Design Interview Questions and Answers")
    assert not SEO_TITLE_RE.search("My Google SDE II Onsite Interview Experience (Offer)")

    # Verify blocked domains
    assert "news.ycombinator.com" in BLOCKED_DOMAINS
    assert "quora.com" in BLOCKED_DOMAINS


def test_trafilatura_universal_body_extraction():
    raw_html = """
    <html>
        <head><title>Engineering Interview Experience</title></head>
        <body>
            <nav>Home | About | Contact Us | Privacy Policy</nav>
            <aside>Popular Posts: Top 10 tips to get hired!</aside>
            <article>
                <h1>My Atlassian SDE II Interview Loop</h1>
                <p>I recently interviewed at Atlassian for a backend engineer role. The process consisted of 4 rounds.</p>
                <p>In Round 1, they asked me to implement a distributed rate limiter supporting token bucket and sliding window counter.</p>
                <p>In Round 2, the question was finding the lowest common ancestor in a Git commit DAG in O(V + E) time.</p>
                <p>In Round 3, we designed a scalable notification engine broadcasting Jira alerts to over 10 million active users.</p>
            </article>
            <footer>Copyright 2026 Engineering Blog. All rights reserved.</footer>
        </body>
    </html>
    """
    clean_text = trafilatura.extract(raw_html, include_comments=False)
    assert clean_text is not None
    assert "Atlassian SDE II Interview Loop" in clean_text
    assert "distributed rate limiter" in clean_text
    # Navbars and footers should be stripped
    assert "Privacy Policy" not in clean_text
    assert "All rights reserved" not in clean_text


def test_cursor_pagination_workflow_state():
    comp = "TestCompanyUniq"
    role = "Senior Systems Engineer"

    p1 = workflow_state.get_cursor_page(comp, role)
    assert p1 >= 1

    next_p = workflow_state.advance_cursor_page(comp, role, 1)
    assert next_p == p1 + 1

    p_check = workflow_state.get_cursor_page(comp, role)
    assert p_check == next_p


@pytest.mark.asyncio
async def test_full_article_extraction_gate():
    agent = CodingProblemExtractionAgent()
    sample_article = (
        "I recently went through the Google SDE II interview process. "
        "In Round 1, the question asked was: Given an integer array nums and an integer k, "
        "return the maximum sum of a non-empty subarray such that the length is at most k. "
        "In Round 2, the interviewer asked me: Design a distributed rate limiter that throttles 500k requests/second "
        "across 3 geographical regions using a sliding window counter. "
        "Finally, in Round 3, the interviewer asked: Tell me about a time you had a fundamental technical disagreement "
        "with your tech lead and how you resolved it constructively."
    )

    qs = await agent.extract_questions_from_full_article(
        article_content=sample_article,
        company="Google",
        role="Software Development Engineer II",
        url="https://medium.com/@dev/google-interview",
        platform="medium.com",
    )

    assert len(qs) >= 2, f"Expected at least 2 extracted questions, got {len(qs)}"
    for q in qs:
        assert q["company_name"] == "Google"
        assert q["question_category"] in CANONICAL_CATEGORIES
        assert len(q["question_text"]) >= 25
