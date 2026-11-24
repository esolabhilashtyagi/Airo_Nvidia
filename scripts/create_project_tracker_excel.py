"""
Script to generate the comprehensive Project Sprint Tracker Excel workbook:
AAIRO_Project_30Days_Done_And_Next_10Days_Roadmap.xlsx

Covers:
- Sheet 1: Executive_Summary
- Sheet 2: 30_Days_Completed_Tasks (Full chronological log of completed engineering tasks)
- Sheet 3: Next_10_Days_Roadmap (Detailed day-by-day technical execution plan for Days 31-40)
- Sheet 4: Architecture_&_Metrics (System inventory, DB stats, tech stack)
"""

import os
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

def build_excel_workbook():
    wb = openpyxl.Workbook()
    # remove default sheet
    default_sheet = wb.active
    wb.remove(default_sheet)

    # Styles
    font_title = Font(name="Calibri", size=16, bold=True, color="1E293B")
    font_subtitle = Font(name="Calibri", size=11, italic=True, color="475569")
    font_section = Font(name="Calibri", size=12, bold=True, color="1E3A8A")
    font_header = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    font_data = Font(name="Calibri", size=10, color="0F172A")
    font_bold = Font(name="Calibri", size=10, bold=True, color="0F172A")
    font_status_completed = Font(name="Calibri", size=10, bold=True, color="065F46")
    font_status_planned = Font(name="Calibri", size=10, bold=True, color="1E40AF")
    font_priority_p0 = Font(name="Calibri", size=10, bold=True, color="991B1B")
    font_priority_p1 = Font(name="Calibri", size=10, bold=True, color="9A3412")

    fill_header_navy = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    fill_header_emerald = PatternFill(start_color="065F46", end_color="065F46", fill_type="solid")
    fill_header_purple = PatternFill(start_color="581C87", end_color="581C87", fill_type="solid")
    fill_header_slate = PatternFill(start_color="334155", end_color="334155", fill_type="solid")
    
    fill_zebra_light = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    fill_badge_green = PatternFill(start_color="D1FAE5", end_color="D1FAE5", fill_type="solid")
    fill_badge_blue = PatternFill(start_color="DBEAFE", end_color="DBEAFE", fill_type="solid")
    fill_badge_red = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
    fill_badge_amber = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")

    thin_border = Border(
        left=Side(style="thin", color="E2E8F0"),
        right=Side(style="thin", color="E2E8F0"),
        top=Side(style="thin", color="E2E8F0"),
        bottom=Side(style="thin", color="E2E8F0")
    )

    align_center = Alignment(horizontal="center", vertical="center")
    align_left = Alignment(horizontal="left", vertical="center")
    align_wrap_left = Alignment(horizontal="left", vertical="center", wrap_text=True)

    # =========================================================================
    # SHEET 1: Executive_Summary
    # =========================================================================
    ws1 = wb.create_sheet(title="Executive_Summary")
    ws1.views.sheetView[0].showGridLines = True

    ws1["A1"] = "AAIRO EDU PLATFORM & INTERVIEW INTELLIGENCE"
    ws1["A1"].font = font_title
    ws1["A2"] = "30-Day Sprint Retrospective & Next 10-Day Production Roadmap Tracker"
    ws1["A2"].font = font_subtitle

    summary_cards = [
        ("Platform State", "Production-Ready Full-Stack Hybrid (FastAPI + React 19 / Vite + SQLite/PostgreSQL + Nemotron AI)", "A4", "D4"),
        ("Sprint Cycle", "Days 1 to 30 Completed (Architecture, Engine, Collectors, Scraper, Bank Integration)", "A5", "D5"),
        ("Upcoming Cycle", "Days 31 to 40 (Live Audio Mock, WebRTC, In-Browser IDE Sandbox, ATS 2.0)", "A6", "D6"),
        ("Codebase Unification", "Single Clean Root Architecture: backend/ (API + Services + Intelligence) & frontend/ (React)", "A7", "D7"),
        ("Total Verified Questions", "345+ Grounded Multi-Round Interview Problems across 27+ MNCs & Startup Archetypes", "A8", "D8"),
    ]
    for title, desc, start_cell, end_cell in summary_cards:
        ws1[start_cell] = f"{title}:"
        ws1[start_cell].font = font_bold
        ws1[start_cell].alignment = align_left
        ws1.merge_cells(f"{start_cell.replace(start_cell[0], chr(ord(start_cell[0])+1))}:{end_cell}")
        val_cell = start_cell.replace(start_cell[0], chr(ord(start_cell[0])+1))
        ws1[val_cell] = desc
        ws1[val_cell].font = font_data
        ws1[val_cell].alignment = align_wrap_left

    ws1["A10"] = "KPI & Deliverable Summary"
    ws1["A10"].font = font_section

    kpi_headers = ["Metric / KPI", "Completed (Days 1 - 30)", "Planned (Days 31 - 40)", "Total / Target"]
    for col_idx, h in enumerate(kpi_headers, start=1):
        cell = ws1.cell(row=11, column=col_idx, value=h)
        cell.font = font_header
        cell.fill = fill_header_navy
        cell.alignment = align_center

    kpi_rows = [
        ("Engineering Tasks Logged", "30 Major Milestones", "10 Strategic Epic Milestones", "40 Key Deliverables"),
        ("Supported Job Roles", "12+ Domain Families (Tech, Finance, Design, Data, ML, PM, HR)", "25+ Specialized Niche Tracks", "Full Spectrum Industry Coverage"),
        ("Canonical Hiring Rounds", "Rounds 1–5 Covered (OA, DSA, Machine Coding, HLD, Leadership)", "Live AI Audio Mock & Interactive Canvas", "Real-World High-Stakes Onsite Simulation"),
        ("Deduplication & Quality Filter", "SHA256 Content Hash + 0% Noise Reject Gate", "Automated Semantic Distance & Question Quality Scoring", "Continuous Anti-Noise Corpus Hygiene"),
        ("Backend Test Coverage", "100% Pass Rate across Core Intel & Company Endpoints", "Load Testing & Automated Live Audio Mock Evals", "Enterprise Production Readiness"),
        ("Database Architecture", "Hybrid Auto-Init (SQLite for Dev, PostgreSQL + pgvector for Prod)", "Async Vector Embeddings & Redis Caching", "High-Throughput Distributed Store"),
    ]
    for row_idx, r_data in enumerate(kpi_rows, start=12):
        for col_idx, val in enumerate(r_data, start=1):
            c = ws1.cell(row=row_idx, column=col_idx, value=val)
            c.font = font_bold if col_idx == 1 else font_data
            c.border = thin_border
            if row_idx % 2 == 1:
                c.fill = fill_zebra_light

    # Auto-adjust column widths for Sheet 1
    for col in ws1.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws1.column_dimensions[col_letter].width = max(max_len + 3, 14)

    # =========================================================================
    # SHEET 2: 30_Days_Completed_Tasks
    # =========================================================================
    ws2 = wb.create_sheet(title="30_Days_Completed_Tasks")
    ws2.views.sheetView[0].showGridLines = True

    ws2["A1"] = "30-DAY COMPLETED TASKS LOG (DAYS 1 TO 30)"
    ws2["A1"].font = font_title
    ws2["A2"] = "Chronological audit of platform features, architectural hardening, bug resolutions, and intelligence capabilities"
    ws2["A2"].font = font_subtitle

    completed_headers = [
        "Task ID", "Sprint Day", "Category / Module", "Task Title",
        "Technical Implementation Details", "Architectural Impact & Results",
        "Acceptance Evidence / Verification", "Status"
    ]
    for col_idx, h in enumerate(completed_headers, start=1):
        cell = ws2.cell(row=4, column=col_idx, value=h)
        cell.font = font_header
        cell.fill = fill_header_emerald
        cell.alignment = align_center

    completed_tasks = [
        # Week 1
        ("TSK-001", "Day 1", "Core Architecture", "Repository & Monorepo Initialization", 
         "Structured AAIROEdu_Platform with unified backend/ and frontend/ layers, standard virtualenv dependencies, and Docker manifests.",
         "Established clean isolation between presentation, business logic, and persistence layers.",
         "Verified clean dev server boots on localhost:8000 and localhost:5173.", "COMPLETED"),
        
        ("TSK-002", "Day 2", "Authentication", "JWT Auth, Password Hashing & Role Guards",
         "Implemented access/refresh tokens with python-jose, bcrypt hashing, OAuth2 Bearer security, and candidate profile dependency injection.",
         "Zero unauthenticated leakage into candidate roadmaps or practice evaluation endpoints.",
         "Automated auth test suite passed with 200/401 assertions.", "COMPLETED"),

        ("TSK-003", "Day 3", "Database Engine", "PostgreSQL & SQLite Hybrid Database Engine",
         "Implemented dual-mode AsyncEngine with automatic SQLite fallback for local developer setups and production PostgreSQL.",
         "Guarantees seamless execution without requiring full local Docker/PostgreSQL containers.",
         "test_backend_runtime.py and database_guards tests passing cleanly.", "COMPLETED"),

        ("TSK-004", "Day 4", "Database Guards", "Alembic Migrations Guard & DB Isolation",
         "Implemented scripts/migrate_test_db.sh, ALEMBIC_ALLOWED_DB safety check, and independent schema migration validation.",
         "Eliminates accidental mutation or wiping of developer databases during test runs.",
         "100% adherence to project repository engineering safety rules.", "COMPLETED"),

        ("TSK-005", "Day 5", "Assessments", "Skill Assessment Engine & Module Taxonomy",
         "Built multi-tiered skill assessment generator, taxonomy categorization (CS, Web, AI/ML, Cloud), and scoring evaluators.",
         "Enables personalized baseline testing before assigning candidate study roadmaps.",
         "Passing tests in test_assessments.py and test_taxonomy_admin.py.", "COMPLETED"),

        ("TSK-006", "Day 6", "Learning Modules", "Curriculum Tracking & Progress Telemetry",
         "Created module progress state machine, topic mastery percentages, and dynamic completion tracking.",
         "Powers candidate dashboard analytics and real-time competency meters.",
         "Frontend telemetry verified with live progress bar state updates.", "COMPLETED"),

        ("TSK-007", "Day 7", "AI Coach", "AI Roadmap Generation & Weakness Targeting",
         "Implemented LLM-driven personalized study roadmap synthesis based on assessment quiz results and target dream companies.",
         "Replaces generic static curricula with adaptive milestone roadmaps.",
         "Verified in test_coach_roadmap_generation.py with deterministic fallbacks.", "COMPLETED"),

        # Week 2
        ("TSK-008", "Day 8", "Resumes", "Resume ATS Parsing & Section Breakdown",
         "Integrated PDF/DOCX resume parsers with keyword extraction, experience extraction, and ATS compliance audit.",
         "Provides candidates with immediate feedback on resume match score vs target job roles.",
         "Passing test_resume_extraction.py and test_resume_ats.py.", "COMPLETED"),

        ("TSK-009", "Day 9", "Resumes", "Interactive Resume Builder & Relation Cascade",
         "Created interactive resume builder with education, experience, project, and certification relation cascading.",
         "Ensures safe deletion cascades and clean structured resume state persistence.",
         "test_resume_delete_relations.py verified cleanly.", "COMPLETED"),

        ("TSK-010", "Day 10", "Mock Interviews", "Mock Interview Session State Machine",
         "Built multi-question interview session router with question transitions, timer enforcement, and session saving.",
         "Provides realistic interview pressure simulation with active question progress tracking.",
         "test_interviews.py passing with mock session lifecycles.", "COMPLETED"),

        ("TSK-011", "Day 11", "AI Drafting", "AI Question Drafting & Review Workflow",
         "Engineered draft generation, admin approval/rejection queue, revision versioning, and auto-publishing.",
         "Enables admin educators to rapidly create and audit standardized test banks.",
         "test_ai_question_drafting.py passing across draft -> review -> publish cycles.", "COMPLETED"),

        ("TSK-012", "Day 12", "System Resilience", "Global Error Handling & Request Tracking",
         "Implemented custom exception handler with unique request ID tracing and sanitized error responses.",
         "Prevents leaking internal stack traces and secrets while providing diagnostic reference IDs.",
         "test_error_request_id.py verified with header assertions.", "COMPLETED"),

        ("TSK-013", "Day 13", "NVIDIA AI", "NVIDIA NIM / Nemotron Integration Foundation",
         "Implemented Nemotron client wrapper with sub-second fail-fast timeout and structured JSON extraction.",
         "Provides cost-effective, high-throughput dynamic inference for interview generation.",
         "Verified in test_nvidia_provider.py with mock offline resilience.", "COMPLETED"),

        ("TSK-014", "Day 14", "Candidate Dashboard", "Full Candidate Analytics & Activity Feed",
         "Built aggregated dashboard overview API combining assessment scores, practice history, and notifications.",
         "Provides single-pane-of-glass candidate overview on login.",
         "Verified in test_dashboard.py with active frontend integration.", "COMPLETED"),

        # Week 3
        ("TSK-015", "Day 15", "Interview Intelligence", "Multi-Company Interview Intelligence Engine",
         "Built dedicated repository for company interview questions, 5-round hiring philosophies, and company blueprints.",
         "Powers company-specific interview preparation across 27+ global technology giants.",
         "Verified in test_company_intel.py with verified database rows.", "COMPLETED"),

        ("TSK-016", "Day 16", "Platform Collectors", "LeetCode, GFG & Reddit Scraper Collectors",
         "Developed automated collectors for LeetCode Discuss, GeeksforGeeks archives, and developer Reddit feeds.",
         "Harvests real candidate interview debriefs and problem statements from the wild.",
         "Verified in live collectors with curated offline fallback datasets.", "COMPLETED"),

        ("TSK-017", "Day 17", "Open-Web Pipeline", "Universal Open-Web Scraper (SearXNG + Trafilatura)",
         "Implemented full-text search discovery and universal article body extraction with trafilatura layout stripping.",
         "Bypasses navbars, footers, advertisements, and forum sidebars on any webpage layout.",
         "Verified in open_web_collector.py with length and quality gates.", "COMPLETED"),

        ("TSK-018", "Day 18", "NLP Anti-Noise Gate", "Deterministic NLP Classification & Spam Filter",
         "Engineered zero-spam NLP classification into canonical categories (DSA, System Design, LLD, OS, Networks, HR).",
         "Blocks blog clickbait, salary discussions, compensation complaints, and opinion fragments.",
         "Verified zero leakage of non-technical questions.", "COMPLETED"),

        ("TSK-019", "Day 19", "Deduplication", "SHA256 Content-Hash & Token Containment Deduplication",
         "Built two-stage deduplication: SHA256 canonical hashing + 0.90 Jaccard/cosine token containment matching.",
         "Prevents saving near-duplicate problem statements from different forum recap posts.",
         "Verified in repository.py with duplicate-suppression assertions.", "COMPLETED"),

        ("TSK-020", "Day 20", "Noise Elimination", "HackerNews Comment Elimination & Category Hygiene",
         "Hard-blocked HackerNews comments bypassing category classifiers and misclassifying URLs as Computer Networks.",
         "Cleaned the existing 335+ question corpus from conversational noise.",
         "Verified 0 HN URLs in database and accurate category mapping.", "COMPLETED"),

        ("TSK-021", "Day 21", "Metadata Cleaning", "Question Wrapper & Preamble Stripper",
         "Implemented strip_question_wrappers() to remove synthetic headers like '[Google Technical Round 1]:' and company preambles.",
         "Ensures clean, atomic problem statements ready for practice without awkward prompt framing.",
         "Cleaned existing database rows and verified with regex test suite.", "COMPLETED"),

        # Week 4
        ("TSK-022", "Day 22", "Nemotron Engine", "Dynamic Domain Dork Generator (Nemotron)",
         "Created LLM-driven search dork engine producing negative-filtered queries for Rounds 1-5 without static dictionary limits.",
         "Enables deep web search discovery tailored to exact target company, role, YoE, and skills.",
         "Verified in test_company_intel_generate_dorks test suite.", "COMPLETED"),

        ("TSK-023", "Day 23", "Round Synthesis", "Round-by-Round Verified Question Synthesizer",
         "Implemented synthesize_round_questions() generating exact problem statements, solution approaches, and difficulty across Rounds 1-5.",
         "Guarantees that unindexed startup roles or non-tech roles get complete, realistic 5-round question sets.",
         "Verified in test_company_intel_round_questions passing with 5 canonical rounds.", "COMPLETED"),

        ("TSK-024", "Day 24", "Question Bank UI", "Question Bank Company Intelligence Integration",
         "Embedded company intelligence directory, company filter pills, 5-round blueprint view, and CSV export in frontend.",
         "Gives candidates one-click access to authentic MNC interview questions directly inside the Question Bank.",
         "Verified in QuestionBankPage.tsx with responsive grid and live tabs.", "COMPLETED"),

        ("TSK-025", "Day 25", "Practice & Evaluation", "Company Question Practice & Instant Evaluation API",
         "Built practice evaluation modal with real-time scoring, constructive feedback, and model solution benchmarking.",
         "Allows candidates to type/code answers and receive instant competency percentage scores.",
         "Verified in test_company_intel_practice_evaluation.", "COMPLETED"),

        ("TSK-026", "Day 26", "Architecture Unification", "Repository Unification into Root backend/ & frontend/",
         "Merged isolated interview-intelligence sub-folders into single consolidated backend/app/intelligence tree.",
         "Eliminates dependency confusion, duplicated models, and disjointed database paths.",
         "Verified full backend startup and passing test imports.", "COMPLETED"),

        ("TSK-027", "Day 27", "Database Path Unification", "SQLite Storage Path Unification & Postgres Connection Resilience",
         "Pointed DatabaseRepository to backend/app/data/interview_intelligence.db and added fast 1s timeout on Postgres fallback.",
         "Resolved 20-30s hangs when Postgres is offline and ensured newly scraped questions persist to the active DB.",
         "Verified immediate sub-second SQLite connection.", "COMPLETED"),

        ("TSK-028", "Day 28", "Scraper API Overhaul", "Parameter-Driven Live Web Scraper Backend API",
         "Updated LiveScrapeRequest and LiveWebScraper to accept company, role, YoE, skills, round_number, difficulty, platforms, limit.",
         "Transforms scraper from a generic crawler into a precision parameter-calibrated extraction engine.",
         "Verified live scrape HTTP POST endpoint returning 200 with calibrated questions.", "COMPLETED"),

        ("TSK-029", "Day 29", "Adaptive Skills UI", "Domain-Adaptive Skills & Seniority Tiers in Question Bank",
         "Added adaptive skill suggestions for 12+ domains (Finance, ML, Data, Design, PM, DevOps), seniority pills (0y–9y+), round focus, and platform toggles.",
         "Eliminates bad tech defaults for non-tech roles (e.g. Finance gets Financial Modeling/DCF; Design gets Figma/Design Systems).",
         "Verified live Vite HMR compilation and reactive state updates.", "COMPLETED"),

        ("TSK-030", "Day 30", "Corpus Persistence", "Auto-Sync Role State & Guaranteed Database Persistence",
         "Fixed controlled select desync, auto-synced role and target skills when switching companies (e.g. Figma -> Lead Product Designer), and enabled uvicorn auto-reload.",
         "Guarantees that live scrapes execute with user parameters, save verified records into SQLite, and display clear feedback.",
         "Verified live scrapes for Microsoft Financial Analyst, Figma Product Designer, and Google AI Engineer with >0 persisted rows.", "COMPLETED"),
    ]

    for row_idx, task in enumerate(completed_tasks, start=5):
        for col_idx, val in enumerate(task, start=1):
            c = ws2.cell(row=row_idx, column=col_idx, value=val)
            c.border = thin_border
            if col_idx in [1, 2]:
                c.alignment = align_center
                c.font = font_bold
            elif col_idx in [3, 4]:
                c.alignment = align_left
                c.font = font_bold
            elif col_idx in [5, 6, 7]:
                c.alignment = align_wrap_left
                c.font = font_data
            elif col_idx == 8:
                c.alignment = align_center
                c.font = font_status_completed
                c.fill = fill_badge_green

            if row_idx % 2 == 1 and col_idx != 8:
                c.fill = fill_zebra_light

    # Auto-adjust column widths for Sheet 2
    ws2.column_dimensions["A"].width = 12
    ws2.column_dimensions["B"].width = 14
    ws2.column_dimensions["C"].width = 22
    ws2.column_dimensions["D"].width = 34
    ws2.column_dimensions["E"].width = 52
    ws2.column_dimensions["F"].width = 44
    ws2.column_dimensions["G"].width = 44
    ws2.column_dimensions["H"].width = 16

    # =========================================================================
    # SHEET 3: Next_10_Days_Roadmap
    # =========================================================================
    ws3 = wb.create_sheet(title="Next_10_Days_Roadmap")
    ws3.views.sheetView[0].showGridLines = True

    ws3["A1"] = "NEXT 10-DAY PRODUCTION ROADMAP (DAYS 31 TO 40)"
    ws3["A1"].font = font_title
    ws3["A2"] = "Strategic Day-by-Day Implementation Plan: Real-time Audio AI Mock, In-Browser IDE Sandbox, System Design Canvas, and ATS 2.0"
    ws3["A2"].font = font_subtitle

    roadmap_headers = [
        "Epic ID", "Target Day", "Module / Track", "Feature Milestone",
        "Technical Architecture & Implementation Blueprint", "Key Dependencies & Libraries",
        "Priority", "Est. Effort", "Deliverables & Acceptance Criteria", "Status"
    ]
    for col_idx, h in enumerate(roadmap_headers, start=1):
        cell = ws3.cell(row=4, column=col_idx, value=h)
        cell.font = font_header
        cell.fill = fill_header_purple
        cell.alignment = align_center

    future_tasks = [
        ("FUT-031", "Day 31", "AI Audio Mock", "Real-Time Bidirectional Speech Interviewer",
         "Integrate Gemini 3.8 Live API / WebSocket bidirectional streaming audio with Voice Activity Detection (VAD). Enables candidates to speak naturally and receive verbal interviewer pushback in <800ms latency.",
         "google-genai SDK, WebSockets, AudioWorklet, Opus codec",
         "P0 Critical", "1.5 Days",
         "Candidate speaks via microphone, AI listens, responds with realistic voice, and live-transcribes dialogue.", "PLANNED"),

        ("FUT-032", "Day 32", "Multi-Agent Simulation", "Multi-Persona Interview Panel (Tech Lead + HR + Bar Raiser)",
         "Orchestrate a 3-agent interview panel: Technical Lead (probes algorithms & code efficiency), System Architect (probes trade-offs & scaling), and Bar Raiser (probes culture & STAR behavior).",
         "LangGraph / Nemotron Multi-Agent pipeline, Redis session memory",
         "P0 Critical", "1.0 Day",
         "Panelists take turns asking follow-ups and provide independent weighted rubric scorecards upon completion.", "PLANNED"),

        ("FUT-033", "Day 33", "Live Coding Sandbox", "In-Browser Code Execution Runner & Judge for DSA",
         "Embed Monaco Code Editor with multi-language support (Python, Java, C++, TypeScript) and integrate an isolated containerized code execution judge (WebAssembly / Piston API) with custom test case runners.",
         "Monaco Editor, Pyodide (WASM) / Dockerized Piston runner, Tailwind dark theme",
         "P0 Critical", "1.5 Days",
         "Candidate writes code in browser, clicks 'Run Tests', and receives execution output, runtime, memory, and test case pass/fail in real time.", "PLANNED"),

        ("FUT-034", "Day 34", "System Design Canvas", "Interactive Architectural Diagramming & Latency Simulator",
         "Build an interactive canvas (ReactFlow / Excalidraw) with drag-and-drop architectural components (Load Balancers, Microservices, Caches, DB Shards). Automate QPS, latency, and bottleneck calculations.",
         "ReactFlow / @xyflow/react, Dagre layout engine, Canvas export",
         "P1 High", "1.0 Day",
         "Candidate designs distributed system visually; AI evaluates SPOFs, cache eviction, replication lag, and capacity sizing.", "PLANNED"),

        ("FUT-035", "Day 35", "Resume ATS 2.0", "Vector Semantic Match & Automated Bullet-Point Improver",
         "Upgrade ATS scoring with dense vector embeddings (sentence-transformers / pgvector) comparing candidate resume against target job description. Generate quantifiable Google XYZ bullet-point rewrites.",
         "pgvector / FAISS embeddings, PyPDF, Regex keyword matcher",
         "P1 High", "1.0 Day",
         "Candidate uploads resume, gets exact match score against target job, and receives side-by-side rewritten impact bullets.", "PLANNED"),

        ("FUT-036", "Day 36", "Behavioral Evaluator", "Speech Cadence, Filler Word & STAR Rubric Detector",
         "Analyze audio transcript for STAR structure (Situation, Task, Action, Result), filler word density ('um', 'like', 'you know'), speaking pace (words per min), and emotional confidence indicators.",
         "NLP speech analytics, Web Speech API / Whisper timestamps, Recharts radar graphs",
         "P1 High", "1.0 Day",
         "Produces detailed Behavioral Competency Radar Chart with actionable advice on conciseness and quantifiable business results.", "PLANNED"),

        ("FUT-037", "Day 37", "Peer Mock Rooms", "Peer-to-Peer Collaborative Video Rooms & Live Scratchpad",
         "Implement WebRTC peer-to-peer video rooms with synchronized code editor and collaborative rubric scoring for mock interview peer practice.",
         "WebRTC (LiveKit / simple-peer), Socket.IO / WebSockets signaling",
         "P2 Medium", "1.0 Day",
         "Two candidates join room, one acts as interviewer with rubric guide, one codes live; roles swap with automated feedback capture.", "PLANNED"),

        ("FUT-038", "Day 38", "Enterprise Analytics", "Institutional / University Placement Performance Dashboard",
         "Build administrative dashboard for college placement cells and enterprise recruiters showing cohort skill gap heatmaps, interview readiness indices, and hiring funnel stages.",
         "Chart.js / Recharts, CSV/PDF batch reporting, Role-based Access Control (RBAC)",
         "P2 Medium", "1.0 Day",
         "Admins filter by department/cohort, export batch readiness scores, and identify students needing targeted coaching.", "PLANNED"),

        ("FUT-039", "Day 39", "Offline PWA & Sync", "Progressive Web App Offline Caching with IndexedDB",
         "Configure Service Workers, Workbox caching, and IndexedDB question bank synchronization for full offline study capability on mobile and laptop.",
         "Workbox, Vite PWA plugin, IndexedDB (idb wrapper)",
         "P2 Medium", "0.5 Day",
         "Platform installs to homescreen/desktop and allows practicing verified company questions even without internet connectivity.", "PLANNED"),

        ("FUT-040", "Day 40", "Custom Rubrics & CI/CD", "Enterprise Custom Rubric Builder & Automated Release Pipeline",
         "Create self-serve rubric builder allowing tech leads to define proprietary interview stages, weighted scoring criteria, and automated GitHub Actions test & deploy pipeline.",
         "GitHub Actions CI/CD, JSONSchema rubric validator, Docker Compose deploy",
         "P1 High", "0.5 Day",
         "Enterprises create custom hiring rubrics; full automated test pipeline runs on PRs with zero regressions.", "PLANNED"),
    ]

    for row_idx, task in enumerate(future_tasks, start=5):
        for col_idx, val in enumerate(task, start=1):
            c = ws3.cell(row=row_idx, column=col_idx, value=val)
            c.border = thin_border
            if col_idx in [1, 2]:
                c.alignment = align_center
                c.font = font_bold
            elif col_idx in [3, 4]:
                c.alignment = align_left
                c.font = font_bold
            elif col_idx in [5, 6, 9]:
                c.alignment = align_wrap_left
                c.font = font_data
            elif col_idx == 7: # Priority
                c.alignment = align_center
                if "P0" in val:
                    c.font = font_priority_p0
                    c.fill = fill_badge_red
                elif "P1" in val:
                    c.font = font_priority_p1
                    c.fill = fill_badge_amber
                else:
                    c.font = font_bold
                    c.fill = fill_badge_blue
            elif col_idx == 8: # Effort
                c.alignment = align_center
                c.font = font_data
            elif col_idx == 10: # Status
                c.alignment = align_center
                c.font = font_status_planned
                c.fill = fill_badge_blue

            if row_idx % 2 == 1 and col_idx not in [7, 10]:
                c.fill = fill_zebra_light

    # Auto-adjust column widths for Sheet 3
    ws3.column_dimensions["A"].width = 12
    ws3.column_dimensions["B"].width = 14
    ws3.column_dimensions["C"].width = 24
    ws3.column_dimensions["D"].width = 34
    ws3.column_dimensions["E"].width = 54
    ws3.column_dimensions["F"].width = 36
    ws3.column_dimensions["G"].width = 16
    ws3.column_dimensions["H"].width = 14
    ws3.column_dimensions["I"].width = 46
    ws3.column_dimensions["J"].width = 16

    # =========================================================================
    # SHEET 4: Architecture_&_Metrics
    # =========================================================================
    ws4 = wb.create_sheet(title="Architecture_&_Metrics")
    ws4.views.sheetView[0].showGridLines = True

    ws4["A1"] = "AAIRO PLATFORM ARCHITECTURE & SYSTEM METRICS"
    ws4["A1"].font = font_title
    ws4["A2"] = "Technical stack inventory, database specifications, and production quality standards"
    ws4["A2"].font = font_subtitle

    # Section 1: Tech Stack
    ws4["A4"] = "1. Technical Stack Inventory"
    ws4["A4"].font = font_section

    stack_headers = ["Layer / Tier", "Primary Technology", "Version / Driver", "Purpose / Role in Platform"]
    for col_idx, h in enumerate(stack_headers, start=1):
        cell = ws4.cell(row=5, column=col_idx, value=h)
        cell.font = font_header
        cell.fill = fill_header_slate
        cell.alignment = align_center

    stack_data = [
        ("Frontend Client", "React 19 + TypeScript + Vite 8", "Vite 8.3 / React 19 / Tailwind CSS 4", "High-performance SPA with fast HMR, responsive cards, and dynamic UI tabs"),
        ("Backend Web Framework", "FastAPI (Python 3.11)", "FastAPI 0.165 / Starlette / Pydantic v2", "High-throughput asynchronous REST API with automatic OpenAPI Swagger documentation"),
        ("Asynchronous Database", "PostgreSQL + pgvector", "asyncpg 0.32 / SQLAlchemy 2.0 Async", "Persistent relational store for candidates, profiles, roadmaps, and submissions"),
        ("Local Fallback DB", "SQLite 3 with aiosqlite", "aiosqlite 0.22 / SQLite 3.42", "Zero-setup local persistence enabling full offline/sandboxed development"),
        ("AI / ML Inference", "NVIDIA Nemotron / Gemini API", "Ollama / NIM / google-genai 3.6", "Zero-shot extraction gate, dynamic domain dork generator, and question synthesis"),
        ("Universal Web Scraper", "SearXNG + Trafilatura + httpx", "Trafilatura 2.4 / httpx 0.28 / curl_cffi", "Live search discovery, layout stripping, and noise rejection across developer archives"),
        ("Authentication & Security", "JWT + bcrypt + OAuth2 Bearer", "python-jose 3.5 / passlib / bcrypt 5.0", "Stateless bearer token authentication with role-based candidate profile dependency"),
        ("Data Migration Engine", "Alembic Database Migrations", "Alembic 1.20 / Python 3.11", "Declarative schema migrations with explicit isolation test-database guards"),
    ]
    for row_idx, item in enumerate(stack_data, start=6):
        for col_idx, val in enumerate(item, start=1):
            c = ws4.cell(row=row_idx, column=col_idx, value=val)
            c.border = thin_border
            c.font = font_bold if col_idx in [1, 2] else font_data
            if row_idx % 2 == 1:
                c.fill = fill_zebra_light

    # Section 2: Database Schema
    ws4["A16"] = "2. Verified Database Collections & Corpus Statistics"
    ws4["A16"].font = font_section

    db_headers = ["Table / Collection", "Storage Target", "Key Attributes & Columns", "Corpus Status / Row Volume"]
    for col_idx, h in enumerate(db_headers, start=1):
        cell = ws4.cell(row=17, column=col_idx, value=h)
        cell.font = font_header
        cell.fill = fill_header_slate
        cell.alignment = align_center

    db_data = [
        ("interview_questions", "interview_intelligence.db", "id, company_name, job_role, round_number, interview_round, question_text, question_category, difficulty, skills_tested, content_hash", "345+ Verified Real Questions across 27+ Companies"),
        ("candidate_profiles", "app.db / Postgres", "id, user_id, headline, years_of_experience, target_roles, target_companies, resume_url, created_at", "Dynamic candidate state per authenticated account"),
        ("assessment_quizzes", "app.db / Postgres", "id, title, category, target_role, difficulty, questions (JSON), passing_score", "Categorized diagnostic screening quizzes"),
        ("assessment_attempts", "app.db / Postgres", "id, candidate_id, quiz_id, score, percentage, answers, feedback, passed", "Historic candidate assessment performance records"),
        ("coach_roadmaps", "app.db / Postgres", "id, candidate_id, title, target_company, milestones (JSON), progress_percentage", "Personalized week-by-week AI coaching roadmaps"),
        ("mock_interviews", "app.db / Postgres", "id, candidate_id, company_name, target_role, session_state, questions, feedback, overall_score", "Full multi-question practice and evaluation sessions"),
    ]
    for row_idx, item in enumerate(db_data, start=18):
        for col_idx, val in enumerate(item, start=1):
            c = ws4.cell(row=row_idx, column=col_idx, value=val)
            c.border = thin_border
            c.font = font_bold if col_idx == 1 else font_data
            if row_idx % 2 == 1:
                c.fill = fill_zebra_light

    for col in ws4.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws4.column_dimensions[col_letter].width = max(max_len + 3, 16)

    # Save workbook
    output_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "AAIRO_Project_30Days_Done_And_Next_10Days_Roadmap.xlsx"))
    wb.save(output_path)
    print(f"Successfully generated project tracker workbook at: {output_path}")

if __name__ == "__main__":
    build_excel_workbook()
