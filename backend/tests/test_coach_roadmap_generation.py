import asyncio
import re
from types import SimpleNamespace
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import event, select
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal, async_engine
from app.models.candidate import CandidateProfile, Education, ProfessionalExperience
from app.models.module import Module, Roadmap
from app.models.taxonomy import Industry, JobRole, Skill
from app.models.user import User

from app.integrations.ai.base import AIResponse
from app.services import coach_service


class RoadmapProvider:
    def __init__(self, data=None, available=True):
        self.data = data
        self.available = available
        self.prompt = ""
        self.calls = 0

    def is_available(self):
        return self.available

    async def generate_structured(self, prompt, response_schema, **_kwargs):
        self.prompt = prompt
        self.calls += 1
        return AIResponse(
            structured_data=self.data,
            provider_name="test-provider",
            model_name="test-model",
            is_success=self.data is not None,
        )


def valid_steps():
    return {"steps": [
        {"title": f"Transition milestone {index}", "description": f"Complete practical learning and practice activity {index} for the target role."}
        for index in range(1, 7)
    ]}


@pytest.mark.asyncio
async def test_ai_transition_plan_is_role_aware_and_does_not_send_direct_identifiers(monkeypatch):
    provider = RoadmapProvider(valid_steps())
    monkeypatch.setattr(coach_service, "get_ai_provider", lambda: provider)
    profile = SimpleNamespace(
        current_role="Software Engineer", target_role="HR Generalist",
        total_experience_months=48, key_skills=["Python", "People analytics"],
        education_history=[SimpleNamespace(degree="BA", field_of_study="Psychology")],
        full_name="Private Test Candidate", email="private@example.com",
        current_company="Private Employer", experience_history=[],
        career_goals="Move into employee relations in my target jurisdiction",
    )

    steps = await coach_service.CoachService._generate_transition_steps(profile, "Human Resources")

    assert len(steps) == 6
    assert "Software Engineer" in provider.prompt
    assert "HR Generalist" in provider.prompt
    assert "People analytics" in provider.prompt
    assert profile.career_goals in provider.prompt
    assert "private@example.com" not in provider.prompt
    assert "Private Employer" not in provider.prompt
    assert "Private Test Candidate" not in provider.prompt


@pytest.mark.asyncio
async def test_invalid_or_unavailable_provider_does_not_create_fallback_roadmap(monkeypatch):
    unavailable = RoadmapProvider(available=False)
    monkeypatch.setattr(coach_service, "get_ai_provider", lambda: unavailable)
    profile = SimpleNamespace(
        current_role=None, target_role="HR Generalist", total_experience_months=0,
        key_skills=[], education_history=[],
    )

    with pytest.raises(HTTPException) as error:
        await coach_service.CoachService._generate_transition_steps(profile, "Human Resources")

    assert error.value.status_code == 503
    assert "AI roadmap generation is unavailable" in error.value.detail

    invalid = RoadmapProvider({"steps": []})
    monkeypatch.setattr(coach_service, "get_ai_provider", lambda: invalid)
    with pytest.raises(HTTPException) as error:
        await coach_service.CoachService._generate_transition_steps(profile, "Human Resources")
    assert error.value.status_code == 503
    assert "existing roadmap remains unchanged" in error.value.detail

    linked_steps = valid_steps()
    linked_steps["steps"][0]["description"] += " See https://example.com/course"
    monkeypatch.setattr(coach_service, "get_ai_provider", lambda: RoadmapProvider(linked_steps))
    with pytest.raises(HTTPException) as error:
        await coach_service.CoachService._generate_transition_steps(profile, "Human Resources")
    assert error.value.status_code == 503
    assert "existing roadmap remains unchanged" in error.value.detail


@pytest_asyncio.fixture
async def roadmap_profile_id():
    """Retained synthetic records, only in the guarded isolated pytest database."""
    suffix = uuid4().hex
    async with AsyncSessionLocal() as db:
        industry = Industry(name=f"zz_test_roadmap_{suffix}", slug=f"zz_test_roadmap_{suffix}")
        user = User(email=f"zz_test_roadmap_{suffix}@example.com", full_name="Synthetic roadmap candidate",
                    hashed_password="not-a-login-password")
        profile = CandidateProfile(
            user=user, industry=industry, current_role="Accountant", target_role="Product Manager",
            key_skills=["Spreadsheets"], total_experience_months=36,
            career_goals="Build a synthetic product portfolio",
            education_history=[Education(degree="BA", field_of_study="Economics", institution="Synthetic institution")],
            experience_history=[ProfessionalExperience(company_name="Synthetic company", job_title="Accountant",
                                                        description="Synthetic budgeting practice")],
        )
        db.add(profile)
        await db.commit()
        return profile.id


async def load_profile(db, profile_id):
    return await db.scalar(select(CandidateProfile).where(CandidateProfile.id == profile_id).options(
        selectinload(CandidateProfile.industry), selectinload(CandidateProfile.education_history),
        selectinload(CandidateProfile.experience_history),
    ))


async def add_module(db, profile, title, role=None, **kwargs):
    module = Module(
        industry_id=profile.industry_id, title=title, description="Synthetic published learning content",
        job_roles=[JobRole(industry_id=profile.industry_id, title=role)] if role else [],
        skills=kwargs.pop("skills", [Skill(name=f"zz_test_new_skill_{uuid4().hex}")]), **kwargs,
    )
    db.add(module)
    await db.commit()
    return module


@pytest.mark.parametrize("source,target,key", [
    ("Engineer", "HR", "engineer_to_hr"),
    ("  Software   Engineer ", "HR Generalist", "engineer_to_hr"),
    ("Mechanical Engineer", "Human Resources", "engineer_to_hr"),
    ("Engineer", "Marketing Specialist", "engineer_to_marketing"),
    ("Human Resources", "Data Scientist", "hr_to_data_science"),
    ("HR Generalist", "Data Science", "hr_to_data_science"),
    ("Teacher", "User Experience Designer", "teacher_to_ux_designer"),
    ("Educator", "UX Designer", "teacher_to_ux_designer"),
])
@pytest.mark.asyncio
async def test_curated_aliases_work_offline_with_general_modules_as_supplements(
    roadmap_profile_id, monkeypatch, source, target, key,
):
    monkeypatch.setattr(coach_service, "get_ai_provider", lambda: RoadmapProvider(available=False))
    async with AsyncSessionLocal() as db:
        profile = await load_profile(db, roadmap_profile_id)
        profile.current_role, profile.target_role = source, target
        general = await add_module(db, profile, "Supplemental general practice", skills=[])
        roadmap = await coach_service.CoachService.generate_personalized_roadmap(db, profile)
        entry = coach_service.CAREER_TRANSITION_KNOWLEDGE_BASE[key]
        assert [task.title for task in roadmap.tasks[:6]] == entry["modules_roadmap"]
        assert all(task.module_id is None for task in roadmap.tasks[:6])
        assert roadmap.tasks[6].module_id == general.id
        assert "curated" in roadmap.description.lower()
        assert "AI-generated" not in roadmap.description
        assert "not independently verified" in roadmap.description
        assert "not exhaustive" in roadmap.description
        repeated = await coach_service.CoachService.generate_personalized_roadmap(db, profile)
        assert repeated.id == roadmap.id


@pytest.mark.asyncio
async def test_curated_sync_helper_works_with_literal_transition_key_and_no_modules(roadmap_profile_id, monkeypatch):
    monkeypatch.setattr(coach_service, "get_ai_provider", lambda: RoadmapProvider(available=False))
    async with AsyncSessionLocal() as db:
        profile = await load_profile(db, roadmap_profile_id)
        profile.current_role, profile.target_role = "engineer", "hr"
        await db.commit()
        roadmap = await coach_service.CoachService.generate_personalized_roadmap(db, profile)
        assert len(roadmap.tasks) == 6
        assert roadmap.tasks[0].title == "Introduction to Human Resources"


@pytest.mark.parametrize("key", list(coach_service.CAREER_TRANSITION_KNOWLEDGE_BASE))
def test_curated_steps_use_real_topics_bridges_and_practical_deliverables(key):
    entry = coach_service.CAREER_TRANSITION_KNOWLEDGE_BASE[key]
    profile = SimpleNamespace(total_experience_months=48, current_role=entry["source_role"],
                              target_role=entry["target_role"], career_goals="Build a practical portfolio")
    steps = coach_service.CoachService._generate_knowledge_base_roadmap(entry, profile)
    assert [step.title for step in steps] == entry["modules_roadmap"]
    assert len(set(step.description for step in steps)) == 6
    text = " ".join(step.description for step in steps)
    assert all(bridge in text for bridge in entry["skill_bridges"])
    assert all(priority in text for priority in entry["learning_priorities"])
    assert all("Deliverable:" in step.description for step in steps)
    assert "General " not in text
    assert "jurisdiction" in text.lower()
    if key == "engineer_to_hr":
        assert "country/state" in text and "employment" in text.lower()
        assert "relevant authorities" in text


@pytest.mark.asyncio
async def test_target_tagged_modules_teach_new_skills_and_exclude_current_role(roadmap_profile_id, monkeypatch):
    monkeypatch.setattr(coach_service, "get_ai_provider", lambda: RoadmapProvider(available=False))
    async with AsyncSessionLocal() as db:
        profile = await load_profile(db, roadmap_profile_id)
        profile.current_role, profile.target_role = "Software Engineer", "HR Generalist"
        current = await add_module(db, profile, "Current-role engineering", "Software Engineer")
        general = await add_module(db, profile, "General supplement")
        target = await add_module(db, profile, "Learn new HR skills", "Human Resources")
        draft = await add_module(db, profile, "Draft HR", "HR", is_published=False)
        archived = await add_module(db, profile, "Archived HR", "HR", is_archived=True)
        foreign = await add_module(db, profile, "Marketing diversion", "Marketing")
        roadmap = await coach_service.CoachService.generate_personalized_roadmap(db, profile)
        assert [task.module_id for task in roadmap.tasks] == [target.id, general.id]
        assert all(task.module_id not in {current.id, draft.id, archived.id, foreign.id} for task in roadmap.tasks)
        assert "deterministic" in roadmap.description
        again = await coach_service.CoachService.generate_personalized_roadmap(db, profile)
        assert again.id == roadmap.id
        profile.career_goals = "Changed HR learning goal"
        await db.commit()
        changed = await coach_service.CoachService.generate_personalized_roadmap(db, profile)
        assert changed.id != roadmap.id


@pytest.mark.parametrize("source,target", [
    ("Prompt Engineer", "HR"), ("Teacher", "UX Researcher"), ("HR", "Data Analyst"),
])
@pytest.mark.asyncio
async def test_unlisted_roles_do_not_inherit_curated_family_coverage(roadmap_profile_id, monkeypatch, source, target):
    provider = RoadmapProvider(valid_steps())
    monkeypatch.setattr(coach_service, "get_ai_provider", lambda: provider)
    async with AsyncSessionLocal() as db:
        profile = await load_profile(db, roadmap_profile_id)
        profile.current_role, profile.target_role = source, target
        await db.commit()
        roadmap = await coach_service.CoachService.generate_personalized_roadmap(db, profile)
        assert provider.calls == 1
        assert "AI-generated six-step" in roadmap.description


@pytest.mark.parametrize("field", [
    "current_role", "target_role", "industry", "key_skills", "education", "experience",
    "total_experience_months", "relevant_experience_months", "career_goals",
])
@pytest.mark.asyncio
async def test_context_changes_regenerate_ai_plan_and_preserve_completed_history(roadmap_profile_id, monkeypatch, field):
    provider = RoadmapProvider(valid_steps())
    monkeypatch.setattr(coach_service, "get_ai_provider", lambda: provider)
    async with AsyncSessionLocal() as db:
        profile = await load_profile(db, roadmap_profile_id)
        roadmap = await coach_service.CoachService.generate_personalized_roadmap(db, profile)
        marker = re.search(r"\[generation-context:v1:[0-9a-f]{64}\]", roadmap.description)
        assert marker is not None
        saved = await db.scalar(select(Roadmap).where(Roadmap.id == roadmap.id).options(selectinload(Roadmap.tasks)))
        saved.tasks[0].is_completed = True
        await db.commit()
        reused = await coach_service.CoachService.generate_personalized_roadmap(db, profile)
        assert reused.id == roadmap.id and reused.tasks[0].is_completed
        assert provider.calls == 1
        if field == "industry":
            profile.industry = Industry(name=f"zz_test_other_{uuid4().hex}", slug=f"zz_test_other_{uuid4().hex}")
        elif field == "education":
            profile.education_history[0].field_of_study = "Business studies"
        elif field == "experience":
            profile.experience_history[0].description = "Changed synthetic experience"
        else:
            setattr(profile, field, {
                "current_role": "Financial Planner", "target_role": "Product Owner", "key_skills": ["Research"],
                "total_experience_months": 37, "relevant_experience_months": 12, "career_goals": "Lead discovery work",
            }[field])
        await db.commit()
        refreshed = await coach_service.CoachService.generate_personalized_roadmap(db, profile)
        assert refreshed.id != roadmap.id and provider.calls == 2
        assert marker.group() not in refreshed.description
        await db.refresh(saved, attribute_names=["status", "tasks"])
        assert saved.status == "superseded"
        assert saved.tasks[0].is_completed
        assert saved.tasks[0].id == roadmap.tasks[0].id


@pytest.mark.parametrize("failure", ["unavailable", "empty", "invalid", "duplicate", "exception"])
@pytest.mark.asyncio
async def test_failed_regeneration_keeps_old_plan_with_general_only_modules(roadmap_profile_id, monkeypatch, failure):
    provider = RoadmapProvider(valid_steps())
    monkeypatch.setattr(coach_service, "get_ai_provider", lambda: provider)
    async with AsyncSessionLocal() as db:
        profile = await load_profile(db, roadmap_profile_id)
        general = await add_module(db, profile, "General supplemental task")
        roadmap = await coach_service.CoachService.generate_personalized_roadmap(db, profile)
        assert provider.calls == 1
        assert len(roadmap.tasks) == 7 and roadmap.tasks[-1].module_id == general.id
        saved = await db.scalar(select(Roadmap).where(Roadmap.id == roadmap.id).options(selectinload(Roadmap.tasks)))
        saved.tasks[0].is_completed = True
        profile.career_goals = "Changed goal requiring regeneration"
        await db.commit()
        provider.available = failure != "unavailable"
        provider.data = None if failure == "empty" else {"steps": []} if failure == "invalid" else valid_steps()
        if failure == "duplicate":
            provider.data["steps"][1] = provider.data["steps"][0].copy()
        if failure == "exception":
            async def fail(*_args, **_kwargs):
                raise RuntimeError("Synthetic provider failure")
            monkeypatch.setattr(provider, "generate_structured", fail)
        with pytest.raises(HTTPException) as error:
            await coach_service.CoachService.generate_personalized_roadmap(db, profile)
        assert error.value.status_code == 503
        await db.rollback()
        old = await db.scalar(select(Roadmap).where(Roadmap.id == roadmap.id).options(selectinload(Roadmap.tasks)))
        assert old.status == "active" and old.tasks[0].is_completed
        assert [task.id for task in old.tasks] == [task.id for task in roadmap.tasks]
        active = (await db.scalars(select(Roadmap).where(
            Roadmap.candidate_profile_id == roadmap_profile_id, Roadmap.status == "active",
        ))).all()
        assert len(active) == 1


@pytest.mark.asyncio
async def test_legacy_description_without_fingerprint_is_not_reused(roadmap_profile_id, monkeypatch):
    provider = RoadmapProvider(valid_steps())
    monkeypatch.setattr(coach_service, "get_ai_provider", lambda: provider)
    async with AsyncSessionLocal() as db:
        profile = await load_profile(db, roadmap_profile_id)
        old = await coach_service.CoachService.generate_personalized_roadmap(db, profile)
        saved = await db.get(Roadmap, old.id)
        saved.description = "AI-generated six-step career-transition guidance from an older context."
        await db.commit()
        new = await coach_service.CoachService.generate_personalized_roadmap(db, profile)
        assert new.id != old.id and provider.calls == 2


@pytest.mark.asyncio
async def test_generation_reloads_profile_after_acquiring_row_lock(roadmap_profile_id, monkeypatch):
    monkeypatch.setattr(coach_service, "get_ai_provider", lambda: RoadmapProvider(available=False))
    async with AsyncSessionLocal() as stale_db, AsyncSessionLocal() as writer_db:
        stale = await load_profile(stale_db, roadmap_profile_id)
        changed = await load_profile(writer_db, roadmap_profile_id)
        changed.current_role, changed.target_role = "Engineer", "Human Resources"
        changed.career_goals = "Changed after the dependency loaded its profile"
        await writer_db.commit()
        roadmap = await coach_service.CoachService.generate_personalized_roadmap(stale_db, stale)
        assert roadmap.title == "Learning roadmap for Human Resources"
        assert roadmap.tasks[0].title == "Introduction to Human Resources"


@pytest.mark.asyncio
async def test_concurrent_generation_serializes_on_profile_and_reuses_one_active_plan(roadmap_profile_id, monkeypatch):
    entered, release, second_lock = asyncio.Event(), asyncio.Event(), asyncio.Event()

    class BlockingProvider(RoadmapProvider):
        async def generate_structured(self, *args, **kwargs):
            entered.set()
            await release.wait()
            return await super().generate_structured(*args, **kwargs)

    provider = BlockingProvider(valid_steps())
    monkeypatch.setattr(coach_service, "get_ai_provider", lambda: provider)
    lock_attempts = []

    def observe_lock(_conn, _cursor, statement, _parameters, _context, _executemany):
        if "candidate_profiles" in statement and "FOR UPDATE" in statement:
            lock_attempts.append(statement)
            if len(lock_attempts) == 2:
                second_lock.set()

    event.listen(async_engine.sync_engine, "before_cursor_execute", observe_lock)
    tasks = []
    try:
        async with AsyncSessionLocal() as first_db, AsyncSessionLocal() as second_db:
            first_profile = await load_profile(first_db, roadmap_profile_id)
            second_profile = await load_profile(second_db, roadmap_profile_id)
            tasks.append(asyncio.create_task(coach_service.CoachService.generate_personalized_roadmap(first_db, first_profile)))
            await asyncio.wait_for(entered.wait(), timeout=5)
            tasks.append(asyncio.create_task(coach_service.CoachService.generate_personalized_roadmap(second_db, second_profile)))
            try:
                await asyncio.wait_for(second_lock.wait(), timeout=5)
            finally:
                release.set()
                results = await asyncio.wait_for(asyncio.gather(*tasks), timeout=10)
            assert results[0].id == results[1].id and provider.calls == 1
            active = (await second_db.scalars(select(Roadmap).where(
                Roadmap.candidate_profile_id == roadmap_profile_id, Roadmap.status == "active",
            ))).all()
            assert len(active) == 1
    finally:
        release.set()
        event.remove(async_engine.sync_engine, "before_cursor_execute", observe_lock)
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
