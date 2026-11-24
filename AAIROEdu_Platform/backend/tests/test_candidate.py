import uuid
import pytest
from httpx import AsyncClient
from pydantic import ValidationError

from app.schemas.candidate import OnboardingStepRequest


def test_onboarding_schema_treats_blank_industry_id_as_unset():
    assert OnboardingStepRequest(step=1, industry_id="").industry_id is None
    assert OnboardingStepRequest(step=1, industry_id="   ").industry_id is None
    assert OnboardingStepRequest(step=1, industry_id=None).industry_id is None

    with pytest.raises(ValidationError):
        OnboardingStepRequest(step=1, industry_id="not-a-uuid")


@pytest.mark.asyncio
async def test_candidate_profile_and_onboarding(async_client: AsyncClient, candidate_headers: dict):
    # 1. Get Profile
    prof_res = await async_client.get("/api/v1/candidates/profile", headers=candidate_headers)
    assert prof_res.status_code == 200
    prof = prof_res.json()["data"]
    assert prof["onboarding_step"] >= 1

    # 2. Save Onboarding Step 1 (Candidate Type)
    step1_res = await async_client.post(
        "/api/v1/candidates/onboarding/step",
        headers=candidate_headers,
        json={
            "step": 1,
            "candidate_type": "working_professional",
            "sub_category": "job_seeker"
        }
    )
    assert step1_res.status_code == 200
    assert step1_res.json()["data"]["candidate_type"] == "working_professional"

    # 3. Save Onboarding Step 4 (Professional Details)
    step4_res = await async_client.post(
        "/api/v1/candidates/onboarding/step",
        headers=candidate_headers,
        json={
            "step": 4,
            "current_company": "Acme Technologies",
            "current_role": "Backend Engineer",
            "target_role": "Senior Software Architect",
            "total_experience_months": 36,
            "key_skills": ["Python", "Docker", "PostgreSQL", "FastAPI"]
        }
    )
    assert step4_res.status_code == 200
    updated_data = step4_res.json()["data"]
    assert updated_data["target_role"] == "Senior Software Architect"
    assert "FastAPI" in updated_data["key_skills"]


@pytest.mark.asyncio
async def test_full_onboarding_persists_after_relogin(async_client: AsyncClient):
    email = f"onboarding_{uuid.uuid4().hex[:10]}@aairo.ai"
    password = "ZzTestOnboardingSecure456!"
    registration = await async_client.post("/api/v1/auth/register", json={
        "email": email, "password": password, "full_name": "Onboarding Test"
    })
    assert registration.status_code == 201

    first_login = await async_client.post("/api/v1/auth/login", json={"email": email, "password": password})
    headers = {"Authorization": f"Bearer {first_login.json()['data']['access_token']}"}
    industries = await async_client.get("/api/v1/industries")
    industry_id = industries.json()["data"][0]["id"]

    steps = [
        {"step": 1, "candidate_type": "student_fresher", "sub_category": "final_year_student"},
        {"step": 2, "industry_id": industry_id},
        {"step": 3, "education": [{"degree": "BSc", "field_of_study": "Biology", "institution": "Example University", "end_year": 2027}]},
        {"step": 4, "target_role": "Research Associate", "total_experience_months": 0, "key_skills": ["Research"]},
        {"step": 5, "interview_rounds_preferred": ["HR", "Domain-Specific"]},
        {"step": 6, "target_companies": [{"company_name": "Example Labs", "target_role": "Research Associate"}]},
        {"step": 7, "interaction_preference": "text", "is_final_step": True},
    ]
    for payload in steps:
        response = await async_client.post("/api/v1/candidates/onboarding/step", headers=headers, json=payload)
        assert response.status_code == 200, response.text

    relogin = await async_client.post("/api/v1/auth/login", json={"email": email, "password": password})
    persisted_headers = {"Authorization": f"Bearer {relogin.json()['data']['access_token']}"}
    persisted = await async_client.get("/api/v1/candidates/profile", headers=persisted_headers)
    assert persisted.status_code == 200
    profile = persisted.json()["data"]
    assert profile["onboarding_completed"] is True
    assert profile["onboarding_step"] == 7
    assert profile["candidate_type"] == "student_fresher"
    assert profile["education_history"][0]["institution"] == "Example University"
    assert profile["target_companies"][0]["company"]["name"] == "Example Labs"
    company_search = await async_client.get("/api/v1/companies", params={"search": "Example Labs"})
    assert company_search.status_code == 200
    assert company_search.json()["data"][0]["name"] == "Example Labs"
