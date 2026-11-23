"""
Unit tests for specialized agent components.
"""

import pytest
from agents.enrichment_agent import DataEnrichmentAgent
from agents.verification_agent import AuthenticityVerificationAgent
from agents.coding_extraction_agent import CodingProblemExtractionAgent
from agents.quality_agent import QualityAssuranceAgent


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
