"""
Unit and Integration Tests for Upgraded Structured Collectors, Nemotron Structural Follow-ups,
Background Harvester Scheduler, and Dataset Maintenance.
"""

import pytest
import asyncio
from collectors.leetcode_collector import LeetCodeCollector
from collectors.gfg_collector import GFGCollector
from collectors.reddit_collector import RedditCollector
from collectors.company_blog_collector import CompanyBlogCollector
from models.nemotron_client import NemotronLocalClient
from core.scheduler import TaskScheduler
from scripts.maintain_dataset import audit_dataset, purge_noise_and_junk


@pytest.mark.asyncio
async def test_leetcode_collector_schema_and_backfill():
    collector = LeetCodeCollector()
    results = await collector.collect(limit=5, use_mock=True)
    assert len(results) == 5
    for item in results:
        assert item["source_platform"] == "LeetCode"
        assert "original_url" in item
        assert "title" in item
        assert len(item["raw_text"]) > 20
        assert "publication_date" in item


@pytest.mark.asyncio
async def test_gfg_collector_schema_and_backfill():
    collector = GFGCollector()
    results = await collector.collect(limit=4, use_mock=True, company="Uber")
    assert len(results) == 4
    for item in results:
        assert item["source_platform"] == "GeeksforGeeks"
        assert "original_url" in item
        assert "Round" in item["raw_text"] or "Round" in item["title"]


@pytest.mark.asyncio
async def test_reddit_collector_filtering_and_backfill():
    collector = RedditCollector()
    results = await collector.collect(limit=3, use_mock=True, company="Google")
    assert len(results) == 3
    for item in results:
        assert item["source_platform"] == "Reddit"
        assert "original_url" in item
        assert len(item["raw_text"]) > 30


@pytest.mark.asyncio
async def test_company_blog_collector_architecture_studies():
    collector = CompanyBlogCollector()
    results = await collector.collect(limit=3, use_mock=True)
    assert len(results) == 3
    for item in results:
        assert item["source_platform"] == "Engineering Blogs"
        assert "Architecture" in item["raw_text"] or "Design" in item["raw_text"]


@pytest.mark.asyncio
async def test_nemotron_structural_followup_synthesis():
    client = NemotronLocalClient()
    base_q = "Design an in-memory key-value cache with LRU eviction supporting get and set in O(1)."
    followups = await client.generate_structural_followups(
        base_question=base_q, company="Netflix", role="Senior Distributed Systems Engineer"
    )

    assert len(followups) == 2
    for variant in followups:
        assert variant["source_type"] == "ai_followup"
        assert variant["difficulty"] == "Hard"
        assert len(variant["question_text"]) > 50
        assert variant["category"] in [
            "Distributed Systems",
            "System Design",
            "Concurrency & Multi-Threading",
            "Data Structures & Algorithms",
        ]
        assert len(variant.get("skills_tested", [])) > 0
        # Ensure variants introduce architectural depth rather than superficial text
        assert any(
            term in variant["question_text"].lower()
            for term in ["active-active", "crdt", "partition", "circuit", "lock-free", "cas", "distributed", "resilience", "concurrency"]
        )


@pytest.mark.asyncio
async def test_scheduler_background_harvester_lifecycle():
    scheduler = TaskScheduler()
    status_init = scheduler.get_harvester_status()
    assert status_init["status"] == "STOPPED"

    scheduler.start_background_harvester(interval_seconds=1)
    status_started = scheduler.get_harvester_status()
    assert status_started["status"] == "RUNNING"

    # Let it initialize briefly
    await asyncio.sleep(0.5)

    scheduler.stop_background_harvester()
    status_stopped = scheduler.get_harvester_status()
    assert status_stopped["status"] == "STOPPED"


def test_dataset_audit_health():
    audit = audit_dataset()
    assert audit["status"] == "HEALTHY"
    assert audit["duplicate_hashes"] == 0
    assert audit["health_score_pct"] == 100.0
