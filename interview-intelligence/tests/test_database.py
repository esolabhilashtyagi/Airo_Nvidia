"""
Database tests: Table operations, SQLite/PostgreSQL schema integrity, and vector embeddings.
"""

import pytest
from database.repository import DatabaseRepository
from database.models import Company, JobRole, InterviewQuestion


@pytest.fixture
def test_repo(tmp_path):
    db_file = tmp_path / "test_db.sqlite"
    repo = DatabaseRepository(database_url=f"sqlite:///{db_file}")
    return repo


def test_company_and_role_creation(test_repo):
    comp = test_repo.get_or_create_company("NVIDIA Corp", "Semiconductors")
    assert comp.name == "NVIDIA Corp"
    assert comp.normalized_name == "nvidia corp"

    role = test_repo.get_or_create_job_role("AI Systems Engineer", "AI Engineering")
    assert role.title == "AI Systems Engineer"


def test_question_insertion_and_deduplication(test_repo):
    q1, is_new1 = test_repo.insert_interview_question(
        company_name="Google",
        job_role="Software Engineer",
        question_text="Implement an LRU Cache with O(1) get and put operations.",
        question_category="Data Structures and Algorithms",
        difficulty="Medium",
        source_platform="LeetCode",
        original_url="https://leetcode.com/discuss/sample_lru",
    )
    assert is_new1 is True
    assert q1.company_name == "Google"

    # Insert duplicate question
    q2, is_new2 = test_repo.insert_interview_question(
        company_name="Google",
        job_role="Software Engineer",
        question_text="Implement an LRU Cache with O(1) get and put operations.",
        question_category="Data Structures and Algorithms",
        difficulty="Medium",
        source_platform="Reddit",
        original_url="https://reddit.com/r/sample_lru",
    )
    assert is_new2 is False
    assert q1.id == q2.id


def test_embedding_storage_and_search(test_repo):
    q, _ = test_repo.insert_interview_question(
        company_name="Amazon",
        job_role="SDE",
        question_text="Design a distributed key-value store with eventual consistency.",
        question_category="System Design",
        difficulty="Hard",
        source_platform="Reddit",
        original_url="https://reddit.com/sample_kv",
    )
    vec = [0.1] * 384
    test_repo.save_embedding(q.id, vec)

    results = test_repo.search_similar_questions(vec, limit=5, min_similarity=0.9)
    assert len(results) >= 1
    assert results[0][0].id == q.id


def test_dynamic_blueprint_generation(test_repo):
    # Test Case A: Established Tech Giant (Google SDE II: 5 rounds)
    bp_swe = test_repo.get_interview_blueprint(
        company_name="Google",
        role="Software Development Engineer II",
        yoe=4.0,
        skills=["Python", "Distributed Systems", "Algorithms"],
    )
    assert bp_swe["target_type"] == "ESTABLISHED_COMPANY"
    assert bp_swe["total_rounds"] == 5
    assert "Google" in bp_swe["target_name"]
    assert any("Algorithms" in r["round_name"] or "Screening" in r["round_name"] for r in bp_swe["rounds"])

    # Test Case A: Netflix Tech (4 rounds, famous for No LeetCode, real systems debugging)
    bp_netflix = test_repo.get_interview_blueprint(
        company_name="Netflix",
        role="Senior Distributed Systems Engineer",
        yoe=6.0,
        skills=["Java", "Concurrency", "Kafka"],
    )
    assert bp_netflix["total_rounds"] == 4
    assert any("No LeetCode" in r["round_name"] or "Concurrency" in r["round_type"] for r in bp_netflix["rounds"])
    assert any("Keeper Test" in r["round_name"] or "Freedom" in r["round_name"] for r in bp_netflix["rounds"])

    # Test Case A: Non-Tech Specialist (Figma Product Designer: 4 rounds)
    bp_design = test_repo.get_interview_blueprint(
        company_name="Figma",
        role="Lead Product Designer",
        yoe=5.0,
        skills=["Figma", "Design Systems", "User Research"],
    )
    assert bp_design["role_family"] == "DESIGN"
    assert bp_design["total_rounds"] == 4
    assert any("Whiteboard" in r["round_name"] or "Design" in r["round_name"] for r in bp_design["rounds"])

    # Test Junior Tech (Entry-level 1.5 yrs: should NOT have distributed systems)
    bp_junior = test_repo.get_interview_blueprint(
        company_name="Amazon",
        role="Software Development Engineer I",
        yoe=1.5,
        skills=["Java", "Data Structures"],
    )
    assert bp_junior["total_rounds"] == 5
    assert bp_junior["yoe_tier"] == "Entry (0-2 yrs)"
    # Round 4 for junior tech must be Object-Oriented Design / Clean Code, not Distributed Systems
    r4 = bp_junior["rounds"][3]
    assert "Object-Oriented" in r4["round_name"] or "Clean Code" in r4["round_name"] or "Modularity" in r4["round_type"]

    # Test Case B: Startup by Industry (4 rounds: practical & high velocity)
    bp_fintech = test_repo.get_interview_blueprint(
        industry="Fintech",
        role="Backend Engineer (Payments)",
        yoe=3.0,
        skills=["Kafka", "PostgreSQL", "Idempotency"],
    )
    assert bp_fintech["target_type"] == "STARTUP_INDUSTRY"
    assert bp_fintech["total_rounds"] == 4
    assert any("Founder" in r["round_name"] or "Machine Coding" in r["round_name"] for r in bp_fintech["rounds"])

    # Test Zero-Hardcoding: Brand new role and company
    bp_unseen = test_repo.get_interview_blueprint(
        company_name="SpaceX",
        role="Avionics Propulsion Systems Lead",
        yoe=7.0,
        skills=["Telemetry", "Fault Trees", "Embedded C++"],
    )
    assert bp_unseen["target_name"] == "SpaceX"
    assert bp_unseen["total_rounds"] in [4, 5]
    assert len(bp_unseen["rounds"][0]["questions"]) >= 1
