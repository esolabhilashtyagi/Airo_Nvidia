import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

from app.integrations.ai.prompt_manager import PromptManager
from app.integrations.ai.provider_factory import get_ai_provider
from app.integrations.ai.response_validator import ResponseValidator
from app.models.assessment import (
    Assessment, AssessmentAttempt, AssessmentQuestion,
    AssessmentResult, AttemptStatus, CandidateAnswer
)
from app.models.candidate import CandidateProfile
from app.models.question import ApprovalStatus, DifficultyLevel, Question, QuestionPracticeLog, QuestionType, SourceProvenance
from app.models.taxonomy import Industry, JobRole, Skill
from app.schemas.assessment import (
    AssessmentConfigureRequest, AssessmentResponse, AssessmentResultResponse,
    AssessmentStartResponse, AttemptHistoryItem, CandidateAnswerSaveRequest
)
from app.schemas.question import QuestionResponse


class AnswerEvaluation(BaseModel):
    score_awarded: float = Field(ge=0, le=100)
    accuracy_score: float = Field(ge=0, le=10)
    completeness_score: float = Field(ge=0, le=10)
    conceptual_clarity_score: float = Field(ge=0, le=10)
    strengths: List[str] = Field(default_factory=list, max_length=10)
    gaps: List[str] = Field(default_factory=list, max_length=10)
    detailed_feedback: str = Field(min_length=1, max_length=5000)


class GeneratedAssessmentOption(BaseModel):
    id: str = Field(min_length=1, max_length=10)
    text: str = Field(min_length=1, max_length=1000)
    is_correct: bool


class GeneratedAssessmentQuestion(BaseModel):
    question_type: QuestionType
    difficulty: DifficultyLevel
    # Direct quiz consumers can construct content-only objects; the generated set
    # validator below requires real labels on every provider-produced item.
    subject: Optional[str] = Field(default=None, min_length=1, max_length=255)
    topic: Optional[str] = Field(default=None, min_length=1, max_length=255)
    question_text: str = Field(min_length=10, max_length=4000)
    expected_answer: str = Field(min_length=1, max_length=10000)
    explanation: Optional[str] = Field(default=None, max_length=4000)
    options: List[GeneratedAssessmentOption] = Field(default_factory=list, max_length=8)
    evaluation_rubric: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("subject", "topic", mode="before")
    @classmethod
    def normalize_labels(cls, value):
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_question_shape(self):
        if self.question_type in (QuestionType.MCQ_SINGLE, QuestionType.MCQ_MULTIPLE):
            ids = [option.id.strip().casefold() for option in self.options]
            correct_count = sum(option.is_correct for option in self.options)
            if len(self.options) < 2 or len(set(ids)) != len(ids):
                raise ValueError("Choice questions require at least two uniquely identified options")
            if correct_count < 1 or (self.question_type == QuestionType.MCQ_SINGLE and correct_count != 1):
                raise ValueError("Choice questions require valid correct option(s)")
        elif self.options:
            raise ValueError("Free-response questions must not include options")
        return self


class GeneratedAssessmentQuestionSet(BaseModel):
    questions: List[GeneratedAssessmentQuestion] = Field(min_length=1, max_length=50)

    @model_validator(mode="after")
    def require_item_labels(self):
        if any(not item.subject or not item.topic for item in self.questions):
            raise ValueError("Every generated question requires subject and topic labels")
        return self


class AssessmentService:
    @staticmethod
    async def configure_and_create_assessment(
        db: AsyncSession,
        request: AssessmentConfigureRequest,
        candidate_profile: CandidateProfile,
    ) -> AssessmentResponse:
        # Validate taxonomy before querying the bank, even when no AI is needed.
        industry = await db.get(Industry, request.industry_id)
        if not industry or not industry.is_active:
            raise HTTPException(status_code=422, detail="Select an active industry before creating an assessment.")
        role = None
        target_role = (getattr(candidate_profile, "target_role", None) or "").strip()[:255]
        if request.job_role_id:
            role = await db.scalar(select(JobRole).where(
                JobRole.id == request.job_role_id,
                JobRole.industry_id == request.industry_id,
                JobRole.is_active.is_(True),
            ))
            if not role:
                raise HTTPException(status_code=422, detail="Select an active job role in the chosen industry.")
        elif target_role:
            role = await db.scalar(select(JobRole).where(
                JobRole.industry_id == request.industry_id,
                func.lower(func.trim(JobRole.title)) == target_role.lower(),
            ).order_by(JobRole.id).limit(1))
            if role and not role.is_active:
                raise HTTPException(status_code=422, detail="Select an active job role in the chosen industry.")
        role_id = role.id if role else None
        required_skill = None
        if request.skill_id:
            required_skill = await db.get(Skill, request.skill_id)
            if not required_skill or not required_skill.is_active:
                raise HTTPException(status_code=422, detail="Select an active skill before creating an assessment.")

        # Prefer approved bank content. The configured AI provider fills only the missing count; its
        # output is stored as an unapproved draft linked to this candidate's test.
        query = (
            select(Question)
            .where(
                Question.industry_id == request.industry_id,
                Question.workflow_status == "published",
                Question.approval_status == ApprovalStatus.APPROVED,
                Question.is_archived.is_(False),
            )
        )
        if role_id:
            query = query.where(or_(
                Question.job_role_id == role_id,
                Question.job_roles.any(id=role_id),
            ))
        if request.subject:
            query = query.where(Question.subject == request.subject)
        topics = AssessmentService._requested_topics(request)
        if topics:
            query = query.where(Question.topic.in_(topics))
        if request.skill_id:
            query = query.where(Question.skills.any(id=request.skill_id))
        if request.question_types:
            try:
                types = [QuestionType(item) for item in request.question_types]
            except ValueError as exc:
                raise HTTPException(status_code=422, detail="One or more question types are invalid") from exc
            query = query.where(Question.question_type.in_(types))
        if request.interview_round and request.interview_round.strip().casefold() not in {"mixed", "any"}:
            query = query.where(Question.interview_round == request.interview_round)
        if request.difficulty and request.difficulty.strip().casefold() not in {"mixed", "any"}:
            try:
                diff_enum = DifficultyLevel(request.difficulty.strip().casefold())
                query = query.where(Question.difficulty == diff_enum)
            except ValueError as exc:
                raise HTTPException(status_code=422, detail="Difficulty is invalid") from exc

        query = query.order_by(func.random() if request.randomize_questions else Question.created_at, Question.id).limit(request.num_questions)
        result = await db.execute(query)
        selected_questions = result.scalars().all()

        generated_questions: List[GeneratedAssessmentQuestion] = []
        missing_count = request.num_questions - len(selected_questions)
        if missing_count:
            provider = get_ai_provider()
            if not provider.is_available():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Only {len(selected_questions)} published questions match this configuration; {request.num_questions} were requested.",
                )
            practice_performance = await AssessmentService._candidate_topic_practice_context(
                db, candidate_profile.id
            )
            generated_questions = await AssessmentService.generate_assessment_questions(
                request=request,
                industry_name=industry.name,
                role_title=role.title if role else target_role or "General role",
                existing_questions=[question.question_text for question in selected_questions],
                number_of_questions=missing_count,
                candidate_experience=AssessmentService._candidate_experience_context(candidate_profile),
                candidate_skills=[str(skill) for skill in (candidate_profile.key_skills or [])[:30]],
                practice_performance=practice_performance,
                required_skill=required_skill.name[:255] if required_skill else None,
            )

        new_assessment = Assessment(
            title=f"{request.difficulty or 'Mixed difficulty'} Assessment — {request.interview_round or 'General practice'}",
            description=(
                f"Timed {request.duration_minutes}-minute assessment with "
                f"{len(selected_questions)} approved Question Bank question(s) and "
                f"{len(generated_questions)} AI-generated, unreviewed question(s)."
            ),
            candidate_profile_id=candidate_profile.id,
            industry_id=request.industry_id,
            job_role_id=role_id,
            difficulty=request.difficulty or "Mixed",
            duration_minutes=request.duration_minutes,
            total_questions=request.num_questions,
            passing_percentage=65.0,
            marks_per_question=request.marks_per_question,
            negative_marking_points=request.negative_marking_points,
            randomize_questions=request.randomize_questions,
            is_active=True
        )
        db.add(new_assessment)
        await db.flush()

        for idx, q in enumerate(selected_questions, start=1):
            db.add(
                AssessmentQuestion(
                    assessment_id=new_assessment.id,
                    question_id=q.id,
                    order_index=idx
                )
            )

        round_name = request.interview_round or "Technical"
        for idx, item in enumerate(generated_questions, start=len(selected_questions) + 1):
            generated_question = Question(
                question_text=item.question_text,
                question_type=item.question_type,
                industry_id=request.industry_id,
                job_role_id=role_id,
                subject=item.subject,
                topic=item.topic,
                skills=[required_skill] if required_skill else [],
                difficulty=item.difficulty,
                interview_round=round_name,
                options=[option.model_dump() for option in item.options],
                expected_answer=item.expected_answer,
                explanation=item.explanation,
                evaluation_rubric=item.evaluation_rubric,
                tags=["ai_generated", "assessment_only"],
                source_provenance=SourceProvenance.AI_GENERATED,
                approval_status=ApprovalStatus.PENDING,
                workflow_status="draft",
                estimated_minutes=max(1, request.duration_minutes // request.num_questions),
            )
            db.add(generated_question)
            await db.flush()
            db.add(AssessmentQuestion(
                assessment_id=new_assessment.id,
                question_id=generated_question.id,
                order_index=idx,
            ))

        await db.commit()
        await db.refresh(new_assessment)
        response = AssessmentResponse.model_validate(new_assessment)
        return response.model_copy(update={"ai_generated_question_count": len(generated_questions)})

    @staticmethod
    def _requested_topics(request: AssessmentConfigureRequest) -> List[str]:
        # Quiz callers use SimpleNamespace and may not expose the extra topics field.
        values = [*(getattr(request, "topics", None) or []), *([request.topic] if request.topic else [])]
        topics = []
        seen = set()
        for value in values:
            if not isinstance(value, str) or not value.strip() or len(value.strip()) > 255:
                raise HTTPException(status_code=422, detail="Requested topic labels must contain 1-255 characters.")
            label = value.strip()
            if label.casefold() not in seen:
                topics.append(label)
                seen.add(label.casefold())
        if len(topics) > 21:
            raise HTTPException(status_code=422, detail="Too many requested topics.")
        return topics

    @staticmethod
    async def generate_assessment_questions(
        request: AssessmentConfigureRequest,
        industry_name: str,
        role_title: str,
        existing_questions: List[str],
        number_of_questions: int,
        candidate_experience: Optional[str] = None,
        candidate_skills: Optional[List[str]] = None,
        practice_performance: Optional[List[Dict[str, Any]]] = None,
        required_skill: Optional[str] = None,
    ) -> List[GeneratedAssessmentQuestion]:
        provider = get_ai_provider()
        if not provider.is_available():
            raise HTTPException(
                status_code=503,
                detail="Not enough approved questions match this assessment. AI question generation is unavailable; check the configured AI provider or add approved Question Bank content.",
            )

        requested_types = list(dict.fromkeys(request.question_types)) or [QuestionType.MCQ_SINGLE.value]
        try:
            allowed_types = [QuestionType(value) for value in requested_types]
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="One or more question types are invalid") from exc
        mixed = not request.difficulty or request.difficulty.strip().casefold() in {"mixed", "any"}
        topics = AssessmentService._requested_topics(request)
        prompt = PromptManager.get_assessment_questions_prompt({
            "industry": industry_name,
            "job_role": role_title,
            "subject": request.subject or "Infer a suitable subject from the job role and candidate context",
            "topic": request.topic or (topics[0] if topics else None) or request.subject or "Infer relevant topics from the job role and candidate skills",
            "requested_topics": topics,
            "required_skill": required_skill.strip()[:255] if required_skill else None,
            "difficulty": "mixed difficulty" if mixed else request.difficulty,
            "interview_round": request.interview_round or "Technical",
            "experience_level": candidate_experience or "not provided; use general role-appropriate practice",
            "candidate_skills": list(dict.fromkeys(candidate_skills or [])),
            "practice_performance": practice_performance or [],
            "allowed_question_types": [value.value for value in allowed_types],
            "number_of_questions": number_of_questions,
            "existing_questions": existing_questions,
        })
        prompt += (
            "\nEvery item must include nonblank subject and topic labels accurately describing its content. "
            "If a subject is requested, use that exact subject label. If requested_topics is nonempty, "
            "each topic label must exactly match one of those requested topics; do not invent other labels. "
            "When required_skill is supplied, every question must exercise that skill, not merely mention it. "
            "When labels are unspecified, label the actual question content; never substitute generic metadata."
        )
        try:
            response = await provider.generate_structured(prompt, GeneratedAssessmentQuestionSet)
            if not response.is_success or not response.structured_data:
                raise ValueError("AI provider returned no structured assessment questions")
            generated = GeneratedAssessmentQuestionSet.model_validate(response.structured_data).questions
            texts = [" ".join(item.question_text.split()) for item in generated]
            normalized = [text.casefold() for text in texts]
            existing = {" ".join(text.split()).casefold() for text in existing_questions}
            if len(generated) != number_of_questions or len(set(normalized)) != len(normalized):
                raise ValueError("AI provider returned an incomplete or repeated question set")
            if existing.intersection(normalized):
                raise ValueError("AI provider repeated an existing Question Bank item")
            if request.subject and any(item.subject != request.subject for item in generated):
                raise ValueError("AI provider returned a subject outside the requested configuration")
            if topics and any(item.topic not in topics for item in generated):
                raise ValueError("AI provider returned a topic outside the requested configuration")
            if any(item.question_type not in allowed_types for item in generated):
                raise ValueError("AI provider returned a question type outside the requested configuration")
            if request.difficulty and request.difficulty.strip().casefold() not in {"mixed", "any"}:
                wanted = DifficultyLevel(request.difficulty.strip().casefold())
                if any(item.difficulty != wanted for item in generated):
                    raise ValueError("AI provider returned a difficulty outside the requested configuration")
            if mixed and len(generated) > 1 and len({item.difficulty for item in generated}) == 1:
                raise ValueError("AI provider did not vary difficulty for a mixed assessment")
            return generated
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("AI assessment question generation failed (%s)", type(exc).__name__)
            raise HTTPException(
                status_code=503,
                detail="The configured AI provider could not produce a complete, valid question set. No assessment or generated questions were saved; retry or add approved questions to the bank.",
            ) from exc

    @staticmethod
    def _candidate_experience_context(candidate_profile: CandidateProfile) -> str:
        """Return a coarse, non-identifying experience band for question calibration."""
        candidate_type = (candidate_profile.candidate_type or "").strip().casefold()
        months = max(0, int(candidate_profile.total_experience_months or 0))
        if months >= 120:
            band = "10+ years"
        elif months >= 60:
            band = "5-10 years"
        elif months >= 24:
            band = "2-5 years"
        elif months > 0:
            band = "under 2 years"
        elif candidate_type in {"student_fresher", "student", "fresher"}:
            band = "student/fresher; no professional experience duration recorded"
        else:
            band = "experience duration not documented"
        return band

    @staticmethod
    async def _candidate_topic_practice_context(
        db: AsyncSession,
        candidate_profile_id: uuid.UUID,
    ) -> List[Dict[str, Any]]:
        """Return objective, deterministic practice aggregates, never answer text."""
        rows = await db.execute(
            select(
                Question.topic,
                func.avg(QuestionPracticeLog.score_percentage),
                func.count(QuestionPracticeLog.id),
            )
            .join(QuestionPracticeLog, QuestionPracticeLog.question_id == Question.id)
            .where(
                QuestionPracticeLog.candidate_profile_id == candidate_profile_id,
                QuestionPracticeLog.evaluation_status == "evaluated",
                QuestionPracticeLog.evaluation_provenance == "deterministic",
                QuestionPracticeLog.score_percentage.is_not(None),
            )
            .group_by(Question.topic)
            .order_by(func.count(QuestionPracticeLog.id).desc(), Question.topic)
            .limit(20)
        )
        summary = []
        for topic, average, count in rows.all():
            if topic and count:
                summary.append({
                    "topic": topic[:255],
                    "average_score_percentage": round(float(average), 1),
                    "evaluated_question_count": int(count),
                })
        return summary

    @staticmethod
    async def start_assessment(
        db: AsyncSession,
        assessment_id: uuid.UUID,
        candidate_profile: CandidateProfile
    ) -> AssessmentStartResponse:
        assessment = await db.scalar(select(Assessment).where(
            Assessment.id == assessment_id,
            Assessment.candidate_profile_id == candidate_profile.id,
        ).with_for_update())
        if not assessment or not assessment.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")

        # Reuse an interrupted in-progress attempt for recovery rather than
        # creating a second active attempt for the same candidate.
        active_attempt = await db.scalar(select(AssessmentAttempt).where(
            AssessmentAttempt.assessment_id == assessment.id,
            AssessmentAttempt.candidate_profile_id == candidate_profile.id,
            AssessmentAttempt.status == AttemptStatus.IN_PROGRESS,
        ).options(selectinload(AssessmentAttempt.answers)).order_by(AssessmentAttempt.started_at.desc()).with_for_update().execution_options(populate_existing=True))
        if active_attempt:
            deadline = active_attempt.started_at + timedelta(minutes=assessment.duration_minutes)
            if datetime.now(timezone.utc) >= deadline:
                await AssessmentService.submit_assessment(
                    db, active_attempt.id, candidate_profile.id, timed_out=True,
                )
                raise HTTPException(
                    status_code=410,
                    detail="This assessment attempt has expired and was submitted. Start a new attempt to continue.",
                )
        # Load questions
        q_query = (
            select(AssessmentQuestion)
            .where(AssessmentQuestion.assessment_id == assessment_id)
            .options(
                selectinload(AssessmentQuestion.question).selectinload(Question.industry),
                selectinload(AssessmentQuestion.question).selectinload(Question.job_role)
            )
            .order_by(AssessmentQuestion.order_index.asc())
        )
        q_res = await db.execute(q_query)
        assessment_questions = q_res.scalars().all()

        attempt = active_attempt or AssessmentAttempt(
            assessment_id=assessment.id,
            candidate_profile_id=candidate_profile.id,
            started_at=datetime.now(timezone.utc),
            status=AttemptStatus.IN_PROGRESS,
            time_spent_seconds=0
        )
        if not active_attempt:
            db.add(attempt)
            await db.flush()

        # Build clean Question responses (hiding expected_answer, is_correct, explanation)
        clean_questions: List[QuestionResponse] = []
        for aq in assessment_questions:
            orig = aq.question
            clean_opts = []
            for opt in orig.options:
                clean_opts.append({"id": opt.get("id"), "text": opt.get("text")})

            q_resp = QuestionResponse(
                id=orig.id,
                question_text=orig.question_text,
                question_type=orig.question_type,
                industry_id=orig.industry_id,
                job_role_id=orig.job_role_id,
                subject=orig.subject,
                topic=orig.topic,
                difficulty=orig.difficulty,
                interview_round=orig.interview_round,
                options=clean_opts,
                expected_answer=None, # Strictly hidden during test
                explanation=None, # Strictly hidden during test
                evaluation_rubric={},
                tags=orig.tags,
                source_provenance=orig.source_provenance,
                approval_status=orig.approval_status,
                created_at=orig.created_at,
                updated_at=orig.updated_at
            )
            clean_questions.append(q_resp)

        await db.commit()

        return AssessmentStartResponse(
            attempt_id=attempt.id,
            assessment_id=assessment.id,
            title=assessment.title,
            duration_minutes=assessment.duration_minutes,
            total_questions=len(clean_questions),
            started_at=attempt.started_at,
            ends_at=attempt.started_at + timedelta(minutes=assessment.duration_minutes),
            questions=clean_questions,
            saved_answers=[{
                "question_id": answer.question_id,
                "selected_options": answer.selected_options,
                "text_response": answer.text_response,
                "is_marked_for_review": answer.is_marked_for_review,
            } for answer in (active_attempt.answers if active_attempt else [])],
        )

    @staticmethod
    async def save_answer(
        db: AsyncSession,
        attempt_id: uuid.UUID,
        candidate_profile_id: uuid.UUID,
        request: CandidateAnswerSaveRequest
    ) -> Dict[str, Any]:
        attempt = await db.scalar(select(AssessmentAttempt).where(AssessmentAttempt.id == attempt_id).with_for_update().execution_options(populate_existing=True))
        if not attempt or attempt.candidate_profile_id != candidate_profile_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment attempt not found")

        if attempt.status != AttemptStatus.IN_PROGRESS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assessment has already been submitted")

        assessment = await db.get(Assessment, attempt.assessment_id)
        if not assessment:
            raise HTTPException(status_code=404, detail="Assessment not found")
        deadline = attempt.started_at + timedelta(minutes=assessment.duration_minutes)
        if datetime.now(timezone.utc) >= deadline:
            await AssessmentService.submit_assessment(db, attempt_id, candidate_profile_id, timed_out=True)
            return {"saved": False, "expired": True, "question_id": str(request.question_id)}

        included = await db.scalar(select(AssessmentQuestion.id).where(
            AssessmentQuestion.assessment_id == assessment.id,
            AssessmentQuestion.question_id == request.question_id,
        ))
        if not included:
            raise HTTPException(status_code=404, detail="Question is not part of this assessment")

        question = await db.get(Question, request.question_id)
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")
        selected_options, text_response = AssessmentService._validate_answer(question, request)

        # Find existing or create
        ans_q = select(CandidateAnswer).where(
            CandidateAnswer.assessment_attempt_id == attempt_id,
            CandidateAnswer.question_id == request.question_id
        )
        ans_res = await db.execute(ans_q.with_for_update())
        answer_rec = ans_res.scalar_one_or_none()

        if not answer_rec:
            answer_rec = CandidateAnswer(
                assessment_attempt_id=attempt_id,
                question_id=request.question_id,
                selected_options=selected_options,
                text_response=text_response,
                is_marked_for_review=request.is_marked_for_review
            )
            db.add(answer_rec)
        else:
            answer_rec.selected_options = selected_options
            answer_rec.text_response = text_response
            answer_rec.is_marked_for_review = request.is_marked_for_review

        await db.commit()
        return {"saved": True, "question_id": str(request.question_id)}

    @staticmethod
    def _validate_answer(question: Question, answer: Any):
        """Validate both incoming and previously stored answers before scoring."""
        try:
            payload = CandidateAnswerSaveRequest(
                question_id=question.id,
                selected_options=answer.selected_options or [],
                text_response=answer.text_response,
            )
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail="Invalid answer option IDs or answer shape.") from exc
        selected = payload.selected_options
        if question.question_type in (QuestionType.MCQ_SINGLE, QuestionType.MCQ_MULTIPLE):
            if payload.text_response is not None:
                raise HTTPException(status_code=422, detail="Choice questions accept selected options, not text responses.")
            if question.question_type == QuestionType.MCQ_SINGLE and len(selected) > 1:
                raise HTTPException(status_code=422, detail="Single-choice questions accept at most one option.")
            option_ids = {str(option["id"]).strip().casefold(): str(option["id"]) for option in question.options}
            if any(value.casefold() not in option_ids for value in selected):
                raise HTTPException(status_code=422, detail="Selected option is not part of this question.")
            selected = [option_ids[value.casefold()] for value in selected]
        elif selected:
            raise HTTPException(status_code=422, detail="Free-response questions accept text, not selected options.")
        return selected, payload.text_response

    @staticmethod
    def _serialize_result(result: AssessmentResult, attempt: AssessmentAttempt) -> AssessmentResultResponse:
        return AssessmentResultResponse.model_validate(result).model_copy(update={
            "time_spent_seconds": attempt.time_spent_seconds,
            "completed_at": attempt.completed_at,
        })

    @staticmethod
    async def submit_assessment(
        db: AsyncSession,
        attempt_id: uuid.UUID,
        candidate_profile_id: uuid.UUID,
        timed_out: bool = False,
    ) -> AssessmentResultResponse:
        attempt_q = (
            select(AssessmentAttempt)
            .where(
                AssessmentAttempt.id == attempt_id,
                AssessmentAttempt.candidate_profile_id == candidate_profile_id
            )
            .options(
                selectinload(AssessmentAttempt.assessment).selectinload(Assessment.questions).selectinload(AssessmentQuestion.question),
                selectinload(AssessmentAttempt.answers).selectinload(CandidateAnswer.question),
                selectinload(AssessmentAttempt.result)
            ).with_for_update().execution_options(populate_existing=True)
        )
        res = await db.execute(attempt_q)
        attempt = res.scalar_one_or_none()

        if not attempt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")

        if attempt.status in {AttemptStatus.COMPLETED, AttemptStatus.TIMED_OUT} and attempt.result:
            return AssessmentService._serialize_result(attempt.result, attempt)
        if attempt.status != AttemptStatus.IN_PROGRESS:
            raise HTTPException(status_code=400, detail="Assessment attempt is not in progress")

        questions_by_id = {item.question_id: item.question for item in attempt.assessment.questions}
        for answer in attempt.answers:
            question = questions_by_id.get(answer.question_id)
            if not question:
                raise HTTPException(status_code=422, detail="Saved answer is not part of this assessment.")
            answer.selected_options, answer.text_response = AssessmentService._validate_answer(question, answer)

        now = datetime.now(timezone.utc)
        attempt.completed_at = now
        deadline = attempt.started_at + timedelta(minutes=attempt.assessment.duration_minutes)
        timed_out = timed_out or now >= deadline
        attempt.status = AttemptStatus.TIMED_OUT if timed_out else AttemptStatus.COMPLETED
        if attempt.started_at:
            attempt.time_spent_seconds = max(0, min(
                int((now - attempt.started_at).total_seconds()),
                attempt.assessment.duration_minutes * 60,
            ))

        # Map candidate answers by question_id
        answers_map = {ans.question_id: ans for ans in attempt.answers}

        total_questions = len(attempt.assessment.questions)
        correct_count = 0
        incorrect_count = 0
        unanswered_count = 0
        topic_scores: Dict[str, Dict[str, Any]] = {}
        diff_scores: Dict[str, Dict[str, Any]] = {}
        question_feedback: List[Dict[str, Any]] = []
        total_score = 0.0
        max_score = float(total_questions * attempt.assessment.marks_per_question)
        has_unavailable_evaluations = False

        for aq in attempt.assessment.questions:
            q = aq.question
            topic = q.topic or "General"
            diff = q.difficulty.value if hasattr(q.difficulty, 'value') else str(q.difficulty)

            if topic not in topic_scores:
                topic_scores[topic] = {"correct": 0, "total": 0, "evaluated": 0, "marks_awarded": 0.0}
            topic_scores[topic]["total"] += 1

            if diff not in diff_scores:
                diff_scores[diff] = {"correct": 0, "total": 0, "evaluated": 0, "marks_awarded": 0.0}
            diff_scores[diff]["total"] += 1

            ans_rec = answers_map.get(q.id)
            if not ans_rec or (not ans_rec.selected_options and not ans_rec.text_response):
                unanswered_count += 1
                if ans_rec:
                    ans_rec.score_awarded = 0.0
                    ans_rec.is_correct = False
                    ans_rec.evaluation_status = "evaluated"
                    ans_rec.evaluation_provenance = "deterministic"
                    ans_rec.feedback = "No answer was submitted for this question."
                topic_scores[topic]["evaluated"] += 1
                diff_scores[diff]["evaluated"] += 1
                question_feedback.append({
                    "question_id": str(q.id), "topic": topic, "question_type": q.question_type.value,
                    "status": "unanswered", "marks_awarded": 0.0,
                    "max_marks": attempt.assessment.marks_per_question,
                    "feedback": "No answer was submitted for this question.",
                })
                continue

            earned: Optional[float] = None
            feedback_text: Optional[str] = None
            rubric_breakdown: Dict[str, Any] = {}
            gaps: List[str] = []
            if q.question_type in (QuestionType.MCQ_SINGLE, QuestionType.MCQ_MULTIPLE):
                correct_ids = [str(opt["id"]).strip().upper() for opt in q.options if opt.get("is_correct")]
                user_ids = [u.strip().upper() for u in ans_rec.selected_options]
                if (
                    q.question_type == QuestionType.MCQ_MULTIPLE and correct_ids
                    and not attempt.assessment.negative_marking_points
                ):
                    # Keep existing partial credit only when negative marking is disabled.
                    # With a configured penalty, all incorrect choice answers use that penalty.
                    overlap = len(set(correct_ids) & set(user_ids))
                    precision = overlap / len(set(user_ids)) if user_ids else 0.0
                    recall = overlap / len(set(correct_ids))
                    ratio = max(0.0, (precision + recall) / 2)
                    is_correct = set(correct_ids) == set(user_ids)
                    earned = attempt.assessment.marks_per_question * ratio
                else:
                    is_correct = set(correct_ids) == set(user_ids)
                    earned = attempt.assessment.marks_per_question if is_correct else -attempt.assessment.negative_marking_points
                ans_rec.is_correct = is_correct
                ans_rec.score_awarded = earned
                ans_rec.evaluation_status = "evaluated"
                ans_rec.evaluation_provenance = "deterministic"
                ans_rec.feedback = "Correct objective answer." if is_correct else "Incorrect objective answer."
                feedback_text = ans_rec.feedback
                if is_correct:
                    correct_count += 1
                    topic_scores[topic]["correct"] += 1
                    diff_scores[diff]["correct"] += 1
                else:
                    incorrect_count += 1
            elif q.question_type == QuestionType.CODING:
                ans_rec.is_correct = None
                ans_rec.score_awarded = None
                ans_rec.evaluation_status = "unavailable"
                ans_rec.evaluation_provenance = "none"
                ans_rec.feedback = "Code was saved. Secure code execution is not configured, so no execution result or score is available."
                has_unavailable_evaluations = True
                feedback_text = ans_rec.feedback
            else:
                evaluation = await AssessmentService._evaluate_subjective_answer(q, ans_rec.text_response or "", attempt.assessment.marks_per_question)
                if evaluation is None:
                    ans_rec.is_correct = None
                    ans_rec.score_awarded = None
                    ans_rec.evaluation_status = "unavailable"
                    ans_rec.evaluation_provenance = "none"
                    ans_rec.feedback = "Your answer was saved, but AI evaluation is unavailable. No score was assigned."
                    has_unavailable_evaluations = True
                else:
                    earned, rubric_breakdown, gaps, feedback_text = evaluation
                    ans_rec.score_awarded = earned
                    ans_rec.is_correct = earned >= attempt.assessment.marks_per_question * 0.6
                    ans_rec.evaluation_status = "evaluated"
                    ans_rec.evaluation_provenance = "ai"
                    ans_rec.rubric_breakdown = rubric_breakdown
                    ans_rec.missing_concepts = gaps
                    ans_rec.feedback = feedback_text
                    if ans_rec.is_correct:
                        correct_count += 1
                        topic_scores[topic]["correct"] += 1
                        diff_scores[diff]["correct"] += 1
                    else:
                        incorrect_count += 1
            if ans_rec.evaluation_status != "unavailable":
                topic_scores[topic]["evaluated"] += 1
                topic_scores[topic]["marks_awarded"] += earned or 0.0
                diff_scores[diff]["evaluated"] += 1
                diff_scores[diff]["marks_awarded"] += earned or 0.0
                total_score += earned or 0.0
            question_feedback.append({
                "question_id": str(q.id), "topic": topic, "question_type": q.question_type.value,
                "status": ans_rec.evaluation_status, "provenance": ans_rec.evaluation_provenance,
                "marks_awarded": earned, "max_marks": attempt.assessment.marks_per_question,
                "rubric_breakdown": rubric_breakdown, "missing_concepts": gaps,
                "feedback": feedback_text or ans_rec.feedback,
                "expected_answer": q.expected_answer,
                "explanation": q.explanation,
                "candidate_answer": ans_rec.text_response or ans_rec.selected_options,
            })

        percentage = None if has_unavailable_evaluations else round((total_score / max(max_score, 1.0)) * 100.0, 1)
        passed = None if percentage is None else percentage >= attempt.assessment.passing_percentage

        # Strong and weak areas
        strong_areas = [top for top, data in topic_scores.items() if data["evaluated"] and (data["correct"] / data["evaluated"]) >= 0.7]
        weak_areas = [top for top, data in topic_scores.items() if data["evaluated"] and (data["correct"] / data["evaluated"]) < 0.7]

        result_rec = AssessmentResult(
            assessment_attempt_id=attempt.id,
            total_score=total_score,
            max_score=max_score,
            percentage=percentage,
            passed=passed,
            correct_count=correct_count,
            incorrect_count=incorrect_count,
            unanswered_count=unanswered_count,
            topic_breakdown=topic_scores,
            difficulty_breakdown=diff_scores,
            strong_areas=strong_areas,
            weak_areas=weak_areas,
            recommendations=(
                f"Evaluation is partial because one or more answers need unavailable AI or code execution. Known marks: {total_score:.1f}/{max_score:.1f}."
                if has_unavailable_evaluations else
                f"Focus next on {', '.join(weak_areas)}." if weak_areas else
                "Review the question-level feedback and continue with the next available learning activity."
            ),
            evaluation_status="partial" if has_unavailable_evaluations else "evaluated",
            evaluation_provenance="mixed" if any(ans.evaluation_provenance == "ai" for ans in attempt.answers) else "deterministic",
            question_feedback=question_feedback,
        )
        attempt.result = result_rec
        db.add(result_rec)

        await db.commit()
        await db.refresh(result_rec)

        return AssessmentService._serialize_result(result_rec, attempt)

    @staticmethod
    async def _evaluate_subjective_answer(question: Question, answer: str, max_marks: float):
        provider = get_ai_provider()
        if not provider.is_available():
            return None
        try:
            prompt = PromptManager.get_descriptive_eval_prompt(
                question=question.question_text,
                expected_answer=question.expected_answer,
                candidate_answer=answer,
                rubric=question.evaluation_rubric or {},
            )
            response = await provider.generate_text(prompt=prompt, max_tokens=1200)
            if not response.is_success or not response.raw_text:
                return None
            output, error = ResponseValidator.validate_pydantic(response.raw_text, AnswerEvaluation)
            if error or output is None:
                return None
            marks = max(0.0, min(max_marks, max_marks * output.score_awarded / 100.0))
            breakdown = {
                "accuracy": output.accuracy_score,
                "completeness": output.completeness_score,
                "conceptual_clarity": output.conceptual_clarity_score,
            }
            return marks, breakdown, output.gaps, output.detailed_feedback
        except Exception:
            # Preserve the answer; evaluation is explicitly marked unavailable.
            return None

    @staticmethod
    async def get_history(
        db: AsyncSession,
        candidate_profile_id: uuid.UUID
    ) -> List[AttemptHistoryItem]:
        query = (
            select(AssessmentAttempt)
            .where(AssessmentAttempt.candidate_profile_id == candidate_profile_id)
            .options(
                selectinload(AssessmentAttempt.assessment),
                selectinload(AssessmentAttempt.result)
            )
            .order_by(AssessmentAttempt.started_at.desc())
        )
        result = await db.execute(query)
        attempts = result.scalars().all()

        output: List[AttemptHistoryItem] = []
        for att in attempts:
            pct = att.result.percentage if att.result else None
            pas = att.result.passed if att.result else None
            output.append(
                AttemptHistoryItem(
                    id=att.id,
                    assessment_id=att.assessment_id,
                    assessment_title=att.assessment.title if att.assessment else "Assessment",
                    started_at=att.started_at,
                    completed_at=att.completed_at,
                    status=att.status,
                    percentage=pct,
                    passed=pas,
                    evaluation_status=att.result.evaluation_status if att.result else "pending",
                )
            )
        return output

    @staticmethod
    async def get_result(db: AsyncSession, attempt_id: uuid.UUID, candidate_profile_id: uuid.UUID) -> AssessmentResultResponse:
        attempt = await db.scalar(
            select(AssessmentAttempt).where(
                AssessmentAttempt.id == attempt_id,
                AssessmentAttempt.candidate_profile_id == candidate_profile_id,
                AssessmentAttempt.status.in_([AttemptStatus.COMPLETED, AttemptStatus.TIMED_OUT]),
            ).options(selectinload(AssessmentAttempt.result))
        )
        if not attempt or not attempt.result:
            raise HTTPException(status_code=404, detail="Assessment result not found")
        return AssessmentService._serialize_result(attempt.result, attempt)
