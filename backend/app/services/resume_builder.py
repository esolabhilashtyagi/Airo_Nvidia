"""Professional, fact-preserving DOCX resume templates from a saved profile."""

import io
import re
from typing import Any, Literal

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor

ResumeTemplate = Literal["modern", "classic", "compact"]
TEMPLATES: dict[str, dict[str, Any]] = {
    "modern": {"accent": "5B21B6", "ink": "172554", "font": "Arial", "name_size": 25, "top": 0.62, "bottom": 0.62, "section_before": 10, "section_after": 4, "center": False},
    "classic": {"accent": "17365D", "ink": "1F2937", "font": "Georgia", "name_size": 22, "top": 0.72, "bottom": 0.72, "section_before": 12, "section_after": 5, "center": True},
    "compact": {"accent": "0F766E", "ink": "1F2937", "font": "Arial", "name_size": 20, "top": 0.45, "bottom": 0.45, "section_before": 7, "section_after": 3, "center": False},
}


def build_profile_resume_docx(user: Any, profile: Any, template: ResumeTemplate = "modern") -> bytes:
    """Build a styled DOCX using only saved profile fields and user-written text."""
    if template not in TEMPLATES:
        raise ValueError("Choose the modern, classic, or compact resume template.")
    style = TEMPLATES[template]
    education = list(profile.education_history or [])
    experience = list(profile.experience_history or [])
    skills = list(dict.fromkeys(str(skill).strip() for skill in (profile.key_skills or []) if str(skill).strip()))
    objective = (profile.career_goals or "").strip()
    if not (education or experience or skills or objective):
        raise ValueError("Add education, experience, skills, or a career objective to your profile before generating a resume.")

    document = Document()
    section = document.sections[0]
    section.top_margin = Inches(style["top"])
    section.bottom_margin = Inches(style["bottom"])
    section.left_margin = Inches(0.78)
    section.right_margin = Inches(0.78)
    normal = document.styles["Normal"]
    normal.font.name = style["font"]
    normal.font.size = Pt(9.5 if template != "compact" else 9)
    normal.font.color.rgb = RGBColor.from_string("374151")
    normal.paragraph_format.space_after = Pt(3)
    normal.paragraph_format.line_spacing = 1.08
    heading_style = document.styles["Heading 1"]
    heading_style.font.name = style["font"]
    heading_style.font.size = Pt(11 if template != "compact" else 10)
    heading_style.font.bold = True
    heading_style.font.color.rgb = RGBColor.from_string(style["accent"])
    heading_style.paragraph_format.keep_with_next = True

    name = (getattr(user, "full_name", None) or "Candidate").strip()
    alignment = WD_ALIGN_PARAGRAPH.CENTER if style["center"] else WD_ALIGN_PARAGRAPH.LEFT
    title = document.add_paragraph()
    title.alignment = alignment
    title.paragraph_format.space_after = Pt(2)
    name_run = title.add_run(name)
    name_run.bold = True
    name_run.font.name = style["font"]
    name_run.font.size = Pt(style["name_size"])
    name_run.font.color.rgb = RGBColor.from_string(style["ink"])

    target_role = (profile.target_role or "").strip()
    if target_role:
        role = document.add_paragraph()
        role.alignment = alignment
        role.paragraph_format.space_after = Pt(4)
        role_run = role.add_run(target_role)
        role_run.bold = template == "modern"
        role_run.font.size = Pt(9 if template == "compact" else 10)
        role_run.font.color.rgb = RGBColor.from_string(style["accent"])

    contact = [value.strip() for value in (getattr(user, "email", None),) if isinstance(value, str) and value.strip()]
    if contact:
        contact_line = document.add_paragraph("  ·  ".join(contact))
        contact_line.alignment = alignment
        contact_line.paragraph_format.space_after = Pt(8)
        for run in contact_line.runs:
            run.font.size = Pt(9 if template != "compact" else 8.5)
            run.font.color.rgb = RGBColor.from_string("64748B")

    def add_heading(label: str) -> None:
        paragraph = document.add_heading(label, level=1)
        paragraph.paragraph_format.space_before = Pt(style["section_before"])
        paragraph.paragraph_format.space_after = Pt(style["section_after"])

    def add_description(text: str) -> None:
        for line in text.splitlines():
            content = line.strip()
            if not content:
                continue
            if re.match(r"^(?:[-*•]|\d+[.)])\s+", content):
                paragraph = document.add_paragraph(style="List Bullet")
                paragraph.paragraph_format.space_after = Pt(2)
                paragraph.add_run(re.sub(r"^(?:[-*•]|\d+[.)])\s+", "", content))
            else:
                paragraph = document.add_paragraph(content)
                paragraph.paragraph_format.space_after = Pt(3)

    if objective:
        add_heading("Career Objective")
        add_description(objective)

    if skills:
        add_heading("Skills")
        paragraph = document.add_paragraph("  ·  ".join(skills))
        paragraph.paragraph_format.space_after = Pt(2)

    if experience:
        add_heading("Experience" if getattr(profile, "candidate_type", None) == "student_fresher" else "Professional Experience")
        for item in experience:
            job_title = (item.job_title or "").strip()
            company = (item.company_name or "").strip()
            heading = document.add_paragraph()
            heading.paragraph_format.keep_with_next = bool((item.description or "").strip())
            heading.paragraph_format.space_after = Pt(1)
            main = " — ".join(part for part in (job_title, company) if part)
            run = heading.add_run(main)
            run.bold = True
            run.font.color.rgb = RGBColor.from_string(style["ink"])
            dates = " – ".join(str(value).strip() for value in (item.start_date, item.end_date or ("Present" if item.is_current else None)) if value and str(value).strip())
            if dates:
                meta = document.add_paragraph(dates)
                meta.paragraph_format.space_after = Pt(2)
                for meta_run in meta.runs:
                    meta_run.italic = True
                    meta_run.font.size = Pt(8.5)
                    meta_run.font.color.rgb = RGBColor.from_string("64748B")
            add_description((item.description or "").strip())

    if education:
        add_heading("Education")
        for item in education:
            qualification = " — ".join(str(part).strip() for part in (item.degree, item.field_of_study) if part and str(part).strip())
            institution = (item.institution or "").strip()
            years = " – ".join(str(year) for year in (item.start_year, item.end_year or ("Present" if item.is_current else None)) if year)
            details = " · ".join(part for part in (institution, years) if part)
            paragraph = document.add_paragraph()
            paragraph.paragraph_format.space_after = Pt(1)
            first = paragraph.add_run(qualification or institution)
            first.bold = True
            first.font.color.rgb = RGBColor.from_string(style["ink"])
            if details and details != qualification and details != institution:
                meta = document.add_paragraph(details)
                meta.paragraph_format.space_after = Pt(2)
                for run in meta.runs:
                    run.font.size = Pt(8.5)
                    run.font.color.rgb = RGBColor.from_string("64748B")
            if item.grade:
                document.add_paragraph(f"Grade: {item.grade.strip()}")

    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def safe_resume_filename(full_name: str, template: str = "modern") -> str:
    stem = re.sub(r"[^A-Za-z0-9_-]+", "_", full_name).strip("_") or "candidate"
    template_suffix = template if template in TEMPLATES else "resume"
    return f"{stem[:72]}_{template_suffix}_resume.docx"
