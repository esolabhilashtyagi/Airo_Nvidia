"""Professional, fact-preserving DOCX resume templates from a saved profile."""

import io
import re
from typing import Any, Literal

try:
    import fitz
except (ImportError, Exception):
    fitz = None
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


def build_profile_resume_pdf(user: Any, profile: Any, template: ResumeTemplate = "modern") -> bytes:
    """Create a clean, single-column, ATS-friendly PDF from saved profile data."""
    if fitz is None:
        raise ValueError("PDF resume generation requires PyMuPDF (fitz) runtime support.")
    if template not in TEMPLATES:
        raise ValueError("Choose the modern, classic, or compact resume template.")
    education = list(profile.education_history or [])
    experience = list(profile.experience_history or [])
    skills = list(dict.fromkeys(str(skill).strip() for skill in (profile.key_skills or []) if str(skill).strip()))
    objective = (profile.career_goals or "").strip()
    if not (education or experience or skills or objective):
        raise ValueError("Add education, experience, skills, or a career objective to your profile before generating a resume.")

    style = TEMPLATES[template]
    accent_hex = style["accent"]
    ink_hex = style["ink"]

    def color(value: str) -> tuple[float, float, float]:
        return tuple(int(value[index:index + 2], 16) / 255 for index in (0, 2, 4))

    accent, ink = color(accent_hex), color(ink_hex)
    left = 42 if template == "compact" else 52
    right = 42 if template == "compact" else 52
    top = 40 if template == "compact" else 48
    bottom = 42
    page_width, page_height = fitz.paper_size("a4")
    body_size = 8.7 if template == "compact" else 9.4
    line_height = body_size * 1.42
    doc = fitz.open()
    page = doc.new_page(width=page_width, height=page_height)
    y = top

    def clean(text: Any) -> str:
        # Standard PDF fonts support Windows-1252. Replace unsupported glyphs
        # predictably rather than letting one profile character break export.
        return str(text).replace("\u2011", "-").replace("\u2022", "•").encode("cp1252", "replace").decode("cp1252")

    def new_page() -> None:
        nonlocal page, y
        page = doc.new_page(width=page_width, height=page_height)
        y = top

    def ensure_room(height: float) -> None:
        if y + height > page_height - bottom:
            new_page()

    def wrap(text: str, size: float, bold: bool = False, max_width: float | None = None) -> list[str]:
        text = clean(text).strip()
        if not text:
            return []
        font = fitz.Font("hebo" if bold else "helv")
        width = max_width or (page_width - left - right)
        lines: list[str] = []
        current = ""
        for word in text.split():
            if font.text_length(word, fontsize=size) > width:
                if current:
                    lines.append(current)
                    current = ""
                piece = ""
                for character in word:
                    if piece and font.text_length(piece + character, fontsize=size) > width:
                        lines.append(piece)
                        piece = character
                    else:
                        piece += character
                current = piece
                continue
            candidate = f"{current} {word}".strip()
            if current and font.text_length(candidate, fontsize=size) > width:
                lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            lines.append(current)
        return lines

    def text_block(text: str, size: float = body_size, ink_color: tuple[float, float, float] = (0.20, 0.25, 0.33), bold: bool = False, gap: float = 2.5, align: int = 0) -> None:
        nonlocal y
        lines = wrap(text, size, bold)
        if not lines:
            return
        for index, line in enumerate(lines):
            ensure_room(size * 1.35 + (gap if index == len(lines) - 1 else 0))
            font_name = "hebo" if bold else "helv"
            font = fitz.Font(font_name)
            text_x = (page_width - font.text_length(line, fontsize=size)) / 2 if align == 1 else left
            page.insert_text((text_x, y + size), line, fontname=font_name, fontsize=size, color=ink_color)
            y += size * 1.35
        y += gap

    name = clean(getattr(user, "full_name", None) or "Candidate").strip()
    centered = template == "classic"
    name_size = 20 if template == "compact" else (22 if centered else 25)
    name_font = fitz.Font("hebo")
    while name_size > 14 and name_font.text_length(name, fontsize=name_size) > page_width - left - right:
        name_size -= 1
    name_width = name_font.text_length(name, fontsize=name_size)
    name_x = (page_width - name_width) / 2 if centered else left
    page.insert_text((name_x, y + name_size), name, fontname="hebo", fontsize=name_size, color=ink)
    y += name_size + 4
    target_role = (profile.target_role or "").strip()
    email = (getattr(user, "email", None) or "").strip()
    header_items = [item for item in (target_role, email) if item]
    for item in header_items:
        text_block(item, size=9 if template != "compact" else 8.3, ink_color=accent if item == target_role else (0.39, 0.44, 0.52), bold=(item == target_role), gap=1.2, align=1 if centered else 0)
    y += 4
    page.draw_line((left, y), (page_width - right, y), color=accent, width=2 if template == "modern" else 1.2)
    y += 10

    def section(title: str) -> None:
        nonlocal y
        ensure_room(25)
        y += 4 if template == "compact" else 7
        page.insert_text((left, y + 10), clean(title.upper()), fontname="hebo", fontsize=9.5 if template != "compact" else 8.8, color=accent)
        y += 14
        page.draw_line((left, y), (page_width - right, y), color=(0.83, 0.86, 0.90), width=0.55)
        y += 5

    def description(text: str) -> None:
        nonlocal y
        for source_line in text.splitlines():
            line = source_line.strip()
            if not line:
                continue
            bullet = bool(re.match(r"^(?:[-*•]|\d+[.)])\s+", line))
            if bullet:
                line = re.sub(r"^(?:[-*•]|\d+[.)])\s+", "", line)
            available_width = page_width - left - right - (12 if bullet else 0)
            lines = wrap(line, body_size, max_width=available_width)
            for index, wrapped in enumerate(lines):
                ensure_room(line_height + (2 if index == len(lines) - 1 else 0))
                prefix = "• " if bullet and index == 0 else ("  " if bullet else "")
                page.insert_text((left, y + body_size), prefix + wrapped, fontname="helv", fontsize=body_size, color=(0.20, 0.25, 0.33))
                y += line_height
            y += 2

    if objective:
        section("Career Objective")
        description(objective)
    if skills:
        section("Skills")
        description("  ·  ".join(skills))
    if experience:
        section("Experience" if getattr(profile, "candidate_type", None) == "student_fresher" else "Professional Experience")
        for item in experience:
            title = " — ".join(part.strip() for part in (item.job_title or "", item.company_name or "") if part and part.strip())
            if title:
                text_block(title, size=body_size + 0.2, ink_color=ink, bold=True, gap=1)
            dates = " – ".join(str(value).strip() for value in (item.start_date, item.end_date or ("Present" if item.is_current else None)) if value and str(value).strip())
            if dates:
                text_block(dates, size=body_size - 0.5, ink_color=(0.39, 0.44, 0.52), gap=1)
            description((item.description or "").strip())
            y += 3
    if education:
        section("Education")
        for item in education:
            qualification = " — ".join(str(part).strip() for part in (item.degree, item.field_of_study) if part and str(part).strip())
            institution = (item.institution or "").strip()
            years = " – ".join(str(year) for year in (item.start_year, item.end_year or ("Present" if item.is_current else None)) if year)
            text_block(qualification or institution, size=body_size + 0.2, ink_color=ink, bold=True, gap=1)
            details = " · ".join(part for part in (institution, years) if part)
            if details and details not in (qualification, institution):
                text_block(details, size=body_size - 0.5, ink_color=(0.39, 0.44, 0.52), gap=1)
            if item.grade:
                text_block(f"Grade: {item.grade.strip()}", size=body_size - 0.5, gap=2)

    for page_number, output_page in enumerate(doc, start=1):
        output_page.draw_line((left, page_height - 28), (page_width - right, page_height - 28), color=(0.87, 0.89, 0.92), width=0.5)
        output_page.insert_text((page_width - right - 48, page_height - 15), f"{page_number}", fontname="helv", fontsize=8, color=(0.43, 0.47, 0.54))
    content = doc.tobytes(garbage=4, deflate=True)
    doc.close()
    return content


def safe_resume_filename(full_name: str, template: str = "modern", file_format: str = "docx") -> str:
    stem = re.sub(r"[^A-Za-z0-9_-]+", "_", full_name).strip("_") or "candidate"
    template_suffix = template if template in TEMPLATES else "resume"
    extension = file_format if file_format in {"pdf", "docx"} else "docx"
    return f"{stem[:72]}_{template_suffix}_resume.{extension}"
