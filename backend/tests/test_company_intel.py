import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_company_intel_list_and_filter(async_client: AsyncClient):
    # 1. List questions for Google
    res = await async_client.get("/api/v1/questions/company-intel?company=Google")
    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data) > 0
    first_q = data[0]
    assert first_q["company_name"] == "Google"
    assert first_q["verification_status"] == "VERIFIED"
    assert "question_text" in first_q
    assert "interview_round" in first_q

    # 2. Filter by canonical Round 2 (DSA)
    res_dsa = await async_client.get("/api/v1/questions/company-intel?company=Google&round_number=2")
    assert res_dsa.status_code == 200
    data_dsa = res_dsa.json()["data"]
    assert len(data_dsa) > 0
    for q in data_dsa:
        assert q["round_number"] == 2


@pytest.mark.asyncio
async def test_company_intel_directory(async_client: AsyncClient):
    # List indexed companies
    res = await async_client.get("/api/v1/questions/company-intel/companies")
    assert res.status_code == 200
    companies = res.json()["data"]
    assert len(companies) >= 20
    comp_names = [c["name"] for c in companies]
    assert "Google" in comp_names
    assert "Meta" in comp_names
    assert "Amazon" in comp_names


@pytest.mark.asyncio
async def test_company_intel_hiring_blueprint(async_client: AsyncClient):
    # Get 5-round hiring blueprint for Google
    res = await async_client.get("/api/v1/questions/company-intel/blueprint/Google")
    assert res.status_code == 200
    blueprint = res.json()["data"]
    assert blueprint["company_name"] == "Google"
    assert blueprint["total_rounds"] == 5
    assert len(blueprint["rounds"]) == 5
    assert "hiring_philosophy" in blueprint

    round_numbers = [r["round_number"] for r in blueprint["rounds"]]
    assert round_numbers == [1, 2, 3, 4, 5]


@pytest.mark.asyncio
async def test_company_intel_practice_evaluation(async_client: AsyncClient):
    # Fetch a question to practice
    res = await async_client.get("/api/v1/questions/company-intel?company=Google&limit=1")
    assert res.status_code == 200
    q = res.json()["data"][0]

    # Evaluate practice answer
    prac_res = await async_client.post(
        "/api/v1/questions/company-intel/practice",
        json={
            "question_id": q["id"],
            "user_response": "We use a hash map with two pointers in O(N) time and O(1) space, handling edge cases of empty input."
        }
    )
    assert prac_res.status_code == 200
    result = prac_res.json()["data"]
    assert result["question_id"] == q["id"]
    assert "score_percentage" in result
    assert result["score_percentage"] >= 60
    assert "feedback" in result
    assert "expected_answer" in result


@pytest.mark.asyncio
async def test_company_intel_generate_dorks(async_client: AsyncClient):
    # Test dynamic dorks generation
    res = await async_client.post(
        "/api/v1/questions/company-intel/generate-dorks",
        json={
            "company": "Google",
            "role": "Software Development Engineer",
            "yoe": 4.0,
            "skills": ["Python", "Distributed Systems"]
        }
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["company"] == "Google"
    assert "round_dorks" in data
    assert len(data["round_dorks"]) >= 5
    assert "platform_queries" in data


@pytest.mark.asyncio
async def test_company_intel_round_questions(async_client: AsyncClient):
    # Test verified round question synthesis
    res = await async_client.post(
        "/api/v1/questions/company-intel/round-questions",
        json={
            "company": "Google",
            "role": "Software Development Engineer",
            "yoe": 4.0,
            "skills": ["Python", "Algorithms"]
        }
    )
    assert res.status_code == 200
    questions = res.json()["data"]
    assert len(questions) > 0
    rounds_present = set(q["round_number"] for q in questions)
    assert {1, 2, 3, 4, 5}.issubset(rounds_present)
    for q in questions:
        assert q["company"] == "Google"
        assert len(q["question_text"]) > 20
        assert q["verification_status"] == "VERIFIED"
