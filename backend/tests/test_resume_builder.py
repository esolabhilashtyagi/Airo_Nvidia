import io
from types import SimpleNamespace

import pytest
try:
    import fitz
except (ImportError, Exception):
    fitz = None
from docx import Document

from app.services.resume_builder import build_profile_resume_docx, build_profile_resume_pdf, safe_resume_filename


def test_profile_resume_contains_only_saved_candidate_fields():
    user = SimpleNamespace(full_name="Riley Morgan", email="riley@example.com")
    profile = SimpleNamespace(
        education_history=[SimpleNamespace(
            degree="Bachelor of Arts", field_of_study="Psychology", institution="State University",
            start_year=2018, end_year=2022, is_current=False, grade="Honors",
        )],
        experience_history=[SimpleNamespace(
            job_title="Software Engineer", company_name="Example Labs", start_date="2022-01",
            end_date=None, is_current=True, description="Built internal tools for the support team.",
        )],
        key_skills=["Python", "People analytics"],
        career_goals="Transition into people operations using my technical background.",
        target_role="HR Generalist", current_role="Software Engineer",
        current_company="Example Labs",
        total_experience_months=51,
    )

    generated = build_profile_resume_docx(user, profile)
    document = Document(io.BytesIO(generated))
    content = "\n".join(paragraph.text for paragraph in document.paragraphs)

    assert "Riley Morgan" in content
    assert "riley@example.com" in content
    assert "HR Generalist" in content
    assert "Software Engineer — Example Labs" in content
    assert "Built internal tools for the support team." in content
    assert "Career Objective" in content
    assert "Professional Summary" not in content
    assert "Psychology" in content and "State University" in content
    assert "People analytics" in content
    assert "improved revenue" not in content


def test_profile_resume_requires_user_provided_content():
    user = SimpleNamespace(full_name="Candidate", email="candidate@example.com")
    profile = SimpleNamespace(
        education_history=[], experience_history=[], key_skills=[], career_goals="",
        target_role=None, current_role=None, total_experience_months=0,
    )

    with pytest.raises(ValueError, match="Add education, experience, skills"):
        build_profile_resume_docx(user, profile)


def test_profile_resume_does_not_invent_a_professional_summary():
    user = SimpleNamespace(full_name="Riley Morgan", email="riley@example.com")
    profile = SimpleNamespace(
        education_history=[], experience_history=[], key_skills=["SQL"], career_goals="",
        target_role="HR Analyst", current_role="Software Engineer", total_experience_months=30,
    )

    document = Document(io.BytesIO(build_profile_resume_docx(user, profile)))
    content = "\n".join(paragraph.text for paragraph in document.paragraphs)

    assert "Professional Summary" not in content
    assert "Currently listed as" not in content
    assert "2 years 6 months" not in content
    assert "Self-reported skills include" not in content
    assert "HR Analyst" in content
    assert "SQL" in content


def test_resume_filename_is_safe_for_download_header():
    assert safe_resume_filename('Riley Morgan / "QA"') == "Riley_Morgan_QA_modern_resume.docx"
    assert safe_resume_filename("Riley Morgan", "classic", "pdf") == "Riley_Morgan_classic_resume.pdf"


@pytest.mark.skipif(fitz is None, reason="PyMuPDF runtime unavailable in local environment")
@pytest.mark.parametrize("template", ["modern", "classic", "compact"])
def test_profile_resume_pdf_is_valid_and_uses_only_saved_candidate_fields(template):
    user = SimpleNamespace(full_name="Riley Morgan", email="riley@example.com")
    profile = SimpleNamespace(
        education_history=[SimpleNamespace(
            degree="Bachelor of Arts", field_of_study="Psychology", institution="State University",
            start_year=2018, end_year=2022, is_current=False, grade="Honors",
        )],
        experience_history=[SimpleNamespace(
            job_title="Software Engineer", company_name="Example Labs", start_date="2022-01",
            end_date=None, is_current=True, description="Built internal tools for the support team.",
        )],
        key_skills=["Python", "People analytics"],
        career_goals="Transition into people operations using my technical background.",
        target_role="HR Generalist", candidate_type="working_professional",
    )

    generated = build_profile_resume_pdf(user, profile, template)
    document = fitz.open(stream=generated, filetype="pdf")
    content = "\n".join(page.get_text() for page in document)

    assert document.page_count >= 1
    assert "Riley Morgan" in content
    assert "riley@example.com" in content
    assert "HR Generalist" in content
    assert "Built internal tools for the support team." in content
    assert "Psychology" in content and "State University" in content
    assert "People analytics" in content
    assert "improved revenue" not in content
    document.close()


@pytest.mark.parametrize("template", ["modern", "classic", "compact"])
def test_profile_resume_templates_are_valid_distinct_docx_layouts(template):
    user = SimpleNamespace(full_name="Riley Morgan", email="riley@example.com")
    profile = SimpleNamespace(
        education_history=[], experience_history=[], key_skills=["Python", "SQL"], career_goals="",
        target_role="Data Analyst", current_role=None, current_company=None, total_experience_months=0,
    )
    document = Document(io.BytesIO(build_profile_resume_docx(user, profile, template)))
    content = "\n".join(paragraph.text for paragraph in document.paragraphs)
    assert "Riley Morgan" in content
    assert "Data Analyst" in content
    assert "Python" in content and "SQL" in content
    assert document.paragraphs[0].runs[0].font.color.rgb is not None


def test_invalid_profile_resume_template_is_rejected():
    user = SimpleNamespace(full_name="Riley Morgan", email="riley@example.com")
    profile = SimpleNamespace(education_history=[], experience_history=[], key_skills=["Python"], career_goals="")
    with pytest.raises(ValueError, match="modern, classic, or compact"):
        build_profile_resume_docx(user, profile, "unsupported")

