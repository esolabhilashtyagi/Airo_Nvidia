import uuid

import pytest
from pydantic import ValidationError

from app.models.question import ApprovalStatus, QuestionType, SourceProvenance
from app.schemas.question import QuestionCreate


def choice_payload():
    return {
        "question_text": "Which response is correct?",
        "question_type": QuestionType.MCQ_SINGLE,
        "industry_id": uuid.uuid4(),
        "subject": "General",
        "topic": "Foundations",
        "options": [
            {"id": "A", "text": "First", "is_correct": True},
            {"id": "B", "text": "Second", "is_correct": False},
        ],
        "expected_answer": "A",
        "source_provenance": SourceProvenance.AI_GENERATED,
    }


def test_new_questions_enter_review_and_do_not_claim_verified_provenance():
    question = QuestionCreate.model_validate(choice_payload())
    assert question.approval_status == ApprovalStatus.PENDING
    assert question.source_provenance == SourceProvenance.AI_GENERATED


@pytest.mark.parametrize("options", [[], [{"id": "A", "text": "Only"}], [
    {"id": "A", "text": "First", "is_correct": False},
    {"id": "B", "text": "Second", "is_correct": False},
]])
def test_single_choice_requires_two_options_and_exactly_one_answer(options):
    payload = choice_payload()
    payload["options"] = options
    with pytest.raises(ValidationError):
        QuestionCreate.model_validate(payload)


def test_multiple_choice_requires_unique_nonempty_option_ids():
    payload = choice_payload()
    payload["question_type"] = QuestionType.MCQ_MULTIPLE
    payload["options"] = [
        {"id": "A", "text": "First", "is_correct": True},
        {"id": "a", "text": "Duplicate", "is_correct": True},
    ]
    with pytest.raises(ValidationError):
        QuestionCreate.model_validate(payload)
