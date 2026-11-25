import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple
from fastapi import HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import String, and_, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import async_engine

from app.integrations.ai.base import AIResponse
from app.integrations.ai.prompt_manager import PromptManager
from app.integrations.ai.provider_factory import get_ai_provider
from app.models.assessment import Assessment, AssessmentAttempt, AssessmentQuestion, AttemptStatus
from app.models.candidate import CandidateProfile, Company
from app.models.question import (
    ApprovalStatus, DifficultyLevel, Question,
    QuestionBookmark, QuestionPracticeLog, QuestionType, SourceProvenance
)
from app.schemas.question import (
    CandidateQuestionResponse, ManagedQuestionResponse, PracticeHistoryItem,
    QuestionCreate, QuestionPracticeRequest, QuestionPracticeResponse,
    QuestionResponse, QuestionUpdate
)
from app.models.taxonomy import (ExperienceLevel, Industry, IndustryCategory,
    InterviewRound, JobRole, Skill, Subject, Topic)
from app.models.user import User


class PracticeEvaluationOutput(BaseModel):
    score_awarded: float = Field(ge=0, le=100)
    detailed_feedback: str = Field(min_length=1, max_length=4000)


class QuestionDraftOutput(BaseModel):
    question_text: str = Field(min_length=10, max_length=10000)
    expected_answer: str = Field(min_length=1, max_length=20000)
    explanation: Optional[str] = Field(default=None, max_length=10000)
    options: List[Dict[str, Any]] = Field(default_factory=list)
    evaluation_rubric: Dict[str, Any] = Field(default_factory=dict)


class QuestionService:
    @staticmethod
    async def generate_question_draft(db: AsyncSession, brief, actor_id: uuid.UUID) -> ManagedQuestionResponse:
        provider = get_ai_provider()
        if not provider.is_available():
            raise HTTPException(status_code=503, detail="AI question drafting is unavailable because no AI provider is configured")
        role_ids = list(dict.fromkeys(brief.job_role_ids + ([brief.job_role_id] if brief.job_role_id else [])))
        roles, skills, companies = await QuestionService._validate_question_links(
            db, brief.industry_id, brief.industry_category_id, brief.subject_id, brief.topic_id,
            role_ids, brief.skill_ids, brief.company_ids, brief.experience_level_id, brief.interview_round_id,
        )
        industry = await db.get(Industry, brief.industry_id)
        prompt_brief = {
            "industry": {"id": str(industry.id), "name": industry.name},
            "roles": [{"id": str(role.id), "title": role.title} for role in roles],
            "skills": [{"id": str(skill.id), "name": skill.name, "category": skill.category} for skill in skills],
            "companies": [{"id": str(company.id), "name": company.name} for company in companies],
            "industry_category_id": str(brief.industry_category_id) if brief.industry_category_id else None,
            "subject": brief.subject, "topic": brief.topic,
            "subject_id": str(brief.subject_id) if brief.subject_id else None,
            "topic_id": str(brief.topic_id) if brief.topic_id else None,
            "experience_level": brief.experience_level,
            "question_type": brief.question_type.value, "difficulty": brief.difficulty.value,
            "interview_round": brief.interview_round,
        }
        prompt = PromptManager.get_question_draft_prompt(prompt_brief)
        try:
            result = await provider.generate_structured(prompt, QuestionDraftOutput)
            if not result.is_success:
                raise HTTPException(status_code=502, detail="AI provider request failed or timed out; no question was saved")
            if not result.structured_data:
                raise ValueError("Provider returned no structured draft")
            draft = QuestionDraftOutput.model_validate(result.structured_data)
            candidate_input = brief.model_dump(mode="json")
            candidate_input.update(draft.model_dump())
            candidate_input["source_provenance"] = SourceProvenance.AI_GENERATED
            candidate_input["approval_status"] = ApprovalStatus.PENDING
            candidate_input["job_role_ids"] = list(dict.fromkeys(brief.job_role_ids + ([brief.job_role_id] if brief.job_role_id else [])))
            candidate_input["job_role_id"] = brief.job_role_id
            validated = QuestionCreate.model_validate(candidate_input)
        except HTTPException:
            raise
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("AI question draft unavailable (%s)", type(exc).__name__)
            raise HTTPException(status_code=502, detail="AI provider did not return a valid question draft; no question was saved") from exc
        normalized_text = validated.question_text.strip().casefold()
        duplicate_id = await db.scalar(select(Question.id).where(
            Question.industry_id == validated.industry_id,
            Question.is_archived.is_(False),
            func.lower(func.trim(Question.question_text)) == normalized_text,
        ).limit(1))
        if duplicate_id:
            raise HTTPException(status_code=409, detail="A question with this text already exists in the selected industry; no question was saved")
        return await QuestionService.create_question(db, validated, actor_id)

    @staticmethod
    def _public_content_filter():
        if async_engine.dialect.name == "sqlite":
            return or_(Question.tags.is_(None), ~cast(Question.tags, String).contains('"assessment_only"'))
        return ~Question.tags.contains(["assessment_only"])

    @staticmethod
    def _reject_private_question(question: Optional[Question]) -> None:
        if question and "assessment_only" in (question.tags or []):
            raise HTTPException(status_code=404, detail="Question not found")

    @staticmethod
    def _load_options():
        return (
            selectinload(Question.industry), selectinload(Question.job_role),
            selectinload(Question.job_roles), selectinload(Question.industry_category),
            selectinload(Question.subject_taxonomy), selectinload(Question.topic_taxonomy),
            selectinload(Question.skills), selectinload(Question.companies),
        )

    @staticmethod
    def _candidate_response(question: Question, is_bookmarked: bool = False) -> CandidateQuestionResponse:
        return CandidateQuestionResponse(
            id=question.id, question_text=question.question_text, question_type=question.question_type,
            industry_id=question.industry_id, job_role_id=question.job_role_id,
            job_role_ids=[role.id for role in question.job_roles], skill_ids=[skill.id for skill in question.skills],
            company_ids=[company.id for company in question.companies], industry_category_id=question.industry_category_id,
            subject_id=question.subject_id, topic_id=question.topic_id, subject=question.subject, topic=question.topic,
            experience_level=question.experience_level, experience_level_id=question.experience_level_id,
            interview_round=question.interview_round, interview_round_id=question.interview_round_id,
            difficulty=question.difficulty, options=[{key: value for key, value in option.items() if key != "is_correct"} for option in question.options],
            source_provenance=question.source_provenance, marks=question.marks, estimated_minutes=question.estimated_minutes,
            is_bookmarked=is_bookmarked, industry=question.industry, job_roles=question.job_roles,
            skills=question.skills, companies=question.companies, created_at=question.created_at, updated_at=question.updated_at,
        )

    @staticmethod
    async def manage_questions(db: AsyncSession, page: int = 1, limit: int = 20,
            workflow_status: Optional[str] = None, provenance: Optional[SourceProvenance] = None,
            industry_id: Optional[uuid.UUID] = None, search: Optional[str] = None,
            sort_by: str = "updated_at", sort_order: str = "desc") -> Tuple[List[ManagedQuestionResponse], int]:
        filters = [QuestionService._public_content_filter()]
        if workflow_status: filters.append(Question.workflow_status == workflow_status)
        if provenance: filters.append(Question.source_provenance == provenance)
        if industry_id: filters.append(Question.industry_id == industry_id)
        if search:
            term = f"%{search.strip()}%"
            filters.append(or_(Question.question_text.ilike(term), Question.subject.ilike(term), Question.topic.ilike(term)))
        total = await db.scalar(select(func.count(Question.id)).where(*filters)) or 0
        sort_fields = {"updated_at": Question.updated_at, "created_at": Question.created_at, "difficulty": Question.difficulty, "subject": Question.subject, "topic": Question.topic, "workflow_status": Question.workflow_status}
        order = sort_fields[sort_by].desc() if sort_order == "desc" else sort_fields[sort_by].asc()
        rows = await db.scalars(select(Question).where(*filters).options(*QuestionService._load_options()).order_by(order, Question.id).offset((page-1)*limit).limit(limit))
        return [ManagedQuestionResponse.model_validate(row) for row in rows.all()], total

    @staticmethod
    async def list_questions(
        db: AsyncSession,
        candidate_profile_id: Optional[uuid.UUID] = None,
        industry_id: Optional[uuid.UUID] = None,
        job_role_id: Optional[uuid.UUID] = None,
        difficulty: Optional[DifficultyLevel] = None,
        question_type: Optional[QuestionType] = None,
        interview_round: Optional[str] = None,
        industry_category_id: Optional[uuid.UUID] = None,
        skill_id: Optional[uuid.UUID] = None,
        subject_id: Optional[uuid.UUID] = None,
        topic_id: Optional[uuid.UUID] = None,
        experience_level_id: Optional[uuid.UUID] = None,
        company_id: Optional[uuid.UUID] = None,
        bookmarked: Optional[bool] = None,
        search: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> Tuple[List[CandidateQuestionResponse], int]:
        filters = [Question.workflow_status == "published", Question.is_archived.is_(False),
                   QuestionService._public_content_filter()]

        if industry_id:
            filters.append(Question.industry_id == industry_id)
        if job_role_id:
            filters.append(or_(Question.job_role_id == job_role_id, Question.job_roles.any(JobRole.id == job_role_id)))
        if difficulty:
            filters.append(Question.difficulty == difficulty)
        if question_type:
            filters.append(Question.question_type == question_type)
        if interview_round:
            filters.append(Question.interview_round == interview_round)
        if industry_category_id: filters.append(Question.industry_category_id == industry_category_id)
        if skill_id: filters.append(Question.skills.any(Skill.id == skill_id))
        if subject_id: filters.append(Question.subject_id == subject_id)
        if topic_id: filters.append(Question.topic_id == topic_id)
        if experience_level_id: filters.append(Question.experience_level_id == experience_level_id)
        if company_id: filters.append(Question.companies.any(Company.id == company_id))
        if bookmarked is not None:
            bookmark_filter = Question.bookmarks.any(and_(QuestionBookmark.candidate_profile_id == candidate_profile_id))
            filters.append(bookmark_filter if bookmarked else ~bookmark_filter)
        if search:
            search_term = f"%{search.strip()}%"
            filters.append(
                or_(
                    Question.question_text.ilike(search_term),
                    Question.subject.ilike(search_term),
                    Question.topic.ilike(search_term)
                )
            )

        # Count query
        count_q = select(func.count(Question.id)).where(and_(*filters))
        total_res = await db.execute(count_q)
        total = total_res.scalar_one()

        # Data query
        offset = (page - 1) * limit
        sort_fields = {"created_at": Question.created_at, "updated_at": Question.updated_at,
            "difficulty": Question.difficulty, "subject": Question.subject, "topic": Question.topic,
            "interview_round": Question.interview_round, "question_type": Question.question_type}
        query = (
            select(Question)
            .where(and_(*filters))
            .options(*QuestionService._load_options())
            .order_by((sort_fields[sort_by].desc() if sort_order == "desc" else sort_fields[sort_by].asc()), Question.id)
            .offset(offset)
            .limit(limit)
        )
        result = await db.execute(query)
        questions = result.scalars().all()

        # Check candidate bookmarks if profile provided
        bookmarked_ids = set()
        if candidate_profile_id:
            b_q = select(QuestionBookmark.question_id).where(
                QuestionBookmark.candidate_profile_id == candidate_profile_id
            )
            b_res = await db.execute(b_q)
            bookmarked_ids = set(b_res.scalars().all())

        output: List[CandidateQuestionResponse] = []
        for q in questions:
            output.append(QuestionService._candidate_response(q, q.id in bookmarked_ids))

        return output, total

    @staticmethod
    async def get_question(
        db: AsyncSession,
        question_id: uuid.UUID,
        candidate_profile_id: Optional[uuid.UUID] = None
    ) -> CandidateQuestionResponse:
        query = (
            select(Question)
            .where(Question.id == question_id, Question.workflow_status == "published", Question.is_archived.is_(False),
                   QuestionService._public_content_filter())
            .options(*QuestionService._load_options())
        )
        result = await db.execute(query)
        q = result.scalar_one_or_none()

        if not q:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Question not found"
            )

        is_bm = False
        if candidate_profile_id:
            b_q = select(QuestionBookmark).where(
                QuestionBookmark.candidate_profile_id == candidate_profile_id,
                QuestionBookmark.question_id == question_id
            )
            b_res = await db.execute(b_q)
            is_bm = b_res.scalar_one_or_none() is not None

        return QuestionService._candidate_response(q, is_bm)

    @staticmethod
    async def toggle_bookmark(
        db: AsyncSession,
        question_id: uuid.UUID,
        candidate_profile_id: uuid.UUID
    ) -> bool:
        question = await db.scalar(select(Question.id).where(
            Question.id == question_id,
            Question.workflow_status == "published",
            Question.is_archived.is_(False),
            QuestionService._public_content_filter(),
        ))
        if not question:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
        query = select(QuestionBookmark).where(
            QuestionBookmark.candidate_profile_id == candidate_profile_id,
            QuestionBookmark.question_id == question_id
        )
        res = await db.execute(query)
        existing = res.scalar_one_or_none()

        if existing:
            await db.delete(existing)
            await db.commit()
            return False
        else:
            bm = QuestionBookmark(
                candidate_profile_id=candidate_profile_id,
                question_id=question_id
            )
            db.add(bm)
            await db.commit()
            return True

    @staticmethod
    async def get_practice_history(db: AsyncSession, candidate_profile_id: uuid.UUID, page: int = 1, limit: int = 20):
        base = select(QuestionPracticeLog).join(Question, Question.id == QuestionPracticeLog.question_id).where(
            QuestionPracticeLog.candidate_profile_id == candidate_profile_id)
        total = await db.scalar(select(func.count(QuestionPracticeLog.id)).join(Question, Question.id == QuestionPracticeLog.question_id).where(
            QuestionPracticeLog.candidate_profile_id == candidate_profile_id)) or 0
        rows = await db.scalars(base.options(selectinload(QuestionPracticeLog.question))
            .order_by(QuestionPracticeLog.created_at.desc()).offset((page-1)*limit).limit(limit))
        return [PracticeHistoryItem(id=row.id, question_id=row.question_id,
            question_text=row.question.question_text, question_type=row.question.question_type,
            user_response=row.user_response, is_correct=row.is_correct, score_percentage=row.score_percentage,
            evaluation_status=row.evaluation_status, evaluation_provenance=row.evaluation_provenance,
            feedback=row.ai_feedback, created_at=row.created_at) for row in rows.all()], total

    @staticmethod
    async def practice_question(
        db: AsyncSession,
        question_id: uuid.UUID,
        candidate_profile_id: uuid.UUID,
        request: QuestionPracticeRequest
    ) -> QuestionPracticeResponse:
        q_result = await db.execute(select(Question).where(
            Question.id == question_id,
            Question.workflow_status == "published",
            Question.is_archived.is_(False),
            QuestionService._public_content_filter(),
        ))
        q = q_result.scalar_one_or_none()
        if not q:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Question not found"
            )

        # The standalone practice API reveals keys; active session answers must
        # instead be saved through the candidate-owned assessment attempt.
        active_attempt = await db.scalar(
            select(AssessmentAttempt.id)
            .join(Assessment, Assessment.id == AssessmentAttempt.assessment_id)
            .join(AssessmentQuestion, AssessmentQuestion.assessment_id == Assessment.id)
            .where(
                AssessmentAttempt.candidate_profile_id == candidate_profile_id,
                AssessmentAttempt.status == AttemptStatus.IN_PROGRESS,
                AssessmentQuestion.question_id == question_id,
                AssessmentAttempt.started_at + Assessment.duration_minutes * timedelta(minutes=1)
                > datetime.now(timezone.utc),
            ).limit(1)
        )
        if active_attempt:
            raise HTTPException(status_code=409, detail="Save this answer through your active assessment session")

        user_answer = request.user_response.strip()
        if not user_answer:
            raise HTTPException(status_code=422, detail="Answer cannot contain only whitespace")
        is_correct = False
        score_percentage = 0.0
        feedback = ""
        evaluation_status = "evaluated"
        evaluation_provenance = "deterministic"

        # MCQ evaluation (Deterministic)
        if q.question_type in (QuestionType.MCQ_SINGLE, QuestionType.MCQ_MULTIPLE):
            correct_opts = [opt["id"].strip().upper() for opt in q.options if opt.get("is_correct")]
            user_opts = [u.strip().upper() for u in user_answer.split(",") if u.strip()]
            valid_opts = {opt["id"].strip().upper() for opt in q.options}
            if not user_opts or len(set(user_opts)) != len(user_opts) or any(option not in valid_opts for option in user_opts):
                raise HTTPException(status_code=422, detail="Select valid option IDs once each")
            if q.question_type == QuestionType.MCQ_SINGLE and len(user_opts) != 1:
                raise HTTPException(status_code=422, detail="Single-choice questions require exactly one option")
            if sorted(correct_opts) == sorted(user_opts):
                is_correct = True
                score_percentage = 100.0
                feedback = f"Excellent! Your choice ({', '.join(user_opts)}) matches the correct answer."
            else:
                is_correct = False
                score_percentage = 0.0
                feedback = f"Incorrect. Correct answer is: {', '.join(correct_opts)}."

        else:
            # Descriptive / Behavioral / Coding answers are never scored without valid AI output.
            ai_provider = get_ai_provider()
            if ai_provider.is_available():
                try:
                    prompt = PromptManager.get_descriptive_eval_prompt(
                        question=q.question_text,
                        expected_answer=q.expected_answer or "",
                        candidate_answer=user_answer,
                        rubric=q.evaluation_rubric
                    )
                    ai_res = await ai_provider.generate_text(prompt=prompt)
                    if ai_res.is_success and ai_res.raw_text:
                        from app.integrations.ai.response_validator import ResponseValidator
                        output, validation_error = ResponseValidator.validate_pydantic(ai_res.raw_text, PracticeEvaluationOutput)
                        if output and not validation_error:
                            score_percentage = output.score_awarded
                            is_correct = output.score_awarded >= 60.0
                            feedback = output.detailed_feedback.strip()
                            evaluation_provenance = "ai"
                except Exception as error:
                    import logging
                    logging.getLogger(__name__).warning("Question evaluation unavailable (%s)", type(error).__name__)

            if not feedback:
                score_percentage = None
                is_correct = None
                evaluation_status = "unavailable"
                evaluation_provenance = "none"
                feedback = "AI evaluation is unavailable or returned an invalid result. Your answer was saved without a score."

        # Record practice log
        log = QuestionPracticeLog(
            candidate_profile_id=candidate_profile_id,
            question_id=question_id,
            user_response=user_answer,
            is_correct=is_correct,
            score_percentage=score_percentage,
            ai_feedback=feedback,
            evaluation_status=evaluation_status,
            evaluation_provenance=evaluation_provenance,
        )
        db.add(log)
        await db.commit()

        return QuestionPracticeResponse(
            question_id=question_id,
            is_correct=is_correct,
            score_percentage=score_percentage,
            evaluation_status=evaluation_status,
            evaluation_provenance=evaluation_provenance,
            expected_answer=q.expected_answer,
            explanation=q.explanation,
            feedback=feedback
        )

    @staticmethod
    async def _validate_question_links(db: AsyncSession, industry_id: uuid.UUID, category_id, subject_id, topic_id,
            role_ids: List[uuid.UUID], skill_ids: List[uuid.UUID], company_ids: List[uuid.UUID], experience_id, round_id):
        industry = await db.get(Industry, industry_id)
        if not industry or not industry.is_active:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="An active industry is required")
        category = await db.get(IndustryCategory, category_id) if category_id else None
        if category_id and (not category or not category.is_active or category.industry_id != industry_id):
            raise HTTPException(status_code=422, detail="Category must belong to the selected active industry")
        subject = await db.get(Subject, subject_id) if subject_id else None
        if subject_id and (not subject or not subject.is_active or subject.industry_id != industry_id):
            raise HTTPException(status_code=422, detail="Subject must belong to the selected active industry")
        topic = await db.get(Topic, topic_id) if topic_id else None
        if topic_id and (not topic or not topic.is_active or not subject or topic.subject_id != subject.id):
            raise HTTPException(status_code=422, detail="Topic must belong to the selected subject")
        roles = list((await db.scalars(select(JobRole).where(JobRole.id.in_(role_ids)))).all()) if role_ids else []
        if len(roles) != len(set(role_ids)) or any(not role.is_active or role.industry_id != industry_id for role in roles):
            raise HTTPException(status_code=422, detail="Every job role must belong to the selected active industry")
        skills = list((await db.scalars(select(Skill).where(Skill.id.in_(skill_ids)))).all()) if skill_ids else []
        if len(skills) != len(set(skill_ids)) or any(not skill.is_active for skill in skills):
            raise HTTPException(status_code=422, detail="Skills must exist and be active")
        companies = list((await db.scalars(select(Company).where(Company.id.in_(company_ids)))).all()) if company_ids else []
        if len(companies) != len(set(company_ids)) or any(not company.is_active or (company.industry and company.industry.casefold() != industry.name.casefold()) for company in companies):
            raise HTTPException(status_code=422, detail="Companies must be active and match the selected industry when industry-scoped")
        experience = await db.get(ExperienceLevel, experience_id) if experience_id else None
        if experience_id and (not experience or not experience.is_active):
            raise HTTPException(status_code=422, detail="Experience level must be active")
        round_taxonomy = await db.get(InterviewRound, round_id) if round_id else None
        if round_id and (not round_taxonomy or not round_taxonomy.is_active or round_taxonomy.industry_id != industry_id):
            raise HTTPException(status_code=422, detail="Interview round must belong to the selected active industry")
        return roles, skills, companies

    @staticmethod
    async def create_question(db: AsyncSession, request: QuestionCreate, actor_id: uuid.UUID) -> ManagedQuestionResponse:
        role_ids = list(dict.fromkeys(request.job_role_ids + ([request.job_role_id] if request.job_role_id else [])))
        roles, skills, companies = await QuestionService._validate_question_links(db, request.industry_id,
            request.industry_category_id, request.subject_id, request.topic_id, role_ids,
            request.skill_ids, request.company_ids, request.experience_level_id, request.interview_round_id)
        if request.subject_id:
            subject = await db.get(Subject, request.subject_id)
            if subject.name != request.subject:
                raise HTTPException(status_code=422, detail="Subject label must match the selected subject")
        if request.topic_id:
            topic = await db.get(Topic, request.topic_id)
            if topic.name != request.topic:
                raise HTTPException(status_code=422, detail="Topic label must match the selected topic")
        if request.interview_round_id:
            interview_round = await db.get(InterviewRound, request.interview_round_id)
            if interview_round.name != request.interview_round:
                raise HTTPException(status_code=422, detail="Interview round label must match the selected round")
        new_q = Question(
            question_text=request.question_text, question_type=request.question_type, industry_id=request.industry_id,
            industry_category_id=request.industry_category_id, job_role_id=role_ids[0] if len(role_ids) == 1 else None,
            job_roles=roles, skills=skills, companies=companies, subject=request.subject, topic=request.topic,
            subject_id=request.subject_id, topic_id=request.topic_id, experience_level=request.experience_level,
            experience_level_id=request.experience_level_id, interview_round_id=request.interview_round_id,
            difficulty=request.difficulty, interview_round=request.interview_round, options=[opt.model_dump() for opt in request.options],
            expected_answer=request.expected_answer, explanation=request.explanation,
            evaluation_rubric=request.evaluation_rubric, tags=request.tags, source_provenance=request.source_provenance,
            source_url=request.source_url, marks=request.marks, estimated_minutes=request.estimated_minutes,
            approval_status=ApprovalStatus.PENDING, workflow_status=request.workflow_status, version_number=1,
            created_by_id=actor_id,
        )
        db.add(new_q)
        await db.flush()
        new_q.root_question_id = new_q.id
        await db.commit()
        loaded = await db.scalar(select(Question).where(Question.id == new_q.id).options(*QuestionService._load_options()))
        return ManagedQuestionResponse.model_validate(loaded)

    @staticmethod
    async def submit_question_for_review(db: AsyncSession, question_id: uuid.UUID) -> ManagedQuestionResponse:
        question = await db.scalar(select(Question).where(Question.id == question_id).with_for_update())
        QuestionService._reject_private_question(question)
        if not question or question.is_archived or question.workflow_status != "draft":
            raise HTTPException(status_code=404, detail="Draft question not found")
        question.workflow_status = "pending_review"
        question.approval_status = ApprovalStatus.PENDING
        await db.commit()
        loaded = await db.scalar(select(Question).where(Question.id == question.id).options(*QuestionService._load_options()))
        return ManagedQuestionResponse.model_validate(loaded)

    @staticmethod
    async def update_question(db: AsyncSession, question_id: uuid.UUID, request: QuestionUpdate, actor_id: uuid.UUID) -> ManagedQuestionResponse:
        question = await db.scalar(select(Question).where(Question.id == question_id).options(*QuestionService._load_options()))
        QuestionService._reject_private_question(question)
        if not question or question.is_archived or question.workflow_status in {"archived", "superseded"}:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
        changes = request.model_dump(exclude_unset=True, exclude={"approval_status", "job_role_ids", "skill_ids", "company_ids"})
        if request.options is not None:
            changes["options"] = [option.model_dump() if hasattr(option, "model_dump") else option for option in request.options]
        role_ids = request.job_role_ids if request.job_role_ids is not None else [role.id for role in question.job_roles]
        if request.job_role_ids is None and not role_ids and question.job_role_id:
            role_ids = [question.job_role_id]
        skill_ids = request.skill_ids if request.skill_ids is not None else [skill.id for skill in question.skills]
        company_ids = request.company_ids if request.company_ids is not None else [company.id for company in question.companies]
        industry_id = changes.get("industry_id", question.industry_id)
        category_id = changes.get("industry_category_id", question.industry_category_id)
        subject_id = changes.get("subject_id", question.subject_id)
        topic_id = changes.get("topic_id", question.topic_id)
        roles, skills, companies = await QuestionService._validate_question_links(db, industry_id, category_id,
            subject_id, topic_id, role_ids, skill_ids, company_ids,
            changes.get("experience_level_id", question.experience_level_id),
            changes.get("interview_round_id", question.interview_round_id))
        subject_label = changes.get("subject", question.subject)
        topic_label = changes.get("topic", question.topic)
        if subject_id:
            subject = await db.get(Subject, subject_id)
            if subject.name != subject_label:
                raise HTTPException(status_code=422, detail="Subject label must match the selected subject")
        if topic_id:
            topic = await db.get(Topic, topic_id)
            if topic.name != topic_label:
                raise HTTPException(status_code=422, detail="Topic label must match the selected topic")
        round_id = changes.get("interview_round_id", question.interview_round_id)
        if round_id:
            selected_round = await db.get(InterviewRound, round_id)
            round_label = changes.get("interview_round", question.interview_round)
            if selected_round.name != round_label:
                raise HTTPException(status_code=422, detail="Interview round label must match the selected round")
        if question.workflow_status == "published":
            values = {name: getattr(question, name) for name in (
                "question_text", "question_type", "industry_id", "industry_category_id", "subject_id", "topic_id",
                "experience_level", "experience_level_id", "interview_round_id", "subject", "topic", "difficulty",
                "interview_round", "options", "expected_answer", "explanation", "evaluation_rubric", "tags",
                "source_provenance", "source_url", "marks", "estimated_minutes")}
            question = Question(**values, job_role_id=question.job_role_id, job_roles=list(roles), skills=list(skills),
                companies=list(companies), workflow_status="pending_review", approval_status=ApprovalStatus.PENDING,
                version_number=question.version_number + 1, root_question_id=question.root_question_id or question.id,
                created_by_id=actor_id)
            db.add(question)
        for key, value in changes.items():
            setattr(question, key, value)
        question.job_roles = roles
        question.skills = skills
        question.companies = companies
        question.job_role_id = roles[0].id if len(roles) == 1 else None
        question.approval_status = ApprovalStatus.PENDING
        question.workflow_status = "pending_review"
        question.reviewed_by_id = None
        question.reviewed_at = None
        question.review_comment = None
        question.published_at = None
        question.created_by_id = actor_id
        await db.commit()
        loaded = await db.scalar(select(Question).where(Question.id == question.id).options(*QuestionService._load_options()))
        return ManagedQuestionResponse.model_validate(loaded)

    @staticmethod
    async def decide_question(db: AsyncSession, question_id: uuid.UUID, decision: ApprovalStatus, actor_id: uuid.UUID, comment: Optional[str] = None) -> ManagedQuestionResponse:
        if decision not in (ApprovalStatus.APPROVED, ApprovalStatus.REJECTED):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Review decision must be approved or rejected")
        question = await db.get(Question, question_id)
        QuestionService._reject_private_question(question)
        if not question or question.is_archived or question.workflow_status not in {"pending_review", "draft"}:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
        question.approval_status = decision
        question.workflow_status = "approved" if decision == ApprovalStatus.APPROVED else "rejected"
        question.reviewed_by_id = actor_id
        question.reviewed_at = datetime.now(timezone.utc)
        question.review_comment = comment
        await db.commit()
        loaded = await db.scalar(select(Question).where(Question.id == question.id).options(*QuestionService._load_options()))
        return ManagedQuestionResponse.model_validate(loaded)

    @staticmethod
    async def publish_question(db: AsyncSession, question_id: uuid.UUID) -> ManagedQuestionResponse:
        question = await db.scalar(select(Question).where(Question.id == question_id).with_for_update())
        QuestionService._reject_private_question(question)
        if not question or question.is_archived:
            raise HTTPException(status_code=404, detail="Question not found")
        if question.workflow_status != "approved":
            raise HTTPException(status_code=409, detail="Only approved content can be published")
        root_id = question.root_question_id or question.id
        await db.execute(Question.__table__.update().where(Question.root_question_id == root_id,
            Question.workflow_status == "published", Question.id != question.id).values(workflow_status="superseded"))
        question.workflow_status = "published"
        question.approval_status = ApprovalStatus.APPROVED
        question.published_at = datetime.now(timezone.utc)
        await db.commit()
        loaded = await db.scalar(select(Question).where(Question.id == question.id).options(*QuestionService._load_options()))
        return ManagedQuestionResponse.model_validate(loaded)

    @staticmethod
    async def get_question_versions(db: AsyncSession, question_id: uuid.UUID) -> List[ManagedQuestionResponse]:
        question = await db.get(Question, question_id)
        QuestionService._reject_private_question(question)
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")
        root_id = question.root_question_id or question.id
        rows = await db.scalars(select(Question).where(Question.root_question_id == root_id,
            QuestionService._public_content_filter())
            .options(*QuestionService._load_options()).order_by(Question.version_number.desc()))
        return [ManagedQuestionResponse.model_validate(row) for row in rows.all()]

    @staticmethod
    async def restore_question_version(db: AsyncSession, question_id: uuid.UUID, source_version_id: uuid.UUID, actor_id: uuid.UUID) -> ManagedQuestionResponse:
        versions = await QuestionService.get_question_versions(db, question_id)
        source = next((v for v in versions if v.id == source_version_id), None)
        if source is None:
            raise HTTPException(status_code=404, detail="Question version not found")
        root_id = source.root_question_id or source.id
        version_number = max(row.version_number for row in versions) + 1
        original = await db.scalar(select(Question).where(Question.id == source_version_id).options(*QuestionService._load_options()))
        QuestionService._reject_private_question(original)
        restored = Question(**{name: getattr(original, name) for name in (
            "question_text", "question_type", "industry_id", "industry_category_id", "subject_id", "topic_id",
            "experience_level", "experience_level_id", "interview_round_id", "subject", "topic", "difficulty",
            "interview_round", "options", "expected_answer", "explanation", "evaluation_rubric", "tags",
            "source_provenance", "source_url", "marks", "estimated_minutes")}, job_role_id=original.job_role_id,
            job_roles=list(original.job_roles), skills=list(original.skills), companies=list(original.companies),
            workflow_status="pending_review", approval_status=ApprovalStatus.PENDING, root_question_id=root_id,
            version_number=version_number, created_by_id=actor_id)
        db.add(restored)
        await db.flush()
        restored.root_question_id = root_id
        await db.commit()
        loaded = await db.scalar(select(Question).where(Question.id == restored.id).options(*QuestionService._load_options()))
        return ManagedQuestionResponse.model_validate(loaded)

    @staticmethod
    async def archive_question(db: AsyncSession, question_id: uuid.UUID) -> None:
        question = await db.get(Question, question_id)
        QuestionService._reject_private_question(question)
        if not question:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
        question.is_archived = True
        question.workflow_status = "archived"
        question.archived_at = datetime.now(timezone.utc)
        await db.commit()

    @staticmethod
    async def generate_quiz(
        db: AsyncSession,
        candidate_profile_id: uuid.UUID,
        topic: str,
        num_questions: int = 10,
    ) -> dict:
        """Persist a candidate-owned quiz and start its answer-safe timed session."""
        from app.services.assessment_service import AssessmentService

        topic = topic.strip()
        if not topic:
            raise HTTPException(status_code=422, detail="A quiz topic is required.")
        if not 1 <= num_questions <= 50:
            raise HTTPException(status_code=422, detail="Question count must be between 1 and 50.")

        candidate_profile = await db.get(
            CandidateProfile,
            candidate_profile_id,
            options=[selectinload(CandidateProfile.industry)],
        )
        if not candidate_profile:
            raise HTTPException(status_code=404, detail="Candidate profile not found")
        if not candidate_profile.industry_id:
            raise HTTPException(status_code=422, detail="Select an industry before creating a quiz")

        # Apply exact topic and valid objective provenance filters before the
        # recent-history limit so unrelated/AI-scored practice cannot calibrate it.
        practice_logs = (await db.scalars(
            select(QuestionPracticeLog).join(Question, Question.id == QuestionPracticeLog.question_id).where(
                QuestionPracticeLog.candidate_profile_id == candidate_profile.id,
                func.lower(Question.topic) == topic.lower(),
                QuestionPracticeLog.evaluation_status == "evaluated",
                QuestionPracticeLog.evaluation_provenance == "deterministic",
                QuestionPracticeLog.score_percentage.between(0, 100),
                QuestionService._public_content_filter(),
            ).order_by(QuestionPracticeLog.created_at.desc(), QuestionPracticeLog.id.desc()).limit(20)
        )).all()
        sample_count = len(practice_logs)
        understanding_pct = round(sum(log.score_percentage for log in practice_logs) / sample_count) if sample_count else None
        if understanding_pct is None or understanding_pct < 50:
            suggested_difficulty = "beginner"
        elif understanding_pct < 75:
            suggested_difficulty = "intermediate"
        else:
            suggested_difficulty = "advanced"

        # Try to get approved questions matching the topic first
        query = (
            select(Question)
            .where(
                Question.workflow_status == "published",
                Question.approval_status == ApprovalStatus.APPROVED,
                Question.is_archived.is_(False),
                QuestionService._public_content_filter(),
                Question.industry_id == candidate_profile.industry_id,
                Question.difficulty == DifficultyLevel(suggested_difficulty),
                func.lower(Question.topic) == topic.lower(),
            )
            .order_by(func.random())
            .limit(num_questions)
        )
        result = await db.execute(query)
        approved_questions = result.scalars().all()

        # If the published bank is short, use the shared strict AI generator.
        # It fails explicitly for unavailable/invalid output instead of inventing
        # questions or returning a smaller set than the candidate requested.
        missing_count = num_questions - len(approved_questions)

        # Build candidate experience context for AI generation
        months = max(0, int(candidate_profile.total_experience_months or 0))
        experience_band = (
            "10+ years" if months >= 120 else "5-10 years" if months >= 60 else
            "2-5 years" if months >= 24 else "under 2 years" if months else
            "student/fresher"
        )

        candidate_skills = list(dict.fromkeys(candidate_profile.key_skills or []))

        generated = []
        if missing_count > 0:
            generated = await AssessmentService.generate_assessment_questions(
                request=SimpleNamespace(
                    question_types=[QuestionType.MCQ_SINGLE.value, QuestionType.SHORT_ANSWER.value],
                    difficulty=suggested_difficulty,
                    subject=topic,
                    topic=topic,
                    interview_round="Practice",
                ),
                industry_name=candidate_profile.industry.name if candidate_profile.industry else "Not provided",
                role_title=candidate_profile.target_role or "Not provided",
                existing_questions=[question.question_text for question in approved_questions],
                number_of_questions=missing_count,
                candidate_experience=experience_band,
                candidate_skills=candidate_skills,
            )

        duration_minutes = min(180, max(5, num_questions * 3))
        assessment = Assessment(
            title=f"Practice Quiz — {topic}"[:255],
            description=f"{len(approved_questions)} approved bank question(s) and {len(generated)} AI-generated, unreviewed question(s).",
            candidate_profile_id=candidate_profile.id,
            industry_id=candidate_profile.industry_id,
            difficulty=suggested_difficulty,
            duration_minutes=duration_minutes,
            total_questions=num_questions,
            passing_percentage=65.0,
            marks_per_question=10.0,
            negative_marking_points=0.0,
            randomize_questions=False,
            is_active=True,
        )
        db.add(assessment)
        await db.flush()
        session_questions = list(approved_questions)
        for item in generated:
            question = Question(
                industry_id=candidate_profile.industry_id,
                question_text=item.question_text,
                question_type=item.question_type,
                subject=topic,
                topic=topic,
                difficulty=item.difficulty,
                interview_round="Practice",
                options=[option.model_dump() for option in item.options],
                expected_answer=item.expected_answer,
                explanation=item.explanation,
                evaluation_rubric=item.evaluation_rubric,
                tags=["ai_generated", "assessment_only"],
                source_provenance=SourceProvenance.AI_GENERATED,
                approval_status=ApprovalStatus.PENDING,
                workflow_status="draft",
                estimated_minutes=max(1, duration_minutes // num_questions),
            )
            db.add(question)
            await db.flush()
            session_questions.append(question)
        for index, question in enumerate(session_questions, start=1):
            db.add(AssessmentQuestion(assessment_id=assessment.id, question_id=question.id, order_index=index))
        await db.commit()
        session = await AssessmentService.start_assessment(db, assessment.id, candidate_profile)
        bank_ids = {question.id for question in approved_questions}

        return {
            "topic": topic,
            "understanding_percentage": understanding_pct,
            "sample_count": sample_count,
            "suggested_difficulty": suggested_difficulty,
            "experience_band": experience_band,
            "questions": [{
                "id": str(question.id),
                "question_text": question.question_text,
                "question_type": question.question_type.value,
                "difficulty": question.difficulty.value,
                "options": [{"id": option.get("id"), "text": option.get("text")} for option in question.options],
                "expected_answer": None,
                "source_provenance": "published_question_bank" if question.id in bank_ids else "ai_generated_unreviewed",
            } for question in session.questions],
            "generated_count": len(generated),
            "based_on_approved": len(approved_questions),
            "assessment_id": str(session.assessment_id),
            "attempt_id": str(session.attempt_id),
            "started_at": session.started_at,
            "ends_at": session.ends_at,
        }
