import io
import uuid
from pathlib import Path

import pytest
from docx import Document
from httpx import AsyncClient
from PIL import Image, ImageDraw, ImageFont
import fitz

from app.core.config import settings


def make_pdf(text: str) -> bytes:
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET".encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    document = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(document))
        document.extend(f"{number} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref_offset = len(document)
    document.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    document.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        document.extend(f"{offset:010} 00000 n \n".encode())
    document.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode())
    return bytes(document)


def make_docx(text: str) -> bytes:
    document = Document()
    for line in text.splitlines():
        document.add_paragraph(line)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def make_resume_image(text: str, size: tuple[int, int] = (1400, 420), fmt: str = "PNG") -> bytes:
    image = Image.new("RGB", size, "white")
    font = ImageFont.load_default(size=48)
    ImageDraw.Draw(image).multiline_text((45, 40), text, fill="black", font=font, spacing=18)
    buffer = io.BytesIO()
    image.save(buffer, format=fmt, quality=95)
    return buffer.getvalue()


def make_scanned_pdf(pages: list[str]) -> bytes:
    document = fitz.open()
    for text in pages:
        page = document.new_page(width=612, height=792)
        if text:
            page.insert_image(fitz.Rect(35, 100, 577, 280), stream=make_resume_image(text, size=(1400, 420)))
    result = document.tobytes()
    document.close()
    return result


async def create_candidate(async_client: AsyncClient) -> dict[str, str]:
    email = f"resume_{uuid.uuid4().hex[:10]}@aairo.ai"
    password = "ResumeTestPassword123!"
    response = await async_client.post("/api/v1/auth/register", json={"email": email, "password": password, "full_name": "Resume Test"})
    assert response.status_code == 201
    login = await async_client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['data']['access_token']}"}


def use_upload_directory(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))


@pytest.mark.asyncio
async def test_valid_pdf_and_docx_extraction_and_duplicate_detection(async_client: AsyncClient, monkeypatch, tmp_path: Path):
    use_upload_directory(monkeypatch, tmp_path)
    headers = await create_candidate(async_client)
    pdf_text = "Taylor Candidate\nEmail: taylor@example.com\nSkills\nPython, PostgreSQL\nExperience\nBuilt reporting tools 2022 - 2024\n- Built reliable test suites"

    pdf = await async_client.post("/api/v1/resumes/upload", headers=headers, files={"file": ("candidate.pdf", make_pdf(pdf_text), "application/pdf")})
    assert pdf.status_code == 201, pdf.text
    pdf_data = pdf.json()["data"]
    assert pdf_data["parsing_status"] == "extracted"
    assert pdf_data["parsed_data"]["contact_info"]["email"] == "taylor@example.com"
    assert "Python" in pdf_data["parsed_data"]["skills"]
    assert "file_path" not in pdf_data
    resume_id = pdf_data["id"]

    detail = await async_client.get(f"/api/v1/resumes/{resume_id}", headers=headers)
    assert detail.status_code == 200
    assert "Built reliable test suites" in detail.json()["data"]["raw_text"]
    assert len(detail.json()["data"]["versions"]) == 1

    duplicate = await async_client.post("/api/v1/resumes/upload", headers=headers, files={"file": ("duplicate.pdf", make_pdf(pdf_text), "application/pdf")})
    assert duplicate.status_code == 409

    docx_text = "Morgan Example\nEmail: morgan@example.com\nEducation\nBSc Biology, Example University 2025"
    docx = await async_client.post("/api/v1/resumes/upload", headers=headers, files={"file": ("candidate.docx", make_docx(docx_text), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")})
    assert docx.status_code == 201, docx.text
    assert docx.json()["data"]["parsing_status"] == "extracted"
    docx_detail = await async_client.get(f"/api/v1/resumes/{docx.json()['data']['id']}", headers=headers)
    assert docx_detail.status_code == 200
    assert docx_detail.json()["data"]["parsed_data"]["education"][0]["graduation_year"] == 2025


@pytest.mark.asyncio
async def test_profile_generated_resume_download_uses_only_authenticated_profile(async_client, monkeypatch):
    owner = await create_candidate(async_client)
    other = await create_candidate(async_client)
    unauthorized = await async_client.post("/api/v1/resumes/generate-from-profile")
    assert unauthorized.status_code == 401
    empty = await async_client.post("/api/v1/resumes/generate-from-profile", headers=owner)
    assert empty.status_code == 422
    updated = await async_client.post(
        "/api/v1/candidates/onboarding/step", headers=owner,
        json={"step": 5, "key_skills": ["Payroll", "Employee Relations"]},
    )
    assert updated.status_code == 200, updated.text
    response = await async_client.post("/api/v1/resumes/generate-from-profile", headers=owner)
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    assert "attachment; filename=" in response.headers["content-disposition"]
    content = "\n".join(paragraph.text for paragraph in Document(io.BytesIO(response.content)).paragraphs)
    assert "Payroll" in content and "Employee Relations" in content
    other_response = await async_client.post("/api/v1/resumes/generate-from-profile", headers=other)
    assert other_response.status_code == 422


@pytest.mark.asyncio
async def test_signatures_formats_and_oversize(async_client: AsyncClient, monkeypatch, tmp_path: Path):
    use_upload_directory(monkeypatch, tmp_path)
    headers = await create_candidate(async_client)

    disguised = await async_client.post("/api/v1/resumes/upload", headers=headers, files={"file": ("fake.pdf", b"plain text pretending to be a PDF", "application/pdf")})
    assert disguised.status_code == 400
    legacy_doc = await async_client.post("/api/v1/resumes/upload", headers=headers, files={"file": ("legacy.doc", b"anything", "application/msword")})
    assert legacy_doc.status_code == 415
    mismatch = await async_client.post("/api/v1/resumes/upload", headers=headers, files={"file": ("wrong.docx", make_pdf("not a docx"), "application/pdf")})
    assert mismatch.status_code == 400

    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_BYTES", 8)
    oversized = await async_client.post("/api/v1/resumes/upload", headers=headers, files={"file": ("large.pdf", b"%PDF-1.4" + b"x", "application/pdf")})
    assert oversized.status_code == 413
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_BYTES", 15 * 1024 * 1024)



@pytest.mark.asyncio
async def test_png_and_jpg_ocr_persist_real_text(async_client: AsyncClient, monkeypatch, tmp_path: Path):
    use_upload_directory(monkeypatch, tmp_path)
    headers = await create_candidate(async_client)
    samples = [
        ("resume.png", "PNG", (1400, 420), "Casey Rivera\nEmail: casey.rivera@example.com\nSkills: Python PostgreSQL"),
        ("resume.jpg", "JPEG", (1000, 300), "Morgan Taylor\nEmail: morgan.taylor@example.com\nSkills: JavaScript Docker"),
    ]
    for index, (filename, image_format, size, source) in enumerate(samples, start=1):
        mime = "image/png" if image_format == "PNG" else "image/jpeg"
        uploaded = await async_client.post(
            "/api/v1/resumes/upload", headers=headers,
            files={"file": (filename, make_resume_image(source, size=size, fmt=image_format), mime)},
        )
        assert uploaded.status_code == 201, uploaded.text
        data = uploaded.json()["data"]
        assert data["parsing_status"] == "extracted", data.get("extraction_error")
        detail = await async_client.get(f"/api/v1/resumes/{data['id']}", headers=headers)
        raw_text = detail.json()["data"]["raw_text"]
        assert "Email" in raw_text
        assert "@example.com" in raw_text
        assert data["parsed_data"]["contact_info"]["email"] in raw_text
        assert len(list(tmp_path.iterdir())) == index


@pytest.mark.asyncio
async def test_scanned_pdf_mult_page_ocr_with_empty_page(async_client: AsyncClient, monkeypatch, tmp_path: Path):
    use_upload_directory(monkeypatch, tmp_path)
    headers = await create_candidate(async_client)
    upload = await async_client.post(
        "/api/v1/resumes/upload", headers=headers,
        files={"file": ("scanned.pdf", make_scanned_pdf([
            "\n".join(["Avery Morgan", "Email: avery.morgan@example.com", "Skills: Python"]),
            "",
            "Experience: Built reliable test workflows",
        ]), "application/pdf")},
    )
    assert upload.status_code == 201, upload.text
    resume = upload.json()["data"]
    assert resume["parsing_status"] == "extracted", resume.get("extraction_error")
    detail = await async_client.get(f"/api/v1/resumes/{resume['id']}", headers=headers)
    raw_text = detail.json()["data"]["raw_text"]
    assert "avery.morgan@example.com" in raw_text
    assert "reliable test workflows" in raw_text


@pytest.mark.asyncio
async def test_ocr_failures_empty_invalid_oversized_and_pdf_page_limit(async_client: AsyncClient, monkeypatch, tmp_path: Path):
    from app.services.resume_service import ResumeService

    use_upload_directory(monkeypatch, tmp_path)
    headers = await create_candidate(async_client)

    empty_png = await async_client.post(
        "/api/v1/resumes/upload", headers=headers,
        files={"file": ("empty.png", make_resume_image("", size=(900, 300)), "image/png")},
    )
    assert empty_png.status_code == 201
    assert empty_png.json()["data"]["parsing_status"] == "extraction_failed"
    assert "No readable text" in empty_png.json()["data"]["extraction_error"]

    corrupt_image = await async_client.post(
        "/api/v1/resumes/upload", headers=headers,
        files={"file": ("broken.png", bytes.fromhex("89504e470d0a1a0a") + b"not-an-image", "image/png")},
    )
    assert corrupt_image.status_code == 400

    monkeypatch.setattr(ResumeService, "MAX_IMAGE_PIXELS", 1000)
    oversized_image = await async_client.post(
        "/api/v1/resumes/upload", headers=headers,
        files={"file": ("large.png", make_resume_image("Large image", size=(100, 100)), "image/png")},
    )
    assert oversized_image.status_code == 201
    assert oversized_image.json()["data"]["parsing_status"] == "extraction_failed"
    assert "dimensions" in oversized_image.json()["data"]["extraction_error"]
    monkeypatch.setattr(ResumeService, "MAX_IMAGE_PIXELS", 40_000_000)

    monkeypatch.setattr("app.services.resume_service.pytesseract.image_to_string", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("ocr failure")))
    failed_ocr = await async_client.post(
        "/api/v1/resumes/upload", headers=headers,
        files={"file": ("ocr-error.png", make_resume_image("OCR failure test"), "image/png")},
    )
    assert failed_ocr.status_code == 201
    assert failed_ocr.json()["data"]["parsing_status"] == "extraction_failed"
    assert "OCR could not read" in failed_ocr.json()["data"]["extraction_error"]

    corrupted_pdf = await async_client.post(
        "/api/v1/resumes/upload", headers=headers,
        files={"file": ("corrupt.pdf", b"%PDF-1.4\\nnot a document", "application/pdf")},
    )
    assert corrupted_pdf.status_code == 201
    assert corrupted_pdf.json()["data"]["parsing_status"] == "extraction_failed"

    monkeypatch.setattr(ResumeService, "MAX_PDF_PAGES", 1)
    too_many_pages = await async_client.post(
        "/api/v1/resumes/upload", headers=headers,
        files={"file": ("many-pages.pdf", make_scanned_pdf(["First page text", "Second page text"]), "application/pdf")},
    )
    assert too_many_pages.status_code == 201
    assert too_many_pages.json()["data"]["parsing_status"] == "extraction_failed"
    assert "100-page" in too_many_pages.json()["data"]["extraction_error"]


@pytest.mark.asyncio
async def test_edit_version_analysis_failure_and_retry(async_client: AsyncClient, monkeypatch, tmp_path: Path):
    use_upload_directory(monkeypatch, tmp_path)
    headers = await create_candidate(async_client)
    text = "Jordan Sample\nEmail: jordan@example.com\nExperience\nBuilt quality tools 2021 - 2023"
    upload = await async_client.post("/api/v1/resumes/upload", headers=headers, files={"file": ("jordan.pdf", make_pdf(text), "application/pdf")})
    resume_id = upload.json()["data"]["id"]

    detail = (await async_client.get(f"/api/v1/resumes/{resume_id}", headers=headers)).json()["data"]
    corrected = detail["parsed_data"]
    corrected["contact_info"]["full_name"] = "Jordan A. Sample"
    saved = await async_client.put(f"/api/v1/resumes/{resume_id}/parsed-data", headers=headers, json={"parsed_data": corrected})
    assert saved.status_code == 200
    assert len(saved.json()["data"]["versions"]) == 2

    class OfflineProvider:
        def is_available(self):
            return False

    monkeypatch.setattr("app.services.resume_service.get_ai_provider", lambda: OfflineProvider())
    unavailable = await async_client.post(f"/api/v1/resumes/{resume_id}/analyze", headers=headers)
    assert unavailable.status_code == 503
    assert "not configured" in unavailable.json()["error"]["message"].lower()
    after_failure = await async_client.get(f"/api/v1/resumes/{resume_id}", headers=headers)
    assert after_failure.json()["data"]["analysis_status"] == "analysis_failed"
    assert after_failure.json()["data"]["latest_analysis"] is None

    retry = await async_client.post(f"/api/v1/resumes/{resume_id}/extract", headers=headers)
    assert retry.status_code == 200
    assert retry.json()["data"]["parsing_status"] == "extracted"


@pytest.mark.asyncio
async def test_malformed_analysis_output_is_persisted_as_failed(async_client: AsyncClient, monkeypatch, tmp_path: Path):
    use_upload_directory(monkeypatch, tmp_path)
    headers = await create_candidate(async_client)
    upload = await async_client.post(
        "/api/v1/resumes/upload", headers=headers,
        files={"file": ("malformed.pdf", make_pdf("Casey Example\nSkills\nPython"), "application/pdf")},
    )
    resume_id = upload.json()["data"]["id"]

    class MalformedProvider:
        def is_available(self):
            return True

        async def generate_structured(self, **kwargs):
            return type("Response", (), {
                "is_success": True,
                "provider_name": "test-provider",
                "structured_data": {"category_scores": {"completeness": 150}},
            })()

    monkeypatch.setattr("app.services.resume_service.get_ai_provider", lambda: MalformedProvider())
    result = await async_client.post(f"/api/v1/resumes/{resume_id}/analyze", headers=headers)
    assert result.status_code == 503
    assert "unavailable" in result.json()["error"]["message"].lower()
    assert "invalid response" in result.json()["error"]["message"].lower()
    detail = await async_client.get(f"/api/v1/resumes/{resume_id}", headers=headers)
    assert detail.json()["data"]["analysis_status"] == "analysis_failed"
    assert detail.json()["data"]["latest_analysis"]["status"] == "analysis_failed"
    assert detail.json()["data"]["latest_analysis"]["analysis_provider"] is None


@pytest.mark.asyncio
async def test_analysis_suggestion_actions_versions_and_candidate_isolation(async_client: AsyncClient, monkeypatch, tmp_path: Path):
    use_upload_directory(monkeypatch, tmp_path)
    owner_headers = await create_candidate(async_client)
    other_headers = await create_candidate(async_client)
    text = "Riley Candidate\nEmail: riley@example.com\nSkills: Python\nExperience\nBuilt reliable test suites 2022 - 2024"
    upload = await async_client.post("/api/v1/resumes/upload", headers=owner_headers, files={"file": ("riley.pdf", make_pdf(text), "application/pdf")})
    resume_id = upload.json()["data"]["id"]

    class TestProvider:
        def is_available(self):
            return True

        async def generate_structured(self, **kwargs):
            return type("Response", (), {
                "is_success": True,
                "provider_name": "test-provider",
                "structured_data": {
                    "category_scores": {key: 60 for key in (
                        "completeness", "professional_summary", "skills_relevance", "experience_presentation",
                        "project_quality", "achievement_descriptions", "education_relevance", "formatting",
                        "target_role_alignment", "industry_relevance",
                    )},
                    "strengths": ["Resume includes a contact email"],
                    "weaknesses": ["No project section was found"],
                    "missing_keywords": ["project documentation"],
                    "improvement_opportunities": ["Add a verified project entry if applicable"],
                    "scoring_explanation": "Category scores use the documented weighted rubric.",
                    "suggestions": [
                        {"category": "Experience", "original_text": "Built reliable test suites", "suggested_text": "Built test suites that were reliable", "reason": "Reorders the existing claim without adding a metric.", "supporting_context": "Built reliable test suites"},
                        {"category": "Experience", "original_text": "Built reliable test suites", "suggested_text": "Reliable test suites were built", "reason": "Offers a passive-voice alternative.", "supporting_context": "Built reliable test suites"},
                    ],
                },
            })()

    monkeypatch.setattr("app.services.resume_service.get_ai_provider", lambda: TestProvider())
    analyzed = await async_client.post(f"/api/v1/resumes/{resume_id}/analyze", headers=owner_headers)
    assert analyzed.status_code == 200, analyzed.text
    analysis = analyzed.json()["data"]
    assert analysis["overall_score"] == 60
    assert analysis["analysis_provider"] == "test-provider"
    assert len(analysis["suggestions"]) == 2
    suggestion_id = analysis["suggestions"][0]["id"]

    unauthorized = await async_client.get(f"/api/v1/resumes/{resume_id}", headers=other_headers)
    assert unauthorized.status_code == 404
    unauthorized_action = await async_client.post(f"/api/v1/resumes/suggestions/{suggestion_id}/action", headers=other_headers, json={"action": "accept"})
    assert unauthorized_action.status_code == 404
    unauthorized_delete = await async_client.delete(f"/api/v1/resumes/{resume_id}", headers=other_headers)
    assert unauthorized_delete.status_code == 404

    unsupported_edit = await async_client.post(
        f"/api/v1/resumes/suggestions/{suggestion_id}/action", headers=owner_headers,
        json={"action": "accept", "edited_text": "Built reliable Kubernetes test suites with 80% coverage"},
    )
    assert unsupported_edit.status_code == 422

    accepted = await async_client.post(
        f"/api/v1/resumes/suggestions/{suggestion_id}/action", headers=owner_headers,
        json={"action": "accept", "edited_text": "Built reliable Python test suites"},
    )
    assert accepted.status_code == 200
    assert accepted.json()["data"]["status"] == "accepted"
    updated_resume = await async_client.get(f"/api/v1/resumes/{resume_id}", headers=owner_headers)
    assert "Built reliable Python test suites" in updated_resume.json()["data"]["parsed_data"]["enhanced_text"]
    versions = await async_client.get(f"/api/v1/resumes/{resume_id}/versions", headers=owner_headers)
    assert versions.status_code == 200
    assert len(versions.json()["data"]) == 2
    assert versions.json()["data"][1]["content"]["accepted_suggestions"][0]["suggested_text"] == "Built reliable Python test suites"
    assert "Built reliable Python test suites" in versions.json()["data"][1]["content"]["enhanced_text"]

    rejected = await async_client.post(
        f"/api/v1/resumes/suggestions/{analysis['suggestions'][1]['id']}/action", headers=owner_headers,
        json={"action": "reject"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["data"]["status"] == "rejected"
    duplicate_action = await async_client.post(f"/api/v1/resumes/suggestions/{suggestion_id}/action", headers=owner_headers, json={"action": "accept"})
    assert duplicate_action.status_code == 409

    deleted = await async_client.delete(f"/api/v1/resumes/{resume_id}", headers=owner_headers)
    assert deleted.status_code == 204
    owner_lookup_after_delete = await async_client.get(f"/api/v1/resumes/{resume_id}", headers=owner_headers)
    assert owner_lookup_after_delete.status_code == 404
    assert len(list(tmp_path.iterdir())) == 0
