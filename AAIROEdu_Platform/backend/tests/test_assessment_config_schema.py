import uuid

import pytest
from pydantic import ValidationError

from app.schemas.assessment import AssessmentConfigureRequest


def test_assessment_marks_accept_only_whole_values():
    base = {"industry_id": uuid.uuid4()}
    request = AssessmentConfigureRequest(
        **base, num_questions=12, marks_per_question=5, negative_marking_points=2,
    )
    assert request.num_questions == 12
    assert request.marks_per_question == 5
    assert request.negative_marking_points == 2

    with pytest.raises(ValidationError):
        AssessmentConfigureRequest(**base, marks_per_question=5.5)
    with pytest.raises(ValidationError):
        AssessmentConfigureRequest(**base, negative_marking_points=0.25)


def test_assessment_taxonomy_fields_normalize_empty_input_and_deduplicate_topics():
    unfiltered = AssessmentConfigureRequest(industry_id=uuid.uuid4())
    assert unfiltered.subject is None
    assert unfiltered.topic is None

    request = AssessmentConfigureRequest(
        industry_id=uuid.uuid4(), subject="   ", topic="", topics=[" Systems ", "systems", "  "],
    )

    assert request.subject is None
    assert request.topic is None
    assert request.topics == ["Systems"]


def test_assessment_taxonomy_labels_respect_database_column_length():
    base = {"industry_id": uuid.uuid4()}
    with pytest.raises(ValidationError):
        AssessmentConfigureRequest(**base, subject="x" * 256)
    with pytest.raises(ValidationError):
        AssessmentConfigureRequest(**base, topics=["x" * 256])


def test_assessment_response_reports_ai_generated_question_count():
    from app.schemas.assessment import AssessmentResponse

    response = AssessmentResponse(
        id=uuid.uuid4(),
        title="Practice assessment",
        industry_id=uuid.uuid4(),
        difficulty="Mixed",
        duration_minutes=20,
        total_questions=5,
        passing_percentage=65,
        ai_generated_question_count=3,
    )

    assert response.ai_generated_question_count == 3


@pytest.mark.parametrize("payload", [
    {"selected_options": ["A", " a "]},
    {"selected_options": [""]},
    {"selected_options": ["   "]},
    {"selected_options": ["A"], "text_response": "Also a text answer"},
])
def test_saved_answer_rejects_duplicate_blank_or_mixed_shape(payload):
    from app.schemas.assessment import CandidateAnswerSaveRequest

    with pytest.raises(ValidationError):
        CandidateAnswerSaveRequest(question_id=uuid.uuid4(), **payload)


def test_saved_answer_normalizes_ids_and_blank_text_without_changing_code():
    from app.schemas.assessment import CandidateAnswerSaveRequest

    answer = CandidateAnswerSaveRequest(question_id=uuid.uuid4(), selected_options=[" a "], text_response="  ")
    assert answer.selected_options == ["a"]
    assert answer.text_response is None
    code = "  def example():\n      return 1\n"
    assert CandidateAnswerSaveRequest(question_id=uuid.uuid4(), text_response=code).text_response == code
