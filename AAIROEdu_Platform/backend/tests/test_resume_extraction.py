"""Local file extraction tests that require no database or personal documents."""
import io

import fitz
import pytest
from fastapi import HTTPException
from PIL import Image, ImageDraw, ImageFont
from docx import Document

from app.services.resume_service import (
    AIResumeAnalysis,
    AIResumeSuggestion,
    ExtractionUnavailable,
    ResumeService,
    ScoreCategories,
)


def resume_image(text: str, size: tuple[int, int] = (1400, 420), image_format: str = "PNG") -> bytes:
    image = Image.new("RGB", size, "white")
    ImageDraw.Draw(image).multiline_text(
        (45, 40), text, fill="black", font=ImageFont.load_default(size=48), spacing=18
    )
    buffer = io.BytesIO()
    image.save(buffer, format=image_format, quality=95)
    return buffer.getvalue()


def scanned_pdf(page_text: list[str]) -> bytes:
    document = fitz.open()
    for text in page_text:
        page = document.new_page(width=612, height=792)
        if text:
            page.insert_image(fitz.Rect(35, 100, 577, 280), stream=resume_image(text))
    output = document.tobytes()
    document.close()
    return output


@pytest.mark.parametrize(
    ("image_format", "mime_type", "size", "expected_email"),
    [
        ("PNG", "image/png", (1400, 420), "casey.rivera@example.com"),
        ("JPEG", "image/jpeg", (1000, 300), "morgan.taylor@example.com"),
    ],
)
def test_real_png_and_jpg_ocr(image_format, mime_type, size, expected_email):
    text = f"Candidate Example\nEmail: {expected_email}\nSkills: Python PostgreSQL"
    extracted = ResumeService.extract_text(resume_image(text, size, image_format), mime_type)
    assert expected_email in extracted
    assert "Python" in extracted


def test_real_scanned_pdf_renders_each_page_and_skips_blank_page():
    pdf = scanned_pdf([
        "Avery Morgan\nEmail: avery.morgan@example.com\nSkills: Python",
        "",
        "Experience: Built reliable test workflows",
    ])
    extracted = ResumeService.extract_text(pdf, "application/pdf")
    assert "avery.morgan@example.com" in extracted
    assert "reliable test workflows" in extracted


def test_mixed_pdf_extracts_text_pages_and_ocr_pages(monkeypatch):
    document = fitz.open()
    text_page = document.new_page(width=612, height=792)
    text_page.insert_text((40, 80), "Candidate: Riley Morgan\nExperience: Backend Engineer")
    scanned_page = document.new_page(width=612, height=792)
    scanned_page.insert_image(fitz.Rect(35, 100, 577, 280), stream=resume_image("scanned page"))
    pdf = document.tobytes()
    document.close()
    ocr_calls = []
    monkeypatch.setattr(ResumeService, "_ocr_image", lambda image: ocr_calls.append(image.size) or "Scanned certification details")

    extracted = ResumeService.extract_text(pdf, "application/pdf")

    assert "Candidate: Riley Morgan" in extracted
    assert "Backend Engineer" in extracted
    assert "Scanned certification details" in extracted
    assert len(ocr_calls) == 1


def test_docx_extracts_header_and_footer_content():
    document = Document()
    document.sections[0].header.paragraphs[0].text = "Riley Morgan | riley@example.com"
    document.add_paragraph("Professional Experience")
    document.sections[0].footer.paragraphs[0].text = "Portfolio: https://example.com"
    content = io.BytesIO()
    document.save(content)

    extracted = ResumeService.extract_text(
        content.getvalue(),
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

    assert "Riley Morgan | riley@example.com" in extracted
    assert "Professional Experience" in extracted
    assert "Portfolio: https://example.com" in extracted


def test_empty_images_and_blank_scanned_pdf_are_rejected():
    with pytest.raises(ValueError, match="No readable text"):
        ResumeService.extract_text(resume_image("", size=(900, 300)), "image/png")
    with pytest.raises(ValueError, match="No readable text"):
        ResumeService.extract_text(scanned_pdf([""]), "application/pdf")


def test_corrupt_pdf_and_pdf_page_limit_are_rejected(monkeypatch):
    with pytest.raises(ValueError, match="corrupted"):
        ResumeService.extract_text(b"%PDF-1.4\nnot a valid PDF", "application/pdf")

    monkeypatch.setattr(ResumeService, "MAX_PDF_PAGES", 1)
    with pytest.raises(ValueError, match="100-page"):
        ResumeService.extract_text(scanned_pdf(["First page", "Second page"]), "application/pdf")


def test_image_dimension_limit_and_tesseract_failure(monkeypatch):
    monkeypatch.setattr(ResumeService, "MAX_IMAGE_PIXELS", 1000)
    with pytest.raises(ValueError, match="dimensions"):
        ResumeService.extract_text(resume_image("Large", (100, 100)), "image/png")

    monkeypatch.setattr(ResumeService, "MAX_IMAGE_PIXELS", 40_000_000)
    monkeypatch.setattr("app.services.resume_service.pytesseract.image_to_string", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("test failure")))
    with pytest.raises(ExtractionUnavailable, match="OCR could not read"):
        ResumeService.extract_text(resume_image("OCR failure"), "image/png")


def test_weighted_resume_rubric_and_grounded_suggestions():
    assert sum(ResumeService.CATEGORY_WEIGHTS.values()) == pytest.approx(1.0)
    source = "Built reliable test suites 2022 - 2024 with Python"
    safe = AIResumeAnalysis(
        category_scores=ScoreCategories(**{key: 50 for key in ResumeService.CATEGORY_WEIGHTS}),
        strengths=["Resume contains a dated testing example"],
        weaknesses=[],
        missing_keywords=[],
        improvement_opportunities=[],
        scoring_explanation="The rubric scores each listed category from source evidence.",
        suggestions=[AIResumeSuggestion(
            category="Experience",
            original_text="Built reliable test suites",
            suggested_text="Reliable test suites were built",
            reason="Reorders the source wording.",
            supporting_context="Built reliable test suites 2022 - 2024 with Python",
        )],
    )
    verified, rejected = ResumeService._validate_suggestions(safe, source)
    assert verified == safe.suggestions
    assert rejected == 0
    assert round(sum(safe.category_scores.model_dump()[key] * weight for key, weight in ResumeService.CATEGORY_WEIGHTS.items()), 2) == 50

    unsafe = safe.model_copy(deep=True)
    unsafe.suggestions[0].suggested_text = "Built reliable test suites with Kubernetes"
    verified, rejected = ResumeService._validate_suggestions(unsafe, source)
    assert verified == []
    assert rejected == 1

    unsafe.suggestions[0].suggested_text = "Built reliable test suites and improved coverage by 80%"
    verified, rejected = ResumeService._validate_suggestions(unsafe, source)
    assert verified == []
    assert rejected == 1

    safe_and_unsafe = safe.model_copy(deep=True)
    safe_and_unsafe.suggestions.append(unsafe.suggestions[0])
    verified, rejected = ResumeService._validate_suggestions(safe_and_unsafe, source)
    assert verified == [safe_and_unsafe.suggestions[0]]
    assert rejected == 1

    assert ResumeService._all_extracted_text_is_grounded({"graduation_year": 2024}, source)
    assert not ResumeService._all_extracted_text_is_grounded({"graduation_year": 2030}, source)


def test_candidate_edited_enhancement_cannot_add_unsupported_facts_or_metrics():
    source = "Built reliable test suites 2022 - 2024 with Python"
    assert ResumeService._rewrite_is_grounded("Built reliable Python test suites", source)
    assert not ResumeService._rewrite_is_grounded("Built reliable Kubernetes test suites", source)
    assert not ResumeService._rewrite_is_grounded("Built reliable test suites with 80% coverage", source)


def test_candidate_edited_enhancement_allows_spacing_cleanup_around_existing_metric():
    source = "reduced user onboarding friction by60%through redesigned flows."
    rewrite = "reduced user onboarding friction by 60% through redesigned flows."
    assert ResumeService._rewrite_is_grounded(rewrite, source)
    assert not ResumeService._rewrite_is_grounded(
        "reduced user onboarding friction by 80% through redesigned flows.", source
    )


def test_ai_suggestion_source_quotes_tolerate_pdf_spacing_without_weakening_evidence():
    source = "Experience\nReduced user onboarding friction by60%through redesigned flows."
    analysis = AIResumeAnalysis(
        category_scores=ScoreCategories(**{key: 50 for key in ResumeService.CATEGORY_WEIGHTS}),
        strengths=["The resume documents an onboarding outcome."],
        weaknesses=[], missing_keywords=[], improvement_opportunities=[],
        scoring_explanation="The rubric uses only the supplied resume.",
        suggestions=[AIResumeSuggestion(
            category="Experience",
            original_text="Reduced user onboarding friction by 60% through redesigned flows.",
            suggested_text="Reduced user onboarding friction by 60% through redesigned flows.",
            reason="Restores spacing around the measured result.",
            supporting_context="Reduced user onboarding friction by 60% through redesigned flows.",
        )],
    )

    verified, rejected = ResumeService._validate_suggestions(analysis, source)
    assert verified == analysis.suggestions
    assert rejected == 0

    unsupported = analysis.model_copy(deep=True)
    unsupported.suggestions[0].supporting_context = "Reduced user onboarding friction by 60% through a new platform."
    verified, rejected = ResumeService._validate_suggestions(unsupported, source)
    assert verified == []
    assert rejected == 1

    unsupported.suggestions[0].supporting_context = "Reduced user onboarding friction by 80% through redesigned flows."
    verified, rejected = ResumeService._validate_suggestions(unsupported, source)
    assert verified == []
    assert rejected == 1


def test_parser_preserves_nontechnical_skills_and_common_section_headings():
    parsed = ResumeService.parse_resume_text(
        "Riley Morgan\nEmail: riley@example.com\n"
        "Professional Experience\nHR Generalist | Example Org\nJan 2021 - Present\n"
        "Managed employee relations and onboarding\n"
        "Skills: Talent Acquisition, Employee Relations; Payroll\n"
        "Academic Qualifications\nBA Psychology, Example College 2020\n"
        "Publications\nPeople operations research\n"
        "Professional Summary\nSeeking an HR leadership role"
    )
    assert {"Talent Acquisition", "Employee Relations", "Payroll"}.issubset(parsed["skills"])
    assert parsed["experience"]
    assert "Managed employee relations and onboarding" in parsed["experience"][0]["responsibilities"]
    assert parsed["education"][0]["graduation_year"] == 2020
    assert parsed["publications"] == ["People operations research"]
    assert "Seeking an HR leadership role" not in parsed["publications"]


def test_parser_does_not_mistake_employment_years_for_phone_number():
    parsed = ResumeService.parse_resume_text(
        "Riley Morgan\nExperience\n2020 - 2024\n2024 - 2025\nSkills\nPython"
    )
    assert "phone" not in parsed["contact_info"]


def test_parser_preserves_skill_capitalization_and_name_from_contact_line():
    parsed = ResumeService.parse_resume_text(
        "Riley Morgan | riley@example.com\nPhone: +91 98765 43210\n"
        "Skills\nAWS, PostgreSQL, JavaScript, C++, Power BI"
    )
    assert parsed["contact_info"]["full_name"] == "Riley Morgan"
    assert parsed["contact_info"]["phone"] == "+91 98765 43210"
    assert {"AWS", "PostgreSQL", "JavaScript", "C++", "Power BI"}.issubset(parsed["skills"])


def test_docx_preserves_interleaved_tables_and_places_contact_header_first():
    document = Document()
    document.sections[0].header.paragraphs[0].text = "Riley Morgan | riley@example.com"
    document.add_paragraph("Education")
    document.add_table(rows=1, cols=1).cell(0, 0).text = "BA Psychology, Example College 2020"
    document.add_paragraph("Experience")
    document.add_table(rows=1, cols=1).cell(0, 0).text = "HR Generalist | Example Org | 2021 - Present"
    document.add_paragraph("Skills")
    document.add_paragraph("Talent Acquisition, Payroll")
    content = io.BytesIO()
    document.save(content)

    extracted = ResumeService.extract_text(
        content.getvalue(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert extracted.startswith("Riley Morgan")
    assert extracted.index("BA Psychology") < extracted.index("Experience")
    assert extracted.index("HR Generalist") < extracted.index("Skills")


@pytest.mark.asyncio
async def test_ai_extraction_accepts_category_labels_not_present_in_source(monkeypatch):
    from app.integrations.ai.base import AIResponse

    class Provider:
        def is_available(self):
            return True

        async def generate_structured(self, **kwargs):
            return AIResponse(
                provider_name="test-provider", is_success=True,
                structured_data={"skills": ["Python"], "skill_categories": {"Programming Languages": ["Python"]}},
            )

    monkeypatch.setattr("app.services.resume_service.get_ai_provider", lambda: Provider())
    parsed = {"skills": [], "skill_categories": {}, "contact_info": {}}
    enriched = await ResumeService.enrich_extraction(parsed, "Riley Morgan\nPython")
    assert enriched["skills"] == ["Python"]
    assert enriched["skill_categories"] == {"Programming Languages": ["Python"]}


@pytest.mark.asyncio
async def test_ai_extraction_retains_grounded_fields_when_one_field_is_hallucinated(monkeypatch):
    from app.integrations.ai.base import AIResponse

    class Provider:
        def is_available(self):
            return True

        async def generate_structured(self, **kwargs):
            return AIResponse(provider_name="test-provider", structured_data={
                "contact_info": {"full_name": "Riley Morgan", "location": "Invented City"},
                "experience": [{"job_title": "HR Generalist", "employer": "Example Org"}],
                "skills": ["Payroll", "Invented skill"],
            })

    monkeypatch.setattr("app.services.resume_service.get_ai_provider", lambda: Provider())
    source = "Riley Morgan\nHR Generalist\nExample Org\nPayroll"
    enriched = await ResumeService.enrich_extraction(ResumeService.parse_resume_text(source), source)
    assert enriched["experience"] == [{"job_title": "HR Generalist", "employer": "Example Org"}]
    assert "Invented City" not in str(enriched)
    assert "Invented skill" not in enriched["skills"]
    assert "Payroll" in enriched["skills"]


def test_ocr_has_a_subprocess_timeout(monkeypatch):
    calls = []
    monkeypatch.setattr("app.services.resume_service.shutil.which", lambda _: "/test/tesseract")
    monkeypatch.setattr(
        "app.services.resume_service.pytesseract.image_to_string",
        lambda image, **kwargs: calls.append(kwargs) or "Riley Morgan",
    )
    with Image.new("RGB", (100, 100)) as image:
        assert ResumeService._ocr_image(image) == "Riley Morgan"
    assert 0 < calls[0]["timeout"] <= 60


def test_accepted_enhancement_replaces_only_one_matching_source_excerpt():
    assert ResumeService._replace_unique_source_excerpt(
        "Experience\nBuilt reliable test suites\nEducation", "Built reliable test suites", "Built reliable Python test suites"
    ) == "Experience\nBuilt reliable Python test suites\nEducation"
    with pytest.raises(HTTPException) as error:
        ResumeService._replace_unique_source_excerpt(
            "Built reliable test suites\nBuilt reliable test suites", "Built reliable test suites", "Built reliable Python test suites"
        )
    assert error.value.status_code == 409
