# Candidate Dashboard AAIRO

## Industry-Independent AI-Powered Career Preparation & Assessment Platform

**Candidate Dashboard AAIRO** is a commercial-grade, multi-tenant career preparation and assessment platform designed for students, freshers, working professionals, job seekers, and career switchers across 20+ industries.

The platform provides a complete, unified candidate preparation journey:
**Registration → Dynamic Onboarding → Profile & Resume Intelligence → Centralized Question Bank → Testing & Assessment → AI Career Coach & Cross-Industry Transitions → Mock Interviews → Performance Analytics.**

---

## 🏗️ Architecture & Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | React 19, TypeScript, Vite, Tailwind CSS, Lucide React, TanStack Query, React Hook Form, Zod, Recharts |
| **Backend** | Python 3.12, FastAPI, SQLAlchemy 2.0 (Async + Sync), Alembic, Pydantic v2 |
| **Database** | PostgreSQL 16+ (Normalized schema with foreign key constraints, indexes, and cascades) |
| **AI Integration** | Modular Provider Layer: **NVIDIA Open-Source NIM** (default: `nemotron-3.5-lightning-30b-a3b` / Llama / self-hosted vLLM) & Google Gemini (legacy). Strict Pydantic output validation, token usage tracking, and honest offline states. |
| **Document Processing** | PyMuPDF, pypdf, python-docx, Tesseract OCR for scanned PDF / image extraction |
| **External APIs** | OpenAlex API (citations-ranked academic & industry articles), YouTube Data API v3 (view-count-ranked video tutorials) |
| **Containerization** | Docker, Docker Compose, Nginx (Frontend SPA proxy) |

---

## 🌟 8 Core Working Modules (What Is Actually Happening)

### 1. Multi-Role Authentication & Security (RBAC)
- **Endpoints**: `/api/v1/auth/*`
- **Functionality**:
  - Secure JWT authentication with short-lived access tokens (60 min) and refresh tokens (7 days).
  - Cryptographic password hashing with `bcrypt`.
  - Role-Based Access Control (`candidate`, `administrator`, `content_manager`).
  - Brute-force rate limiting with PostgreSQL attempt tracking.

### 2. Dynamic Candidate Onboarding & Profiling
- **Endpoints**: `/api/v1/candidates/*`, `/api/v1/industries/*`, `/api/v1/companies/*`
- **Functionality**:
  - Industry-independent, database-driven onboarding wizard.
  - Captures career aspirations, target job roles, preferred companies, educational background, technical/soft skills, and interaction mode (Text/Voice).
  - Strictly candidate-isolated data access.

### 3. Resume Intelligence & Profile-to-Resume Generator
- **Endpoints**: `/api/v1/resumes/*`
- **Functionality**:
  - **Multi-Format Ingestion**: Uploads PDF, DOCX, and scanned images with OCR extraction.
  - **Deterministic ATS Scoring**: Keyword frequency, section compliance (Summary, Experience, Education, Skills, Projects), and job description match percentage.
  - **AI Resume Analysis**: Identifies skill gaps, candidate strengths, and structured resume bullet suggestions.
  - **Grounded Suggestion Actions**: Candidates can accept/reject suggestions. Grounding checks prevent hallucinated facts from corrupting resume versions.
  - **Profile Resume Builder** (`POST /api/v1/resumes/generate-from-profile`): Converts profile details directly into a downloadable, beautifully formatted Word document (`.docx`).

### 4. Centralized Question Bank & Taxonomy
- **Endpoints**: `/api/v1/questions/*`, `/api/v1/question-taxonomy/*`
- **Functionality**:
  - Multi-level taxonomy: Industry → Category → Domain → Subject → Topic → Skill.
  - Candidate practice mode with objective instant scoring for MCQs.
  - Answer keys are strictly protected from candidate API responses until submission.
  - Bookmarking, search, difficulty filtering, and persistent practice history.
  - Admin controls for authoring, AI drafting (via NVIDIA/Gemini), review, publication, and revision rollback.

### 5. Testing Mode & Dynamic Quiz Generator
- **Endpoints**: `/api/v1/testing/*`
- **Functionality**:
  - Candidate assessment sessions with timed windows and objective score calculation.
  - **Dynamic Quiz Generator** (`POST /api/v1/testing/quiz`): Uses NVIDIA open-source models to generate calibrated, fresh multiple-choice questions on any subject/topic based on candidate difficulty level and latest industry trends (with deterministic offline fallback).

### 6. AI Career Coach & Cross-Industry Transition Roadmaps
- **Endpoints**: `/api/v1/coach/*`
- **Functionality**:
  - **Interactive Coach Chat**: Context-aware AI mentorship answering candidate queries about interviews, preparation strategy, and career progression.
  - **Cross-Industry Career Transition Knowledge Base** (`POST /api/v1/coach/career-transition`): Maps transferable skills, gap bridging, certification pathways, and step-by-step roadmaps for candidates switching domains (e.g. Engineering → HR, Marketing → Tech, Sales → Product Management).
  - **Curated Learning Resources** (`GET /api/v1/coach/resources`): Fetches the **top 5 most cited articles** via OpenAlex and **top 5 most viewed video tutorials** via YouTube Data API for any topic.

### 7. Learning Modules & Structured Lessons
- **Endpoints**: `/api/v1/modules/*`, `/api/v1/admin/modules/*`
- **Functionality**:
  - Role-linked and skill-linked course modules with markdown lessons.
  - Candidate enrollment and persistent lesson completion tracking.
  - Admin workflows for lesson authoring, reordering, draft/publish states, and archiving.

### 8. AI Mock Interview Engine & Performance Analytics
- **Endpoints**: `/api/v1/interviews/*`, `/api/v1/dashboard/*`
- **Functionality**:
  - Simulates multi-turn technical and behavioral interviews tailored to target role and company.
  - Turn-by-turn question delivery and candidate response capture.
  - Multi-dimensional rubric evaluation report: Overall Score, Technical Score, Domain Score, Communication Score, and Structure Score.
  - Unified candidate dashboard tracking readiness score, assessment breakdown, and recent activity feed.

---

## 🚀 Quick Start Guide

For Render production deployment and the required database migration allowlist, see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

### Prerequisites
- Python 3.12+
- Node.js >= 18
- PostgreSQL 16+ (or Docker)

### 1. Environment Configuration
Create a `.env` file in the project root:
```bash
cp .env.example .env
```
Key configuration parameters:
```env
# AI Model Selection (NVIDIA Open-Source / NIM by default)
AI_PROVIDER=nvidia
NVIDIA_API_KEY=your_nvidia_api_key_here
NVIDIA_MODEL=nvidia/nemotron-3.5-lightning-30b-a3b
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1

# Optional Video & Article APIs
YOUTUBE_API_KEY=your_youtube_api_key_here
OPENALEX_BASE_URL=https://api.openalex.org
```

### 2. Database Setup
Start PostgreSQL via Docker Compose:
```bash
docker compose up -d postgres
```
Run database migrations and seed baseline taxonomy:
```bash
./scripts/migrate_test_db.sh upgrade head
```

### 3. Run Backend (FastAPI)
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Interactive Swagger API documentation: `http://localhost:8000/docs`

### 4. Run Frontend (React + Vite)
```bash
cd frontend
npm install
npm run dev
```
Access the application at `http://localhost:5173`

---

## 🧪 Testing & Verification

### Run Backend Tests (162 Tests)
```bash
cd backend
DATABASE_URL="postgresql+asyncpg://aairo_user:aairo_secure_password@localhost:5432/aairo_phase4_pytest" \
DATABASE_URL_SYNC="postgresql://aairo_user:aairo_secure_password@localhost:5432/aairo_phase4_pytest" \
GEMINI_API_KEY='' NVIDIA_API_KEY='' ./venv/bin/pytest tests/ -q
```
*All 162 unit and integration tests execute against the isolated test database.*

### Run Frontend Tests (18 Tests & TypeScript Verification)
```bash
cd frontend
npm test -- --run
npm run build
```
*Zero TypeScript errors (`tsc -b`), all Vitest unit tests pass, and Vite builds cleanly in ~1.1s.*

---

## 📁 Project Directory Structure

```
CandidateDashboardAAIRO/
├── backend/
│   ├── alembic/                # Database migrations
│   ├── app/
│   │   ├── api/v1/             # REST API routers (auth, resumes, coach, etc.)
│   │   ├── core/               # App configuration, security, database session
│   │   ├── integrations/ai/    # NVIDIA & Gemini AI provider implementations
│   │   ├── models/             # SQLAlchemy ORM models
│   │   ├── schemas/            # Pydantic v2 request/response schemas
│   │   ├── services/           # Core business logic (resume, coach, interview, etc.)
│   │   └── main.py             # FastAPI application entrypoint
│   └── tests/                  # Pytest test suites (162 tests)
├── frontend/
│   ├── src/
│   │   ├── api/                # Typed API client services
│   │   ├── components/         # Reusable UI components (Navbar, Sidebar, etc.)
│   │   ├── context/            # AuthContext & state management
│   │   ├── layouts/            # Dashboard & Auth layouts
│   │   ├── pages/              # View pages (Resume, Coach, Testing, Interview, etc.)
│   │   └── types/              # TypeScript interfaces
│   └── vite.config.ts          # Vite build configuration
├── docs/                       # Technical architecture, schema, and API docs
├── scripts/                    # Database migration & utility scripts
├── docker-compose.yml          # Containerized PostgreSQL & services
└── .env.example                # Template environment variables
```
