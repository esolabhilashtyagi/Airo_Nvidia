import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.integrations.ai.prompt_manager import PromptManager
from app.integrations.ai.provider_factory import get_ai_provider
from app.integrations.ai.response_validator import ResponseValidator
from app.models.interview import (
    InterviewEvaluation, InterviewQuestion, InterviewResponse,
    InterviewStatus, MockInterview,
)
from app.models.question import ApprovalStatus, Question, QuestionType
from app.models.taxonomy import Industry, JobRole
from app.models.candidate import CandidateProfile
from app.schemas.interview import (
    InterviewReportResponse, InterviewRespondRequest, InterviewResponseReview,
    InterviewSessionResponse, InterviewSetupRequest,
)


class InterviewTurn(BaseModel):
    interviewer_message: str = Field(min_length=2, max_length=4000)
    is_follow_up: bool
    question_focus: str = Field(min_length=2, max_length=120)


class GeneratedInterviewQuestion(BaseModel):
    question_text: str = Field(min_length=10, max_length=2000)


class GeneratedInterviewQuestionSet(BaseModel):
    questions: List[GeneratedInterviewQuestion] = Field(min_length=1, max_length=20)


class InterviewEvaluationOutput(BaseModel):
    overall_score: float = Field(ge=0, le=100)
    technical_score: float = Field(ge=0, le=100)
    domain_score: float = Field(ge=0, le=100)
    communication_score: float = Field(ge=0, le=100)
    structure_score: float = Field(ge=0, le=100)
    key_strengths: List[str] = Field(default_factory=list, max_length=10)
    improvement_areas: List[str] = Field(default_factory=list, max_length=10)
    detailed_feedback: Dict[str, Any] = Field(default_factory=dict)
    question_evaluations: List[Dict[str, Any]] = Field(default_factory=list, max_length=40)


class InterviewService:
    @staticmethod
    def _history(interview: MockInterview, new_answer: Optional[str] = None) -> List[Dict[str, Any]]:
        output = []
        for question in sorted(interview.questions, key=lambda item: item.order_index):
            answer = question.response.candidate_answer if question.response else ""
            if new_answer is not None and not answer and question is interview.questions[-1]:
                answer = new_answer
            output.append({"q": question.question_text, "a": answer})
        return output

    @staticmethod
    async def setup_and_start_interview(
        db: AsyncSession,
        candidate_profile: CandidateProfile,
        request: InterviewSetupRequest,
    ) -> InterviewSessionResponse:
        if request.mode == "voice":
            raise HTTPException(status_code=503, detail="Voice interview is unavailable because no speech provider is configured. Text mode is available.")
        industry_id = request.industry_id or candidate_profile.industry_id
        if not industry_id:
            raise HTTPException(status_code=422, detail="Select an industry before starting an interview.")
        industry = await db.get(Industry, industry_id)
        if not industry or not industry.is_active:
            raise HTTPException(status_code=422, detail="Select an active industry.")

        role = await db.scalar(select(JobRole).where(
            JobRole.industry_id == industry_id,
            JobRole.is_active.is_(True),
            func.lower(JobRole.title) == request.job_role.strip().lower(),
        ))
        question_query = select(Question).where(
            Question.industry_id == industry_id,
            Question.workflow_status == "published",
            Question.approval_status == ApprovalStatus.APPROVED,
            Question.is_archived.is_(False),
            Question.interview_round == request.interview_round,
        )
        if role:
            question_query = question_query.where(or_(
                Question.job_role_id == role.id,
                Question.job_roles.any(id=role.id),
            ))
        else:
            question_query = question_query.where(Question.job_role_id.is_(None))
        bank_questions = (await db.scalars(
            question_query.order_by(func.random()).limit(request.number_of_questions)
        )).all()

        # The shared Question Bank remains the first choice. When it has no
        # approved match, create interview-scoped questions through the configured AI provider;
        # never insert generated content into the editorial question bank.
        question_sources: List[tuple[str, Optional[uuid.UUID], str]]
        if bank_questions:
            question_sources = [
                (question.question_text, question.id, question.source_provenance.value)
                for question in bank_questions
            ]
        else:
            provider = get_ai_provider()
            if not provider.is_available():
                raise HTTPException(
                    status_code=503,
                    detail="No approved questions match this interview. AI question generation is unavailable; configure the AI provider or add approved questions to the bank.",
                )
            prompt = PromptManager.get_interview_questions_prompt(
                role=request.job_role.strip(),
                industry=industry.name,
                round_type=request.interview_round,
                difficulty=request.difficulty,
                experience_level=request.experience_level,
                number_of_questions=request.number_of_questions,
            )
            try:
                response = await provider.generate_structured(
                    prompt=prompt,
                    response_schema=GeneratedInterviewQuestionSet,
                )
                if not response.is_success or not response.structured_data:
                    raise ValueError("AI provider returned no valid generated question set")
                generated = GeneratedInterviewQuestionSet.model_validate(response.structured_data)
                texts = [" ".join(item.question_text.split()) for item in generated.questions]
                normalized = [text.casefold() for text in texts]
                if len(texts) != request.number_of_questions or len(set(normalized)) != len(texts):
                    raise ValueError("AI provider returned an incomplete or repeated question set")
                question_sources = [(text, None, "ai_generated") for text in texts]
            except Exception as exc:
                raise HTTPException(
                    status_code=503,
                    detail="The configured AI provider could not produce a complete, valid interview question set. No interview was started; retry or add approved questions to the bank.",
                ) from exc

        interview = MockInterview(
            candidate_profile_id=candidate_profile.id,
            industry_id=industry_id,
            job_role=request.job_role.strip(),
            interview_type=request.interview_type,
            target_company=request.target_company,
            interview_round=request.interview_round,
            difficulty=request.difficulty,
            experience_level=request.experience_level,
            duration_minutes=request.duration_minutes,
            total_questions=len(question_sources),
            mode="text",
            status=InterviewStatus.IN_PROGRESS,
            started_at=datetime.now(timezone.utc),
            evaluation_status="pending",
        )
        db.add(interview)
        await db.flush()
        for index, (question_text, source_question_id, source_provenance) in enumerate(question_sources, start=1):
            db.add(InterviewQuestion(
                mock_interview_id=interview.id,
                question_text=question_text,
                source_question_id=source_question_id,
                source_provenance=source_provenance,
                order_index=index,
                is_follow_up=False,
            ))
        await db.commit()
        saved_interview = await db.scalar(
            select(MockInterview).where(MockInterview.id == interview.id)
            .options(selectinload(MockInterview.questions).selectinload(InterviewQuestion.response))
        )
        first_question = sorted(saved_interview.questions, key=lambda item: item.order_index)[0]
        return InterviewSessionResponse(
            id=saved_interview.id,
            job_role=saved_interview.job_role,
            target_company=saved_interview.target_company,
            interview_round=saved_interview.interview_round,
            difficulty=saved_interview.difficulty,
            mode=saved_interview.mode,
            status=saved_interview.status,
            started_at=saved_interview.started_at,
            current_question_index=1,
            total_questions=saved_interview.total_questions,
            interviewer_message=first_question.question_text,
            current_question_id=first_question.id,
            ai_status="ai_generated" if first_question.source_question_id is None else "question_bank",
            history=[],
        )

    @staticmethod
    async def get_session(db: AsyncSession, interview_id: uuid.UUID, candidate_profile_id: uuid.UUID) -> InterviewSessionResponse:
        interview = await db.scalar(select(MockInterview).where(
            MockInterview.id == interview_id,
            MockInterview.candidate_profile_id == candidate_profile_id,
        ).options(selectinload(MockInterview.questions).selectinload(InterviewQuestion.response)))
        if not interview:
            raise HTTPException(status_code=404, detail="Mock interview not found")
        questions = sorted(interview.questions, key=lambda item: item.order_index)
        pending = next((item for item in questions if item.response is None), None)
        current = pending or questions[-1]
        return InterviewSessionResponse(
            id=interview.id,
            job_role=interview.job_role,
            target_company=interview.target_company,
            interview_round=interview.interview_round,
            difficulty=interview.difficulty,
            mode=interview.mode,
            status=interview.status,
            started_at=interview.started_at,
            current_question_index=current.order_index,
            total_questions=interview.total_questions,
            interviewer_message=current.question_text if pending else None,
            current_question_id=current.id if pending else None,
            ai_status="question_bank" if pending and current.source_question_id else "ai_generated" if pending else interview.evaluation_status,
            history=InterviewService._history(interview),
        )

    @staticmethod
    async def respond_to_question(
        db: AsyncSession,
        interview_id: uuid.UUID,
        candidate_profile_id: uuid.UUID,
        request: InterviewRespondRequest,
    ) -> Any:
        interview = await db.scalar(select(MockInterview).where(
            MockInterview.id == interview_id,
            MockInterview.candidate_profile_id == candidate_profile_id,
        ).options(
            selectinload(MockInterview.questions).selectinload(InterviewQuestion.response),
            selectinload(MockInterview.industry),
        ).with_for_update())
        if not interview:
            raise HTTPException(status_code=404, detail="Mock interview not found")
        if interview.status != InterviewStatus.IN_PROGRESS:
            raise HTTPException(status_code=409, detail="Mock interview is not active")
        if interview.started_at and (datetime.now(timezone.utc) - interview.started_at).total_seconds() >= interview.duration_minutes * 60:
            return await InterviewService.conclude_interview(db, interview_id, candidate_profile_id)

        questions = sorted(interview.questions, key=lambda item: item.order_index)
        current = next((item for item in questions if item.response is None), None)
        if current is None:
            return await InterviewService.conclude_interview(db, interview_id, candidate_profile_id)
        answer_text = request.candidate_answer.strip()
        if current.response is None:
            db.add(InterviewResponse(
                interview_question_id=current.id,
                candidate_answer=answer_text,
                duration_seconds=request.duration_seconds,
            ))
            await db.commit()
            # Reload the persisted transcript before external work.
            interview = await db.scalar(select(MockInterview).where(
                MockInterview.id == interview_id
            ).options(
                selectinload(MockInterview.questions).selectinload(InterviewQuestion.response),
                selectinload(MockInterview.industry),
            ).execution_options(populate_existing=True))
            questions = sorted(interview.questions, key=lambda item: item.order_index)
            current = questions[-1]
        else:
            # Retry generation from the saved answer; never create a duplicate response.
            answer_text = current.response.candidate_answer

        history = InterviewService._history(interview)
        next_pending = next((item for item in questions if item.response is None), None)
        if next_pending:
            return InterviewSessionResponse(
                id=interview.id, job_role=interview.job_role, target_company=interview.target_company,
                interview_round=interview.interview_round, difficulty=interview.difficulty, mode=interview.mode,
                status=interview.status, started_at=interview.started_at,
                current_question_index=next_pending.order_index, total_questions=interview.total_questions,
                interviewer_message=next_pending.question_text, current_question_id=next_pending.id,
                history=history,
                ai_status="question_bank" if next_pending.source_question_id else "ai_generated",
            )
        if len(questions) >= interview.total_questions:
            return await InterviewService.conclude_interview(db, interview_id, candidate_profile_id)

        provider = get_ai_provider()
        if not provider.is_available():
            return InterviewSessionResponse(
                id=interview.id, job_role=interview.job_role, target_company=interview.target_company,
                interview_round=interview.interview_round, difficulty=interview.difficulty, mode=interview.mode,
                status=interview.status, started_at=interview.started_at,
                current_question_index=len(questions), total_questions=interview.total_questions,
                interviewer_message=None, current_question_id=None, history=history, ai_status="unavailable",
            )

        prompt = PromptManager.get_interview_turn_prompt(
            role=interview.job_role,
            industry=interview.industry.name if interview.industry else "Not provided",
            target_company=None,  # Do not imply affiliation or invent company interview practices.
            round_type=interview.interview_round,
            question_index=len(questions) + 1,
            total_questions=interview.total_questions,
            history=history,
            last_answer=answer_text,
        )
        try:
            ai_response = await provider.generate_text(prompt=prompt, max_tokens=800)
            if not ai_response.is_success or not ai_response.raw_text:
                raise ValueError("No interviewer response was returned")
            turn, validation_error = ResponseValidator.validate_pydantic(ai_response.raw_text, InterviewTurn)
            if validation_error or turn is None:
                raise ValueError("Interviewer response was invalid")
            normalized = " ".join(turn.interviewer_message.split()).lower()
            if any(normalized == " ".join(item.question_text.split()).lower() for item in questions):
                raise ValueError("Interviewer returned a repeated question")
        except Exception:
            return InterviewSessionResponse(
                id=interview.id, job_role=interview.job_role, target_company=interview.target_company,
                interview_round=interview.interview_round, difficulty=interview.difficulty, mode=interview.mode,
                status=interview.status, started_at=interview.started_at,
                current_question_index=len(questions), total_questions=interview.total_questions,
                interviewer_message=None, current_question_id=None, history=history, ai_status="unavailable",
            )

        next_question = InterviewQuestion(
            mock_interview_id=interview.id,
            question_text=turn.interviewer_message,
            source_question_id=None,
            source_provenance="ai_generated",
            order_index=len(questions) + 1,
            is_follow_up=turn.is_follow_up,
            parent_question_id=current.id if turn.is_follow_up else None,
        )
        db.add(next_question)
        await db.commit()
        await db.refresh(next_question)
        return InterviewSessionResponse(
            id=interview.id, job_role=interview.job_role, target_company=interview.target_company,
            interview_round=interview.interview_round, difficulty=interview.difficulty, mode=interview.mode,
            status=interview.status, started_at=interview.started_at,
            current_question_index=next_question.order_index, total_questions=interview.total_questions,
            interviewer_message=next_question.question_text, current_question_id=next_question.id,
            history=history, ai_status="ai_generated",
        )

    @staticmethod
    async def conclude_interview(
        db: AsyncSession,
        interview_id: uuid.UUID,
        candidate_profile_id: uuid.UUID,
    ) -> InterviewReportResponse:
        interview = await db.scalar(select(MockInterview).where(
            MockInterview.id == interview_id,
            MockInterview.candidate_profile_id == candidate_profile_id,
        ).options(
            selectinload(MockInterview.questions).selectinload(InterviewQuestion.response),
            selectinload(MockInterview.evaluation),
            selectinload(MockInterview.industry),
        ).with_for_update())
        if not interview:
            raise HTTPException(status_code=404, detail="Mock interview not found")
        if interview.evaluation:
            return InterviewService._report(interview, interview.evaluation)

        interview.status = InterviewStatus.COMPLETED
        interview.completed_at = datetime.now(timezone.utc)
        transcript = [
            {"question": question.question_text, "answer": question.response.candidate_answer if question.response else ""}
            for question in sorted(interview.questions, key=lambda item: item.order_index)
        ]
        provider = get_ai_provider()
        evaluation_data = None
        if provider.is_available() and any(row["answer"] for row in transcript):
            prompt = PromptManager.get_interview_evaluation_prompt(
                role=interview.job_role,
                industry=interview.industry.name if interview.industry else "Not provided",
                target_company=None,
                round_type=interview.interview_round,
                transcript=transcript,
            )
            try:
                response = await provider.generate_text(prompt=prompt, max_tokens=2500)
                if response.is_success and response.raw_text:
                    evaluation_data, validation_error = ResponseValidator.validate_pydantic(response.raw_text, InterviewEvaluationOutput)
                    if validation_error:
                        evaluation_data = None
            except Exception:
                evaluation_data = None

        if evaluation_data:
            evaluation = InterviewEvaluation(
                mock_interview_id=interview.id,
                overall_score=evaluation_data.overall_score,
                technical_score=evaluation_data.technical_score,
                domain_score=evaluation_data.domain_score,
                communication_score=evaluation_data.communication_score,
                structure_score=evaluation_data.structure_score,
                evaluation_status="evaluated",
                evaluation_provenance="ai",
                key_strengths=evaluation_data.key_strengths,
                improvement_areas=evaluation_data.improvement_areas,
                detailed_feedback=evaluation_data.detailed_feedback,
                question_evaluations=evaluation_data.question_evaluations,
            )
            interview.evaluation_status = "evaluated"
        else:
            evaluation = InterviewEvaluation(
                mock_interview_id=interview.id,
                overall_score=None,
                technical_score=None,
                domain_score=None,
                communication_score=None,
                structure_score=None,
                evaluation_status="unavailable",
                evaluation_provenance="none",
                key_strengths=[], improvement_areas=[],
                detailed_feedback={"message": "Interview responses were saved. No evaluation score is available because AI evaluation is not configured or did not return validated output."},
                question_evaluations=[],
            )
            interview.evaluation_status = "unavailable"
        db.add(evaluation)
        await db.commit()
        await db.refresh(evaluation)
        return InterviewService._report(interview, evaluation)

    @staticmethod
    def _report(interview: MockInterview, evaluation: InterviewEvaluation) -> InterviewReportResponse:
        evaluations_by_question = {
            item.get("question_number"): item
            for item in (evaluation.question_evaluations or [])
            if isinstance(item, dict) and isinstance(item.get("question_number"), int)
        }
        responses = []
        for question_number, question in enumerate(sorted(interview.questions, key=lambda item: item.order_index), start=1):
            if not question.response:
                continue
            item = evaluations_by_question.get(question_number, {})
            refined_answer = item.get("refined_answer") if isinstance(item, dict) else None
            responses.append(InterviewResponseReview(
                question_number=question_number,
                question=question.question_text,
                candidate_answer=question.response.candidate_answer,
                refined_answer=refined_answer.strip() if isinstance(refined_answer, str) and refined_answer.strip() else None,
            ))
        return InterviewReportResponse(
            id=evaluation.id,
            mock_interview_id=interview.id,
            overall_score=evaluation.overall_score,
            technical_score=evaluation.technical_score,
            domain_score=evaluation.domain_score,
            communication_score=evaluation.communication_score,
            structure_score=evaluation.structure_score,
            evaluation_status=evaluation.evaluation_status,
            evaluation_provenance=evaluation.evaluation_provenance,
            key_strengths=evaluation.key_strengths,
            improvement_areas=evaluation.improvement_areas,
            detailed_feedback=evaluation.detailed_feedback,
            question_evaluations=evaluation.question_evaluations,
            responses=responses,
            completed_at=interview.completed_at,
        )

    @staticmethod
    async def get_report(db: AsyncSession, interview_id: uuid.UUID, candidate_profile_id: uuid.UUID) -> InterviewReportResponse:
        interview = await db.scalar(select(MockInterview).where(
            MockInterview.id == interview_id,
            MockInterview.candidate_profile_id == candidate_profile_id,
        ).options(
            selectinload(MockInterview.evaluation),
            selectinload(MockInterview.questions).selectinload(InterviewQuestion.response),
        ))
        if not interview or not interview.evaluation:
            raise HTTPException(status_code=404, detail="Interview report not found")
        return InterviewService._report(interview, interview.evaluation)

    @staticmethod
    async def get_history(db: AsyncSession, candidate_profile_id: uuid.UUID) -> List[MockInterview]:
        result = await db.scalars(select(MockInterview).where(
            MockInterview.candidate_profile_id == candidate_profile_id,
        ).order_by(MockInterview.created_at.desc()).limit(50))
        return list(result.all())
