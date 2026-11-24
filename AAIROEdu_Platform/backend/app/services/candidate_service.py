import uuid
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.candidate import CandidateProfile, CandidateTargetCompany, Company, Education, ProfessionalExperience
from app.models.taxonomy import Industry
from app.schemas.candidate import (
    CandidateProfileResponse, EducationCreate, EducationResponse,
    ExperienceCreate, ExperienceResponse, OnboardingStepRequest,
    TargetCompanyCreate, TargetCompanyResponse
)


class CandidateService:
    @staticmethod
    async def get_profile(db: AsyncSession, user_id: uuid.UUID) -> CandidateProfileResponse:
        query = (
            select(CandidateProfile)
            .where(CandidateProfile.user_id == user_id)
            .options(
                selectinload(CandidateProfile.industry).selectinload(Industry.categories),
                selectinload(CandidateProfile.industry).selectinload(Industry.job_roles),
                selectinload(CandidateProfile.education_history),
                selectinload(CandidateProfile.experience_history),
                selectinload(CandidateProfile.target_companies).selectinload(CandidateTargetCompany.company)
            )
        )
        result = await db.execute(query)
        profile = result.scalar_one_or_none()

        if not profile:
            profile = CandidateProfile(
                user_id=user_id,
                onboarding_completed=False,
                onboarding_step=1
            )
            db.add(profile)
            await db.commit()
            await db.refresh(profile)

        return CandidateProfileResponse.model_validate(profile)

    @staticmethod
    async def save_onboarding_step(
        db: AsyncSession,
        user_id: uuid.UUID,
        request: OnboardingStepRequest
    ) -> CandidateProfileResponse:
        query = (
            select(CandidateProfile)
            .where(CandidateProfile.user_id == user_id)
            .options(
                selectinload(CandidateProfile.education_history),
                selectinload(CandidateProfile.experience_history),
                selectinload(CandidateProfile.target_companies),
                selectinload(CandidateProfile.industry)
            )
        )
        result = await db.execute(query)
        profile = result.scalar_one_or_none()

        if not profile:
            profile = CandidateProfile(user_id=user_id)
            db.add(profile)

        # Update step
        profile.onboarding_step = max(profile.onboarding_step or 1, request.step)

        if request.candidate_type:
            profile.candidate_type = request.candidate_type
        if request.sub_category:
            profile.sub_category = request.sub_category
        if request.industry_id:
            profile.industry_id = request.industry_id
        if request.current_company is not None:
            profile.current_company = request.current_company
        if request.current_role is not None:
            profile.current_role = request.current_role
        if request.target_role is not None:
            profile.target_role = request.target_role
        if request.total_experience_months is not None:
            profile.total_experience_months = request.total_experience_months
        if request.relevant_experience_months is not None:
            profile.relevant_experience_months = request.relevant_experience_months
        if request.employment_status is not None:
            profile.employment_status = request.employment_status
        if request.key_skills is not None:
            profile.key_skills = request.key_skills
        if request.career_goals is not None:
            profile.career_goals = request.career_goals
        if request.interview_rounds_preferred is not None:
            profile.interview_rounds_preferred = request.interview_rounds_preferred
        if request.interaction_preference:
            profile.interaction_preference = request.interaction_preference

        # Handle Education records
        if request.education is not None:
            # Clear existing to avoid duplicate entries on re-run
            for old_edu in list(profile.education_history):
                await db.delete(old_edu)
            for edu_in in request.education:
                profile.education_history.append(
                    Education(
                        degree=edu_in.degree,
                        field_of_study=edu_in.field_of_study,
                        institution=edu_in.institution,
                        start_year=edu_in.start_year,
                        end_year=edu_in.end_year,
                        grade=edu_in.grade,
                        is_current=edu_in.is_current
                    )
                )

        # Handle Experience records
        if request.experience is not None:
            for old_exp in list(profile.experience_history):
                await db.delete(old_exp)
            for exp_in in request.experience:
                profile.experience_history.append(
                    ProfessionalExperience(
                        company_name=exp_in.company_name,
                        job_title=exp_in.job_title,
                        start_date=exp_in.start_date,
                        end_date=exp_in.end_date,
                        is_current=exp_in.is_current,
                        description=exp_in.description
                    )
                )

        # Handle Target Companies
        if request.target_companies is not None:
            for old_tc in list(profile.target_companies):
                await db.delete(old_tc)
            for tc_in in request.target_companies:
                # Find or create company
                comp_query = select(Company).where(Company.name == tc_in.company_name.strip())
                comp_res = await db.execute(comp_query)
                company = comp_res.scalar_one_or_none()
                if not company:
                    company = Company(name=tc_in.company_name.strip())
                    db.add(company)
                    await db.flush()

                profile.target_companies.append(
                    CandidateTargetCompany(
                        company_id=company.id,
                        target_role=tc_in.target_role or profile.target_role
                    )
                )

        if request.is_final_step or request.step >= 7:
            profile.onboarding_completed = True
            profile.onboarding_step = 7
            # Initial baseline readiness calculation
            profile.interview_readiness_score = CandidateService.calculate_readiness_score(profile)

        await db.commit()
        return await CandidateService.get_profile(db, user_id)

    @staticmethod
    def calculate_readiness_score(profile: CandidateProfile) -> float:
        """
        Explainable formula:
        - Profile completeness (Industry, target role, education, skills): 30%
        - Target companies defined: 10%
        - Interview preferences set: 10%
        - Baseline: 50% on complete onboarding
        """
        score = 0.0
        if profile.industry_id:
            score += 15.0
        if profile.target_role:
            score += 15.0
        if profile.key_skills and len(profile.key_skills) > 0:
            score += min(len(profile.key_skills) * 3.0, 15.0)
        if profile.education_history:
            score += 10.0
        if profile.interview_rounds_preferred:
            score += 10.0
        if profile.target_companies:
            score += 10.0
        return min(round(score, 1), 75.0)
