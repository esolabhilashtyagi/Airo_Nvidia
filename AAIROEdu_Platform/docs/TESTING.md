# Testing Strategy & Execution Guide — Candidate Dashboard AAIRO

## Isolated database migrations

Run Alembic commands only through the repository wrapper. By default it targets `aairo_phase4_pytest`, derives the sync URL from the same async `DATABASE_URL`, prints both resolved URLs with passwords redacted, and sets the required `ALEMBIC_ALLOWED_DB` guard before invoking Alembic:

```sh
./scripts/migrate_test_db.sh current
./scripts/migrate_test_db.sh upgrade head
./scripts/migrate_test_db.sh check
```

The application root `.env` is never printed or used to select the migration target. To use another isolated test database, set both `AAIRO_TEST_DB_NAME` and `AAIRO_TEST_DATABASE_URL` to that test DB. The database name must match exactly. The guard in `backend/alembic/env.py` independently rejects an unset allowlist or a mismatched target before creating an engine. Do not use this wrapper for a development or production database.

## Password-reset email setup

SMTP also sends a welcome email after candidate registration and a separate profile-completion email when the newly-created profile is incomplete. These are best-effort background deliveries after the account transaction commits; an SMTP outage does not fail account creation. The profile email links to `/onboarding`. Password recovery uses a one-time, 30-minute reset link. Configure `SMTP_HOST`, `SMTP_FROM_EMAIL`, and the provider's `SMTP_USERNAME`/`SMTP_PASSWORD` in the backend environment; `SMTP_PORT=587` with `SMTP_STARTTLS=True` is the default. For an implicit-TLS relay set `SMTP_USE_SSL=True` and `SMTP_PORT=465`. Set `FRONTEND_BASE_URL` to the URL candidates use to open AAIRO (for Docker Compose, usually `http://localhost:3000`; for local Vite, `http://localhost:5173`). Restart the backend after changing settings. Do not commit provider credentials.

The reset-token table is introduced by migration `ba2026v8`; apply it only through `./scripts/migrate_test_db.sh upgrade head` on the isolated test DB, and use the deployment's reviewed migration process for other environments. Forgot-password requests are rate limited and return an account-enumeration-safe message. Reset tokens are stored as hashes, expire after 30 minutes, work once, and password reset revokes existing refresh sessions.

## Current backend-only acceptance checkpoint (2026-11-22)

- Current implementation adds an NVIDIA-compatible AI provider, mixed-PDF OCR, DOCX header/footer extraction, adaptive question context, profile-generated resume downloads, career-transition roadmaps, and real article/video search APIs. Coverage includes full unit, integration, and E2E suites.
- The current provider default is `AI_PROVIDER=nvidia`, model `nvidia/nemotron-3.5-lightning-30b-a3b`. Set `NVIDIA_API_KEY` for NVIDIA-hosted inference or point `NVIDIA_BASE_URL` to a compatible self-hosted endpoint. Never print keys. Provider integration tests use mocked HTTP; they do not prove live service availability.
- Video results require `YOUTUBE_API_KEY`; article results use OpenAlex and are ranked by citation counts. The authenticated API is `GET /api/v1/coach/resources?topic=<topic>`; it reports unavailable integrations rather than supplying sample links.
- `POST /api/v1/resumes/generate-from-profile` returns a DOCX based only on the signed-in candidate's saved profile. It currently has no frontend control because frontend files remain unchanged.
- The full backend DB-backed suite, Docker image build, and database persistence acceptance were not verified in the 2026-11-22 pass. The isolated test DB connection was blocked before reaching PostgreSQL; do not redirect these checks to the configured database.

## Quality Assurance Philosophy
We maintain multi-level automated testing to guarantee product stability, security, candidate data isolation, and resilient fallback execution.

---

## 1. Test Levels

### 1.1 Backend Unit & Integration Tests (Pytest)
- **Framework**: `pytest`, `pytest-asyncio`, `httpx` (ASGITransport test client).
- **Test Database**: Dedicated test PostgreSQL database or isolated transactional test session.
- **Coverage Domains**:
  1. `test_auth.py`: Registration, duplicate checks, login, invalid credentials, JWT expiry, role checks.
  2. `test_candidates.py`: Multi-step onboarding, education, experience, target companies, isolation between candidates.
  3. `test_resumes.py`: PostgreSQL API integration for real PDF/DOCX extraction, validation, candidate isolation, provider failures, schema-valid analysis, suggestion review/versioning, and deletion. ATS match-review GET/POST and the non-persisting job-description extraction route still need authenticated API coverage against the isolated DB.
  4. `test_resume_extraction.py`: Database-free real PNG/JPG OCR, multi-page image-based PDF OCR (including blank pages), corrupt/empty files, pixel/page limits, OCR failure handling, score weights, and suggestion grounding. Requires Tesseract and PyMuPDF.
  4. `test_questions.py`: Question taxonomy, filtering by industry/role/difficulty, bookmarking, practice logging, admin review workflow. These DB-backed checks still need a clean dedicated-database run for Phase 4 acceptance.
  5. `test_assessments.py`: Test generation, timer constraints, deterministic MCQ evaluation, auto-submission calculation, report statistics.
  6. `test_interviews.py`: Interview lifecycle (setup -> question progression -> submission -> rubric evaluation).
  7. `test_ai_provider.py`: Gemini client parsing, schema validation, fallback behavior when API key is missing or invalid.
  8. `test_security.py`: Cross-tenant data isolation (Candidate A cannot read Candidate B's resume or test results), SQL injection safety, path traversal prevention.

### 1.2 Frontend Unit & Component Tests (Vitest & React Testing Library)
- **Framework**: `vitest`, `@testing-library/react`, `@testing-library/user-event`, `jsdom`.
- **Coverage Domains**:
  1. Auth forms: Form validation (email formats, password rules), submit states.
  2. Onboarding wizard: Step navigation, conditional field rendering (Fresher vs Experienced), payload submission.
  3. Resume library/detail: Upload validation and progress, status/error display, parsed-data correction, analysis-unavailable state, suggestion review, and version history.
  4. Testing interface: Timer ticking, question navigation, option selection, submit confirmation dialog.
  5. Dashboard analytics: Render with empty states and loaded states.

### 1.3 End-to-End User Journeys (Playwright)
- **Journey A (Onboarding & Activation)**: Register -> Login -> Complete 7-step Onboarding -> Land on Dashboard with personalized recommendations.
- **Journey B (Resume Intelligence)**: Upload resume -> Trigger Analysis -> Inspect category scores -> Review & accept suggestions.
- **Journey C (AI Coach & Roadmap)**: Open Coach -> Request Skill Gap Analysis -> Generate Roadmap -> Complete first task.
- **Journey D (Centralized Question Bank)**: Filter questions by Banking / Healthcare / IT -> Bookmark question -> Practice question and review explanation.
- **Journey E (Testing Mode)**: Configure test -> Answer MCQs and descriptive question -> Submit -> Verify instant calculation of score and topic breakdown.
- **Journey F (AI Mock Interview)**: Configure Interview -> Answer interview questions -> Conclude interview -> Verify comprehensive evaluation report.
- **Journey G (Admin Governance)**: Admin login -> Create custom industry & job role -> Create new question -> Approve AI-generated content.

The Playwright suite currently at `frontend/e2e/resume.spec.ts` exercises the Phase 3 resume journey: UI registration and PDF upload, parsed-data correction, validation/drag-and-drop/retry, AI success or unavailable states, suggestion acceptance when Gemini returns suggestions, logout/login persistence, cross-candidate access, responsive widths, and upload throttling. Run `npm run test:e2e`; it starts the API against a separate `aairo_phase3_e2e` database, applies migrations, and uses temporary upload storage. The database is created if absent and is never dropped/reset. This suite does not yet satisfy Phase 4 question-bank/module journey coverage.

Phase 4 has a focused backend schema test at `backend/tests/test_question_schemas.py`; the question and module integration tests require PostgreSQL. Add and run a dedicated Playwright journey for candidate question practice, answer-key reveal timing, admin review, module enrollment, and lesson progress before Phase 4 acceptance.

Verification run on 2026-11-18: the complete backend suite passed **29 tests** against a new, isolated PostgreSQL database (`aairo_phase4_pytest`) with test-only seed fixtures. Frontend Vitest passed **2 tests**, and the Playwright resume suite passed **8 tests with 1 Gemini-dependent test skipped** against its separate E2E database. This is useful regression evidence but does not yet cover the full Phase 4 admin and candidate journeys described above.

---

## 2. Test Execution Commands

### Running Backend Tests
```bash
cd backend
source venv/bin/activate
pytest -v --tb=short
```

### Running Frontend Tests
```bash
cd frontend
npm run test
npm run build
npm run lint
npm run test:e2e
```

### Running Integration & Health Checks
```bash
python backend/tests/run_e2e_workflows.py
```
