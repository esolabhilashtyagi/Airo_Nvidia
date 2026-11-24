# API Design Documentation — Candidate Dashboard AAIRO

All API endpoints are versioned under `/api/v1` and return standardized JSON envelopes.

---

## Standard JSON Response Envelope

### Success Response
```json
{
  "success": true,
  "data": { ... },
  "message": "Operation completed successfully",
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 150
  }
}
```

### Error Response
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Target company name cannot be blank",
    "details": [
      { "field": "name", "issue": "String should have at least 1 character" }
    ]
  },
  "request_id": "req_8f1b209c"
}
```

---

## Endpoint Specification by Module

### 1. Authentication (`/api/v1/auth`)
- `POST /register`: Candidate registration (`email`, `password`, `full_name`).
- `POST /login`: OAuth2 password request form / JSON credentials -> returns access & refresh tokens.
- `POST /refresh`: Issues a new access token given a valid refresh token.
- `POST /logout`: Invalidate refresh token.
- `GET /me`: Returns current user profile, role, and candidate profile linkage.
- `POST /forgot-password`: Requests password reset email link/token.
- `POST /reset-password`: Resets password using token.

### 2. Candidate Onboarding & Profile (`/api/v1/candidates`)
- `GET /profile`: Get comprehensive profile details.
- `PUT /profile`: Update profile information.
- `POST /onboarding/step`: Save multi-step onboarding progress.
- `GET /onboarding/status`: Retrieve current onboarding step and completion status.
- `POST /education`: Add educational qualification record.
- `DELETE /education/{id}`: Delete educational record.
- `POST /experience`: Add work experience record.
- `DELETE /experience/{id}`: Delete work experience record.
- `POST /target-companies`: Add target companies and target job roles.

### 3. Taxonomy & Industries (`/api/v1/industries`)
- `GET /`: List all active industries with category and role counts.
- `GET /{id}`: Retrieve industry details with child categories and job roles.
- `GET /{id}/job-roles`: List job roles for an industry.

### 4. Resume Intelligence (`/api/v1/resumes`)
- `POST /job-description/extract`: Authenticated extraction of a PDF, DOCX, or UTF-8 TXT job description (15 MB file limit; 80–12,000 extracted characters). The source file is not persisted.
- `POST /upload`: Multipart PDF/DOCX/PNG/JPG/JPEG upload. Validates signature, extension, MIME, size, and duplicate content; returns extraction status.
- `GET /`: List current candidate's resumes.
- `GET /{id}`: Retrieve candidate-owned parsed data, raw extracted text, status, and versions.
- `POST /{id}/extract`: Retry local text extraction.
- `PUT /{id}/parsed-data`: Save candidate corrections as a new version.
- `GET /{id}/versions`: List saved versions.
- `POST /{id}/analyze` and `POST /{id}/enhance`: Run structured Gemini analysis; unavailable provider or invalid grounded output returns an error and never fabricates scores.
- `GET /{id}/analysis`: Retrieve latest analysis and suggestions, or `null` if none.
- `POST /suggestions/{suggestion_id}/action`: Accept (optionally edited) or reject a candidate-owned suggestion. Acceptance creates a version.
- `DELETE /{id}`: Remove candidate-owned resume and stored file.
- `POST /{id}/ats-review`: Save a deterministic job-description match estimate (`job_title`, `job_description`, 80–12,000 chars).
- `GET /{id}/ats-review`: Retrieve the latest estimate for the candidate-owned resume.
- `POST /{id}/analyze` and `/enhance` accept the optional same job payload for job-targeted AI suggestions; the job description is context, never evidence about candidate skills.

Image OCR requires Tesseract; scanned-PDF OCR additionally requires PyMuPDF. Analysis requires configured Gemini.

Resume APIs use candidate-scoped PostgreSQL fixed-window throttles. Defaults: upload 20/hour, extraction retry 20/hour, analysis/enhancement 5/hour. The settings `RESUME_UPLOAD_RATE_LIMIT`, `RESUME_UPLOAD_RATE_WINDOW_SECONDS`, `RESUME_EXTRACTION_RATE_LIMIT`, `RESUME_EXTRACTION_RATE_WINDOW_SECONDS`, `RESUME_AI_RATE_LIMIT`, and `RESUME_AI_RATE_WINDOW_SECONDS` control these limits. HTTP 429 responses include `Retry-After`. Apply the current Alembic head before using these routes.

The ATS estimate compares up to 40 terms extracted from the supplied posting and five common section headings. Its transparent formula is 85% term coverage + 15% section coverage. It is a deterministic estimate based on extracted text, not an official vendor score or recruiter outcome. Missing terms are not candidate claims; only add them when accurate. Persisted reviews are scoped through their resume foreign key and are deleted with the resume.

### 5. Centralized Question Bank (`/api/v1/questions`)
- `GET /`: Candidate-visible approved, non-archived question search (currently implemented industry, role, type, difficulty, search, and pagination filters).
- `GET /{id}`: Candidate question content without answer key, explanation, or MCQ correctness flags.
- `POST /{id}/bookmark`: Bookmark/unbookmark a candidate-visible question.
- `GET /bookmarks`: List the candidate's bookmarks.
- `POST /{id}/practice`: Persist an answer. Objective answers are deterministically graded; subjective AI evaluation is labeled by status/provenance and has no score when provider output is unavailable or invalid. The answer key is returned only after submission.
- `/manage`: Role-gated content-manager/admin list, create (pending), edit (returns changed content to pending review), review (approve/reject), and archive operations.

### 6. Learning Modules (`/api/v1/modules`)
- `GET /`: List published modules for the candidate's industry.
- `GET /roadmap/active`: Retrieve the active roadmap before the dynamic module-id route.
- `GET /{id}`: Retrieve published, in-industry module detail and persisted lesson completion IDs.
- `POST /{id}/start`: Enroll / start module.
- `POST /{id}/lessons/{lesson_id}/complete`: Mark lesson completed.


### 7. AI Career Coach (`/api/v1/coach`)
- `GET /skill-gap`: Evidence-based skill gap analysis comparing profile against target role.
- `POST /roadmap/generate`: Generate personalized milestone roadmap based on candidate data.
- `GET /roadmap`: Retrieve active roadmap and task completion status.
- `POST /roadmap/tasks/{task_id}/toggle`: Mark roadmap task completed.
- `GET /conversations`: List coach chat history.
- `POST /chat`: Send message to AI Career Coach (returns streaming or JSON response with guidance and practice suggestions).

### 8. Testing Mode (`/api/v1/testing`)
- `POST /assessments/configure`: Generate customized timed test based on candidate preferences.
- `POST /assessments/{id}/start`: Initialize assessment attempt and activate countdown timer.
- `POST /attempts/{attempt_id}/save-answer`: Auto-save candidate answer for a question.
- `POST /attempts/{attempt_id}/submit`: Conclude test, trigger deterministic + AI grading, return final score.
- `GET /attempts/{attempt_id}/results`: View comprehensive assessment report.
- `GET /history`: List user's past assessment attempts.

### 9. AI Mock Interviews (`/api/v1/interviews`)
- `POST /setup`: Configure mock interview parameters (industry, role, round, text/voice mode).
- `POST /{id}/start`: Start interview session, receive interviewer greeting and question 1.
- `POST /{id}/respond`: Submit candidate response, receive follow-up or next question.
- `POST /{id}/conclude`: End interview and generate detailed rubric evaluation report.
- `GET /{id}/report`: Retrieve final feedback report.
- `GET /history`: List candidate's interview history.

### 10. Dashboard & Analytics (`/api/v1/dashboard`)
- `GET /overview`: Summary cards (Resume score, module progress, tests completed, interview readiness score).
- `GET /analytics`: Weekly activity time series, score progression, topic performance distribution.
- `GET /recommendations`: AI-driven recommended next actions and modules.

### 11. Administration (`/api/v1/admin`)
- `GET /stats`: Platform-wide candidate count, question count, assessment stats.
- Question management operations are currently provided under `/api/v1/questions/manage` for content-manager/admin roles. Full taxonomy and module/lesson CRUD is not yet implemented.
- `GET /users`: List and manage user accounts and roles.
