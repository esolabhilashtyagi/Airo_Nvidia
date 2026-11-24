"""
Unit tests for specialized agent components.
"""

import pytest
from agents.enrichment_agent import DataEnrichmentAgent
from agents.verification_agent import AuthenticityVerificationAgent
from agents.coding_extraction_agent import CodingProblemExtractionAgent
from agents.quality_agent import QualityAssuranceAgent
from agents.deduplication_agent import DeduplicationAgent
from agents.classification_agent import QuestionClassificationAgent
from models.fallback_models import canonicalize_text, CANONICAL_CATEGORIES
from database.repository import get_db_repository


def test_enrichment_agent_canonicalization():
    enricher = DataEnrichmentAgent()
    data = {
        "company_name": "google inc",
        "job_role": "sde 2",
        "raw_text": "We discussed Python, Docker, and Kubernetes microservices.",
    }
    enriched = enricher.enrich_experience(data)
    assert enriched["company_name"] == "Google"
    assert enriched["job_role"] == "Software Development Engineer II"
    assert "Python" in enriched["detected_skills"]
    assert "Kubernetes" in enriched["detected_skills"]


@pytest.mark.asyncio
async def test_authenticity_verification():
    verifier = AuthenticityVerificationAgent()
    first_person_text = "In my interview with Microsoft, the interviewer asked me about sliding window algorithms."
    ver_res = await verifier.verify_record(first_person_text)
    assert ver_res["is_first_person"] is True
    assert ver_res["confidence_score"] >= 0.70


@pytest.mark.asyncio
async def test_coding_problem_extraction():
    extractor = CodingProblemExtractionAgent()
    q = (
        "Problem: Two Sum II\n"
        "Input format: Array of integers numbers sorted in non-decreasing order.\n"
        "Constraints: 2 <= numbers.length <= 3 * 10^4.\n"
        "Example 1: numbers = [2,7,11,15], target = 9. Output: [1,2]"
    )
    res = await extractor.extract_coding_problem(q, "https://example.com/twosum")
    assert res is not None
    assert "constraints" in res and res["constraints"] is not None
    assert "Two Sum" in res["title"]


def test_quality_assurance_agent():
    qa = QualityAssuranceAgent()
    valid_doc = {
        "source_platform": "Reddit",
        "original_url": "https://reddit.com/r/test",
        "raw_text": "This is a sufficiently long raw document text describing interview questions.",
    }
    assert qa.validate_raw_document(valid_doc) is True

    invalid_doc = {"source_platform": "Reddit"}
    assert qa.validate_raw_document(invalid_doc) is False


def test_deduplication_canonical_numeric_masking():
    """Verifies that combinatorial number-swapping collapses into identical canonical form."""
    q1 = "Given a stream of incoming HTTP requests, throttle users exceeding 100 requests in 1 second."
    q2 = "In an interview for SDE at Google: Given a stream of incoming HTTP requests, throttle users exceeding 50,000 requests in 60 seconds."
    c1 = canonicalize_text(q1)
    c2 = canonicalize_text(q2)
    assert "<num>" in c1
    assert "<num>" in c2
    assert c1 == c2, f"Expected canonicalized questions to match, got: {c1} vs {c2}"


@pytest.mark.asyncio
async def test_classification_canonical_categories():
    """Verifies that classification outputs are strictly within CANONICAL_CATEGORIES and reject '* Domain'."""
    classifier = QuestionClassificationAgent()
    questions = [
        "Given an array of integers, find the maximum subarray sum in O(N).",
        "Design a distributed rate limiter supporting 500k requests/second.",
        "Implement a thread-safe LRU cache with O(1) read and write operations.",
        "Trapping Rain Water: calculate how much water can be trapped after raining.",
    ]
    for q in questions:
        res = await classifier.classify_question(q)
        cat = res["category"]
        assert cat in CANONICAL_CATEGORIES, f"Category '{cat}' is not canonical!"
        assert "Domain" not in cat, f"Detected '* Domain' bug in category: {cat}"


def test_repository_company_isolation():
    """Verifies that searching for a company (Atlassian) returns strictly Atlassian questions without company leakage."""
    db = get_db_repository()
    qs = db.get_maximum_relevant_questions(
        company="Atlassian",
        role="Software Development Engineer",
        yoe=4.0,
        skills=["Java", "Distributed Systems"],
        limit=20,
    )
    assert len(qs) > 0, "Expected Atlassian questions to be returned"
    for q in qs:
        assert q.company_name == "Atlassian", f"Company leakage detected: {q.company_name} in Atlassian search!"
