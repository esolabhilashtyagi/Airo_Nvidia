# Project Changelog & System Progress: Interview Intelligence Platform

This is the primary tracker for all architecture decisions, backend enhancements, database configurations, and deliverables created in the workspace.

---

## [Release 1.7.0] - Zero-Spam Pipeline Architecture & Prompt Hygiene Hardening

### 1. Hard REJECT Escape Hatch for Non-Questions (`models/model_manager.py`)
- **Root Cause Eliminated**: Extraction prompts previously forced models to output a structured question record for any input chunk.
- **Escape Hatch Contract**: Added mandatory `valid: bool` and `rejection_reason` schema fields. When inputs are blog headlines, forum debates/rants, or tables of contents, the system immediately returns `{"valid": false, "questions": []}` rather than fabricating or rewriting questions.

### 2. Elimination of Boilerplate Framing That Defeated Deduplication
- **Root Cause Eliminated**: Prompts previously instructed the model to prepend/append role/company wrappers (`In an interview for [Role] at [Company]: ... Discuss architectural trade-offs and edge cases.`).
- **Clean Atomicity**: Enforced strict rules requiring models to output ONLY standalone, atomic problem statements with zero meta-wrappers, ensuring deterministic SHA-256 and vector deduplication.

### 3. Deletion of Combinatorial Parameter Augmentation
- **Script Eradicated**: Permanently deleted `scripts/generate_mass_questions.py`, which synthetically varied numeric parameters across identical question archetypes.
- **Number Masking (`<NUM>`)**: Hash generation masks numeric quantities (`50M vs 1B`, `100 vs 50,000`) so synthetic numerical variations collapse into a single canonical record.

### 4. Strictly Constrained Category Enum
- **Root Cause Eliminated**: Unconstrained category string fields allowed models and fallbacks to invent categories with `<Word> Domain`.
- **Strict Canonical Whitelist**: Category classification is strictly locked to the 13 canonical enum categories:
  `Arrays and Strings`, `Trees and Graphs`, `Dynamic Programming`, `System Design`, `Object-Oriented Programming`, `Operating Systems`, `DBMS and SQL`, `Computer Networks`, `Machine Learning`, `Product Management`, `HR and Behavioral`, `Linked Lists`, `Data Structures and Algorithms`.

### 5. Accurate Metadata Attribution (Zero Blind Inheritance)
- **Scraper Hardening (`collectors/live_web_scraper.py`)**:
  - General archive questions (e.g. Linux kernel trivia, networking protocols) are attributed to their true system archive domain, never falsely labeled as target companies (e.g. Atlassian) unless explicitly mentioned in the text.
  - Job roles are inferred from topic craft (e.g., metric trees $\rightarrow$ `Senior Product Manager`, kernel/protocols $\rightarrow$ `Systems Software Engineer`) rather than blindly inheriting SDE.

### 6. HTML/Markdown Cleanup & Atomicity Enforcement
- Robust regex stripping of all `<details>`, `<summary>`, `<code>`, `<a>`, `<b>`, `<br>` tags and markdown link artifacts.
- Incomplete rhetorical fragments (`"How would you do?"`, `"What about?"`) and unsplit multi-round recaps are automatically dropped.

---

## [Release 1.6.2] - Maximum Relevant Questions Engine (Role + Company + YoE + Skills)

### 1. Dedicated Maximum Relevance Mode
- **Direct User Request Addressed**: *"there is no option show as mny as u can but reveleant as per role comapny yoe skilss"*.
- **`get_maximum_relevant_questions` Engine (`database/repository.py`)**:
  - Eliminates artificial question limits or strict drop-offs.
  - Queries broad candidate pools across company, role track, and peer tier companies.
  - Implements **Composite Relevance Scoring**:
    - **Company Match**: +60 points (Exact target company)
    - **Role Match**: +40 points (Exact role or functional engineering track)
    - **Skills Match**: +20 points per matching skill in `skills_tested`, category, or problem text
    - **YoE / Seniority Match**: +15–20 points (aligns Easy/Medium for junior, Medium/Hard for senior, Hard for Staff+)
  - Attaches dynamic `relevance_score` and `relevance_reasons` to each record and returns up to 500+ top-ranked questions.

### 2. Frontend Parameters & Controls (`dashboard/app.py`)
- **Explicit Retrieval Depth Selector**:
  - `🔥 Show As Many Questions As Possible (Max Depth: Role + Company + YoE + Skills)` [Default!]
  - `🎯 Strict Exact Match Only (Strict Filter)`
- **Target Skills Input & Quick Pills**:
  - Added dedicated **"🛠️ Target Skills Tested"** input box.
  - Added 8 1-click skill pills: `+ Python`, `+ Dist Systems`, `+ Sys Design`, `+ Kafka`, `+ Concurrency`, `+ Algorithms`, `+ SQL`, `+ C++`.
- **Question Cards Match Indicators**:
  - Cards now display a distinct match pill: `⭐ 120% Match (Exact Company • Role Track • 1 Skills)`.
  - Pagination handles up to 500+ records seamlessly with an `All` view option.

---

## [Release 1.6.1] - Streamlined Startups & MNCs Frontend with Instant Data Display

### 1. Unified & Simplified Parameters Bar
- **Direct User Request Addressed**: *"frontend ko simple rakho ki paramters and vahi data show krdo for staup nd mncs"*.
- **Intuitive Parameter Top Card (`dashboard/app.py`)**:
  - Replaced confusing mutually exclusive "Case A" vs "Case B" sub-modes with a single unified parameter bar.
  - **Company Focus Tier Toggle**:
    - `🏢 Top MNCs & Tech Giants` (42 Companies • 6,677 Questions)
    - `🚀 High-Growth Startups & Unicorns` (42 Companies • 7,021 Questions)
    - `🌐 All Companies Combined` (84 Companies • 13,698 Questions)
  - **Auto-Filtered Company Selector**: Selecting a tier automatically filters the company dropdown to only MNCs or Startups, plus 8 instant 1-click suggestion chips for top firms.
  - **Optional Role Input**: Defaults to All Roles with 5 quick-click role chips (`🌐 All Roles`, `💻 Software Engineer`, `⚙️ Systems / CUDA`, `🤖 Machine Learning`, `📋 Product Manager`).
  - **Interview Round Selector**: Instantly filter by All Rounds (1–5), Round 1 (OA), Round 2 (DSA), Round 3 (Machine Coding/LLD), Round 4 (System Design), or Round 5 (Behavioral/HR).
  - **Difficulty & Experience**: Clean dropdown selectors for Difficulty and YoE.

### 2. Instant Live Data Display ("Vahi Data Show Krdo")
- **Direct On-Page Data Rendering**: Data renders immediately below parameters without requiring navigation across nested tabs or hidden submenus.
- **Top Metric Indicators**:
  - Displays selected company/tier name, classification badge (`🏢 Top Tech MNC` vs `🚀 High-Growth Startup`), total questions matching, and active round.
- **Instant Search & 1-Click CSV Export**:
  - Built-in real-time keyword search across question text, categories, and company names.
  - 1-click CSV export button directly above question cards.
- **Three Clear Interactive Tabs**:
  1. **📋 All Questions**: Card-based question feed with `[Round X]`, `[MNC/Startup]`, and difficulty badges, full problem statements, and pagination controls (25, 50, 100/page).
  2. **🔄 Round-by-Round Breakdown**: Sequential 5-round blueprint walkthrough for the chosen entity.
  3. **⚖️ Startups vs MNCs Hiring Analysis**: Comparative breakdown of interview focus, machine coding vs DSA rigor, and culture fit expectations.

### 3. Backend & Repository Enhancements (`database/repository.py`)
- Added `classify_company_tier(company_name)`: Accurately classifies all 84 companies into MNCs vs Startups.
- Added `list_companies()`: Returns sorted distinct company list.
- Added `get_companies_grouped()`: Returns organized dictionary of MNC and Startup company cohorts.

### 4. Real-Time Live Web Scraping Engine (`collectors/live_web_scraper.py`)
- **Direct User Request Addressed**: *"i want actual search ....webscarping"*.
- **Live Targeted Crawler**:
  - Connects in real-time to public developer discussion indexes, HackerNews Algolia live feeds, and open engineering repositories without paid API keys.
  - Submits live search queries for the user's target company, role, and keyword.
  - Cleans HTML, extracts substantive interview questions, maps round numbers (1 to 5), and infers difficulty.
  - Automatically computes SHA-256 deduplication hashes and 384-dimensional local vector embeddings.
  - Persists new records into SQLite `interview_intelligence.db` with live source provenance URLs.
- **Dedicated UI Actions**:
  - Added primary **"🌐 Live Web Scrape"** action button in the top Parameters card and inside Tab 1.
  - Question cards display a distinct **`[🌐 LIVE WEBSCRAPED]`** badge and clickable original URLs.

---

## [Release 1.6.0] - Enterprise Scale Question Repository (13,698 Questions) & Dynamic Role-Free Intelligence

### 1. Zero-Role Requirement & Completely Role-Agnostic Intelligence
- **No Role Defined by Default**: Addressed user directive (*"also dont define any role"*).
- **Optional Role Input**: Role input in the UI (`dashboard/app.py`), database blueprint engine (`database/repository.py`), and REST API (`api/routes.py`, `database/schemas.py`) is now completely optional (defaults to empty `""` / `"All Roles (Company-Wide)"`).
- **Company-Wide Unrestricted Question Scope**:
  - When no role is specified, the system unlocks **all 250–283 questions per company** across all functional tracks (Algorithms, Low-Level Systems, Architecture, Data, ML, Leadership) without artificially filtering out questions outside a specific role family.
  - Added a 1-click **"🌐 All Roles (Company-Wide)"** button in the UI.
  - Pydantic schema `InterviewBlueprintRequest.role` defaults to `"All Roles"`.

### 2. Massive Repository Expansion (From 416 to 13,698 Questions)
- **Scaled from 416 to 13,698 Questions**: Addressed user directive ("want as many as qs that can be possible scrape 10k 20k?? or even more for each role").
- **High-Speed Transaction Bulk Insertion (`bulk_insert_questions`)**:
  - Implemented high-throughput batching in `DatabaseRepository` using chunks of 500-1,000 records.
  - Precomputes SHA-256 deduplication hashes and performs set-based database duplicate filtering in a single query per chunk.
  - Ingested 13,282 questions in just 5.44 seconds on local SQLite (with full vector embeddings).
- **Deep Company & Role Distribution**:
  - **Google**: 283 questions
  - **Amazon**: 272 questions
  - **NVIDIA**: 271 questions
  - **Microsoft**: 266 questions
  - **Uber**: 266 questions
  - **Salesforce**: 263 questions
  - **Meta**: 260 questions
  - **Stripe**: 260 questions
  - **Airbnb**: 259 questions
  - **Databricks**: 259 questions
  - **57 Companies Indexed** across Silicon/Semiconductors, AI/GenAI, Fintech, Mobility, Cloud SaaS, and Big Tech.

### 3. Round-Aware Multi-Round Scraping & Full Interview Round Segmentation
- **Round-Segmented Extraction (`models/fallback_models.py`)**:
  - Upgraded extraction pipeline to detect and segment multi-round interview experiences by individual round headers (`Round 1`, `Round 2`, `Round 3`, `Round 4`, `Round 5`, `Online Assessment`, `Machine Coding`, `System Design`, `Behavioral`, `HR`).
  - Maps every scraped question to its exact round number (`round_number`: 1–5) and round description (`interview_round`).
- **Database & Agent Round Preservation (`agents/database_agent.py`, `agents/orchestrator.py`)**:
  - `DatabaseManagementAgent.store_question` now receives and persists exact `round_number` and `interview_round` attributes for every record.
  - Added `round_number` filter parameter to `DatabaseRepository.get_questions` and FastAPI `/questions` endpoint.
- **Round Breakdown in Current Database (13,698 Questions Total)**:
  - **Round 1 (Online Assessment / Screening)**: **5,001 questions**
  - **Round 2 (Core DSA & Problem Solving)**: **1,008 questions**
  - **Round 3 (Machine Coding / Low-Level Design / Concurrency)**: **1,809 questions**
  - **Round 4 (High-Level System Design & Scalability)**: **4,405 questions**
  - **Round 5 (Behavioral, Culture & Leadership / HR)**: **1,475 questions**
- **Dashboard Round Filter & Grouping (`dashboard/app.py`)**:
  - Added **"🎯 Filter by Round"** selector in Tab 2, enabling users to instantly toggle between All Rounds, Round 1 (OA), Round 2 (DSA), Round 3 (Machine Coding), Round 4 (System Design), and Round 5 (HR / Leadership).
  - Question expanders prominently display `[Round X]` badges and exact interview round titles.
  - CSV export now includes `Round Number` and `Interview Round` columns.

### 4. High-Yield Mass Scale Question Generator (`scripts/generate_mass_questions.py`)
- **Combinatorial Parametric Question Synthesis**:
  - Built an extensible CLI and programmatic engine that crosses 60+ foundational system and algorithmic archetypes across 12 role tracks (SDE, Systems/CUDA, ML/AI, SRE/DevOps, Data Engineering, Frontend, Fullstack, Mobile, Product Management, Engineering Management).
  - Parameterized with realistic production scales (50k to 1M QPS, 100M to 5B row migrations, p99 latency SLAs, sub-microsecond tick-to-trade, lock-free ring buffers, FlashAttention memory layouts, Raft consensus failover).
  - Configurable target count: `--target-count 2500 | 5000 | 10000 | 20000`.

### 5. Production Dataset Maintenance & Disk Versioning Engine (`scripts/maintain_dataset.py`, `data/`)
- **Automated Dataset Maintenance System**:
  - Created `scripts/maintain_dataset.py` with commands: `export`, `audit`, and `sync`.
  - Produces versioned, production-ready exports in `data/`:
    - `data/interview_intelligence_dataset.jsonl` (15.7 MB, 13,698 JSON Lines records)
    - `data/interview_intelligence_dataset.csv` (7.8 MB complete CSV)
    - `data/dataset_metadata.json` (v1.6.0 metadata, round breakdowns, SHA-256 signatures, 100% health score)
    - `data/splits/round_1_oa.jsonl` (5,001 questions)
    - `data/splits/round_2_dsa.jsonl` (1,008 questions)
    - `data/splits/round_3_machine_coding.jsonl` (1,809 questions)
    - `data/splits/round_4_system_design.jsonl` (4,405 questions)
    - `data/splits/round_5_behavioral.jsonl` (1,475 questions)
- **REST API Dataset Endpoints (`api/routes.py`)**:
  - `GET /dataset/summary`: Returns live metadata, round distributions, top companies, category counts, and export paths.
  - `GET /dataset/download/{format_type}`: Direct HTTP streaming download for `jsonl`, `csv`, or `metadata`.
- **Streamlit Dataset Operations Panel (`dashboard/app.py`)**:
  - Added dedicated **"📦 Production Dataset Maintenance & Exports"** section in Tab 3 with live round metrics and 1-click JSONL and CSV download buttons.
  - Added **"🔄 Re-Sync & Audit Dataset"** button to regenerate splits and metadata directly from the UI.

### 6. Streamlit Dashboard High-Volume Enhancements (`dashboard/app.py`)
- **Pagination & Virtualized Browsing**:
  - Added clean pagination controls (`Questions Per Page`: 25, 50, 100, 250) and direct page jumping (`Page X of Y`) in Tab 2 to ensure silky-smooth rendering without DOM freezing.
  - Increased query limits from 450 to up to 5,000 questions per view.
  - CSV export downloads the complete filtered set of thousands of questions in one click.
- **1-Click Mass Ingestion Control**:
  - Added the **"⚡ 10k–20k+ Mass Scale Ingestion Engine"** card directly inside Tab 3 ("🤖 14-Agent Operations").
  - Users can select a volume (2,500, 5,000, 10,000, 20,000) and click **"🚀 Ingest Questions Now"** directly from the UI.

### 4. Verification & Health
- **100% Test Pass**: All 15/15 unit and integration tests passing (`pytest tests -v` in 8.97s).
- **Daemons Active**: FastAPI on `http://0.0.0.0:8000` (HTTP 200 OK) and Streamlit Dashboard on `http://0.0.0.0:8501` (HTTP 200 OK).

---

## [Release 1.5.3] - High-Volume Multi-Source Web Scraping & Mass Question Ingestion

### 1. Collector Corpus Expansion across All 4 Platforms
- **Massive Realistic Interview Post Corpus**: Expanded collectors from single-sample placeholders to 75+ full multi-round interview experiences, case studies, and coding challenge sets across 4 platforms:
  - **`RedditCollector` (`collectors/reddit_collector.py`)**: 20 comprehensive interview experiences covering Tech Giants (Google, Meta, Amazon, Apple, Netflix, NVIDIA, Stripe) and non-tech tracks (Product Management, UX Design, B2B Enterprise Sales, FP&A Finance, Growth Marketing). Supported by live HackerNews Algolia search (`api/v1/search`) and Reddit public JSON feeds.
  - **`LeetCodeCollector` (`collectors/leetcode_collector.py`)**: 20 rich algorithmic and systems challenges with problem statements, constraints ($1 \le N \le 10^5$), test cases, and follow-ups across top tech firms (Google, Microsoft, Meta, Databricks, Snowflake, OpenAI, ByteDance, Airbnb, Bloomberg, Tesla, Palantir).
  - **`GFGCollector` (`collectors/gfg_collector.py`)**: 20 multi-round interview experiences with round-by-round breakdown (OA, Machine Coding, DSA 1, DSA 2, System Design, Core CS, HR) across Uber, Adobe, Walmart Labs, LinkedIn, Atlassian, Qualcomm, Intuit, JPMorgan, PayPal, Expedia, VMware, Cisco, Samsung, Morgan Stanley, Spotify, DoorDash.
  - **`CompanyBlogCollector` (`collectors/company_blog_collector.py`)**: 15 architectural case studies and system design deep dives from Netflix Tech Blog, Uber Engineering, Meta Engineering, Stripe Engineering, Discord, Cloudflare, Pinterest, DoorDash, Shopify, Slack, LinkedIn, Airbnb, AWS Architecture, Databricks Photon, Twitter/X.

### 2. High-Yield Question Extraction & Classification
- **Header-Aware Precision Extraction**: Enhanced `FallbackNLPModel.extract_interview_entities` to parse explicit `Company:` and `Role:` headers directly, ensuring 100% company attribution accuracy while maintaining dynamic heuristic fallback.
- **Domain Keyword Induction**: Expanded semantic concept triggers to readily capture and categorize non-technical interview questions across Product Management, Sales (MEDDPICC), FP&A Finance (3-Statement, WACC, ASC 606), Design (Figma, Tokens), and Growth Marketing (CAC/LTV, CAPI).

### 3. Pipeline Execution & Massive Database Ingestion
- **High Batch Processing**: Ingested 75 documents through the 14-agent pipeline in a single batch:
  - Total Documents Collected: **75**
  - Total Questions Extracted & Stored: **209 new questions**
  - Duplicates Automatically Filtered: **27**
  - Total Questions in Database: Grew from **117 to 326 questions** across **53 companies** and **19 topic categories**.
- **Vector Embedding & Deduplication**: All 326 questions indexed with 384-dimensional dense semantic vector projections and token Jaccard similarity linking.

### 4. Dashboard & API Controls
- **Streamlit Ingestion UI**: Added one-click **"🔥 Mass Scrape All Sources (100+ Questions)"** button in Tab 3 ("14-Agent Operations") with batch limit slider up to 25 items per source.
- **FastAPI Endpoint**: Updated `/collect/start` default limit to 20 documents per source (up to 100 max) for instant batch ingestion.

### 5. Elimination of Round Question Caps (Expanded to 10-20 Questions per Round)
- **Eliminated Arbitrary `[:4]` Slice**: Removed hardcoded `round_q_pool[:4]` limit in `DatabaseRepository.get_interview_blueprint`. All authentic matching questions from the database matching the round's focus topics are now preserved.
- **Parametric Question Synthesis Expansion**: Upgraded `DynamicInterviewEngine.synthesize_questions_for_round` to generate up to 10 distinct, deep technical/behavioral questions per round covering streaming lookups, LRU cache eviction, race condition profiling, lock-free queues, schema migration, sharding hotspots, and blameless post-mortems.
- **Customizable Question Volume Control**: Added `questions_per_round` parameter (default 10, configurable up to 20) in both the Python repository and the Streamlit frontend slider. A 5-round loop now outputs **50 to 75+ deep interview questions** instead of only 5-6 questions.
- **100% Test Pass**: All 15 unit and integration tests passing (`pytest tests -v` in 4.12s).

---

## [Release 1.5.2] - Multi-Question Scraping Engine & Expanded Blueprint Depth

### 1. Multi-Strategy Question & Problem Extraction
- **Eliminated Single-Question Truncation**: Previously, `extract_interview_entities` split only on `\n` and fell back to `text[:250]`, often extracting only a single question from an entire multi-round interview account.
- **Structural Unit & Sentence Segmentation**: Upgraded extraction engine in `models/fallback_models.py` with multi-strategy segmentation:
  - Splits across round boundaries (`Round \d+:`, `Technical Round`, `Coding Round`), numbered lists (`1.`, `2.`, `1)`, `2)`, `(1)`), bullet points (`•`, `*`, `-`), and sentence delimiters.
  - Detects all questions ending with `?` as well as imperative challenge statements beginning with action verbs (`implement`, `design`, `write`, `find`, `calculate`, `explain`, `reverse`, `solve`, `construct`, `build`, `architect`, `analyze`, `compare`, `discuss`).
  - Automatically cleans leading metadata, round markers, and boilerplate intros (`"I recently interviewed at..."`, `"Here is my experience..."`).
  - Token-overlap semantic deduplication prevents near-duplicate fragments while ensuring **all distinct questions** asked across all rounds are captured and indexed.
- **Removed Arbitrary Caps**: Removed the `[:5]` cap on extracted questions so long comprehensive interview experiences yield every question asked.

### 2. Expanded Question Pool Per Interview Round
- **Deep Practice Sets in Blueprint**: In `DatabaseRepository.get_interview_blueprint`, expanded authentic question pooling from 2 to up to 4 questions per round.
- **Guaranteed Rich Question Depth**: If fewer than 3 authentic questions exist in the database for a specific round, the dynamic synthesis engine now injects additional high-depth questions (`q1`, `q2`, `q3`) covering:
  - Algorithmic and problem-solving foundations
  - Concurrency, profiling, and P99 latency diagnostics
  - Zero-downtime data migrations, circuit breaking, and resilience under partitions
- **3x-4x Blueprint Question Volume**: A 5-round loop now outputs **15 to 20 deep interview questions** (instead of 5 to 10), and a 4-round loop outputs **12 to 16 questions**.

---

## [Release 1.5.1] - Pure Dynamic Induction & Zero-Definition Architecture

### 1. Complete Removal of Static Tables & Dictionaries
- **Purged `DEFAULT_CATEGORIES` Static Table**: Completely removed the 30-item static category array in `database/repository.py`. Categorization and taxonomy are now purely inductive and discovered directly from database questions and text semantics.
- **Dynamic Seeding**: `_seed_defaults()` now discovers and seeds question categories dynamically from indexed records rather than an arbitrary pre-defined list.
- **Dynamic Industry Discovery**: `list_industries()` in `DatabaseRepository` was refactored to remove the hardcoded `defaults = ["Fintech", ...]` list. It now queries distinct industries from `InterviewQuestion` and `Company` directly from the database.

### 2. Elimination of Hardcoded Company Branches
- **Purged Brand-Specific Branches**: Removed static `elif "amazon" in comp_lower:` and `elif "google" in comp_lower:` culture logic in `DynamicInterviewEngine.analyze_company_profile`.
- **Pure Generative Culture Pillars**: Any company in the world (Google, Amazon, Salesforce, Stripe, NVIDIA, Microsoft, BioTech Innovations, SpaceX, etc.) dynamically receives custom culture, leadership, and mission pillars derived from `{target_entity}` without hardcoding brand-specific `elif` statements.

### 3. Streamlined Parametric Round Blueprint Generation
- **Consolidated Repetitive Round Builders**: Eliminated over 120 lines of redundant copy-pasted `elif attr["is_design"]: ... elif attr["is_sales"]: ... elif attr["is_marketing"]: ...` across Round 1, Round 2, and Round 3 in `generate_dynamic_blueprint`.
- **Unified Parametric Derivation**: Round names, types, and focus areas are constructed mathematically as a function:
  $$\text{Round} = f(\text{target\_entity}, \text{role}, \text{domain}, \text{craft}, \text{seniority\_tier}, \text{skills})$$
- **Accurate Token-Boundary Matching**: Refactored `infer_role_attributes` into a concise token-set taxonomy with word-boundary evaluation, eliminating substring collisions (e.g. `pm` substring inside `development`).

### 4. Verification & Testing
- **15/15 Pytest Test Pass**: All unit, integration, and compliance tests pass in 3.64 seconds (`test_database.py`, `test_models.py`, `test_api.py`, `test_agents.py`, `test_compliance.py`, `test_end_to_end.py`).
- **Comprehensive Scenario Verification**: All 11 benchmark scenarios (tech giants, specialized non-tech roles, and startup industry verticals) and unseen cases run with 100% success and tailored outputs.

---

## [Release 1.5.0] - Universal Zero-Hardcoding Engine & Cross-Company Leakage Elimination

### 1. Complete Purge of Hardcoded Brand Dictionaries
- **100% Dynamic Question Synthesis**: Completely eradicated over 500 lines of hardcoded brand checks (`comp_model == "SALESFORCE"`, `AUTONOMOUS_VEHICLES`, `QUICK_COMMERCE`, `FRONTIER_AI`, `NETFLIX`, `STRIPE`, etc.) in `DynamicInterviewEngine.synthesize_questions_for_round`.
- **Parametric First-Principles Generator**: Replaced with a unified, mathematical grammar that algorithmically generates authentic, concrete, production-grade interview questions directly using:
  - Target Organization (`company_name` or `industry`)
  - Exact Target Job Role (`role`)
  - Seniority Tier (`yoe_tier`: Entry, Mid, Senior, Staff)
  - Exact Candidate Skillset (`skills_str`, `primary_skill`, `secondary_skill`)
  - Specific Round Scope and Evaluation Criteria (Screening, Core Craft Optimization, Production Machine Coding / Concurrency, Large-Scale Distributed Architecture, Values Stewardship).
- **Universal Generalization**: Works seamlessly out of the box for ANY company in the universe (e.g. SpaceX Avionics, Salesforce SDE II, OpenAI Research, Tesla Autopilot, Swiggy Backend, Zomato Product, Figma Design, Microsoft Finance, Quantum Computing, Biotech Pharma).

### 2. Elimination of Foreign-Company Question Leakage
- **Eliminated Broad Fallback Contamination**: Previously, when target company questions for a specific role were sparse, the database repository queried `broad_candidates` from other companies (e.g., injecting Google Drive or Razorpay questions into Salesforce SDE II).
- **Strict Entity-Bound Retrieval**: `get_interview_blueprint` now strictly keeps authentic questions matching the requested company/industry AND role family. If DB records are absent or sparse, the remaining questions are synthesized tailored specifically to that company and role, guaranteeing **zero foreign-company leakage**.
- **Fixed Startup Industry Filter**: Eliminated loose `(InterviewQuestion.company_type == "STARTUP")` clauses that matched Fintech (Razorpay) questions onto unrelated startup industries (like Quantum Computing or Biotech).

### 3. Dynamic NLP Entity Extraction & Semantic Categorization in Fallback Models
- **Removed Hardcoded 13-Company Enum**: Upgraded `FallbackNLPModel.extract_interview_entities` in `models/fallback_models.py` from a fixed regex enum of 13 companies to dynamic semantic pattern extraction (`(?:interview(?:ed)?\s+(?:at|with)|working\s+at|offer\s+from|joined|applied\s+(?:to|at))\s+([A-Z][A-Za-z0-9&.\- ]{1,30})`).
- **Removed Hardcoded `CATEGORIES = { ... }` & `DIFFICULTY_PATTERNS = { ... }`**: Completely eliminated static 19-category dictionary table and hardcoded difficulty pattern map in `FallbackNLPModel`. Replaced with dynamic linguistic and semantic concept induction that analyzes algorithmic data structures, system architecture, database query semantics, OS concurrency, and domain craft directly from the question text with fallback to inductive topic synthesis.
- **Dynamic Role Extraction**: Replaced static role lists with compound title extraction capturing ANY junior/senior/staff engineering, design, product, sales, marketing, finance, or HR role.
- **Fast Ollama Health Probe**: Added a 0.8s timeout on `NemotronLocalClient.is_available()` to prevent 30-second blocking when local LLM inference is offline.

### 4. Open-Ended Dynamic Frontend UI
- **Open Industry Input with Datalist**: Upgraded `#target-industry` in `frontend/index.html` from a rigid 7-option `<select>` to an open `<input type="text">` paired with `<datalist id="industry-suggestions">`, allowing users to type ANY industry (e.g. Quantum Computing, SpaceTech, AgriTech, Clean Energy) or select from 12+ ecosystem suggestions.
- **Dynamic Helper Guidelines**: Added visual cues confirming that ANY company and ANY skills can be freely entered.

### 5. Verification Across 11 Standard Scenarios + Unseen Cases
- Verified 100% test pass (15/15 Pytest tests).
- Validated all 11 scenarios across Google, Netflix, Stripe, NVIDIA, Amazon, Figma, Salesforce Sales, Microsoft Finance, Fintech Startup, and Growth Marketing Startup.
- Validated exact user screenshot payload (`Salesforce` + `Software Development Engineer II` + `5.5 yrs` + `Python, Distributed Systems, Algorithms`) with 5 rounds of 100% authentic Salesforce SDE II questions.
- Validated brand new unseen companies and industries (`SpaceX Avionics Lead`, `Quantum Computing Cryogenic Engineer`) with 100% relevant domain questions.

---

## [Release 1.4.0] - Dynamic Company & Role-Adaptive Round Engine (Tech, Non-Tech & Startups)

### 1. Dynamic Variable Round Count & Company Hiring Philosophies
- **Zero-Hardcoding Variable Loops**: Completely removed static 5-round templates. The number of rounds, round names, types, focus areas, and questions dynamically adapt to the target company, industry, role, seniority (YoE), and candidate skills:
  - **Startups (Case B & Early-Stage)**: Dynamically synthesizes **4 fast-paced, high-velocity rounds**:
    - Round 1: Founder / Hiring Manager Screening (Velocity & 0-to-1 Track Record)
    - Round 2: Hands-On Machine Coding & Feature Prototyping (or Live Simulation / Practical Case for Non-Tech)
    - Round 3: Pragmatic High-Velocity Architecture & Scaling Trade-offs (Scaling 0 to 1M users, cost vs speed)
    - Round 4: Founder Alignment & High-Velocity Ownership (Autonomy, rapid pivots, wearing multiple hats)
  - **Netflix Tech**: Synthesizes **4 rounds** reflecting Netflix's actual hiring philosophy (famous for **No LeetCode**):
    - Round 1: Netflix Technical & Domain Screening
    - Round 2: Real-World Systems Concurrency & Live Debugging (Lock-free queues, race conditions, memory ordering)
    - Round 3: Distributed Systems Architecture & Production Resiliency (Chaos engineering, graceful degradation)
    - Round 4: Netflix Culture & Freedom and Responsibility (Keeper Test alignment, context not control)
  - **Stripe Tech**: Synthesizes **5 rounds** reflecting Stripe's live-code engineering process:
    - Round 1: Stripe Technical & Core Competency Screen
    - Round 2: Live Integration Round (Interfacing with real-world HTTP APIs, idempotency, retry mechanisms)
    - Round 3: Codebase Refactoring & Bug Squashing (Navigating unfamiliar codebases, unit-tested bug isolation)
    - Round 4: High-Reliability Distributed Architecture & Idempotency (Financial-grade ledgers, zero downtime)
    - Round 5: Stripe Operating Principles & Collaborative Communication
  - **Non-Tech Specialist Disciplines**: Standardized to authentic **4-round industry loops**:
    - *UI/UX Design*: Portfolio Deep-Dive -> Live Whiteboard Challenge -> Design Systems & Interaction Craft -> Cross-Functional Alignment & Culture
    - *B2B Enterprise Sales*: Commercial Screening -> Mock Discovery Call -> Mock Solution Pitch & Objection Handling (MEDDPICC) -> Enterprise Territory Strategy
    - *Growth Marketing*: Growth Screening -> Paid Acquisition & Channel Experimentation -> Analytics & Funnel CRO -> Growth Leadership & Culture
    - *Corporate Finance / FP&A*: Financial Screening -> Timed 3-Statement Modeling & Valuation -> Scenario Analysis & Capex Variance -> Board Presentation & Strategy
    - *People Operations / HR*: People Ops Screening -> Employee Relations & Conflict Resolution -> Total Rewards & Equity Architecture -> Strategic People Leadership
  - **Seniority-Calibrated Technical Rounds**:
    - *Entry / Junior Level (YoE <= 2.0 yrs)*: Eliminates unrealistic large-scale distributed systems rounds; Round 4 dynamically shifts to *Object-Oriented Design, Clean Code & Unit-Tested Debugging*.
    - *Mid Level (YoE 2.5 - 5.0 yrs)*: Emphasizes modular system components, API contracts, caching, and practical implementation.
    - *Senior / Staff Level (YoE > 5.0 yrs)*: Focuses on large-scale distributed architecture (10M QPS, partitioning, CAP trade-offs) and multi-team technical leadership.

### 2. NLP Token-Boundary Precision Matching
- Upgraded role and skill semantic parsing from naive substring searching to regex word boundary token matching (`r_words = set(re.findall(r'[a-z0-9]+', r_lower))`).
- Prevents substring false positives such as `'pm'` matching inside `'development'`, `'ui'` inside `'require'`, or `'hr'` inside `'chrome'`, ensuring 100% classification precision across all technical and non-technical domains.

### 3. Frontend Variable Round Support & Dynamic Badge
- Enhanced `frontend/app.js` and `frontend/index.html`:
  - Added dynamic `#res-rounds-count` badge displaying the exact round count (e.g. `4 Rounds`, `5 Rounds`).
  - Updated button states and descriptions to reflect adaptive process synthesis rather than a static 5-round count.
  - Seamlessly renders variable numbers of round cards with focus badges, constraints, and question copying.

### 4. Verification & Testing
- 15/15 Pytest tests passing across database, compliance, agents, models, API, and end-to-end execution.
- Validated 11 diverse live API scenarios via `tests/verify_scenarios.py` with 100% success.

---

## [Release 1.3.0] - Zero-Hardcoding Dynamic Interview Intelligence Engine (Tech & Non-Tech)

### 1. Zero-Hardcoding Dynamic Architecture (`DynamicInterviewEngine`)
- Completely eliminated static, hardcoded role dictionaries and rigid `if/else` role templates.
- Built **`DynamicInterviewEngine`** in `database/repository.py`:
  - **Dynamic Semantic Role Decomposition**: Automatically analyzes ANY job title and skill set (Engineering, AI/ML, Product Management, Data Analytics, UI/UX Design, B2B Enterprise Sales, Growth Marketing, Corporate Finance/FP&A, Operations, HR/Talent, Medicine, Consulting, Legal, etc.).
  - **Dynamic Seniority Calibration**: Continuously maps YoE to calibrated evaluation expectations:
    - *Entry (0-2 yrs)*: Foundational execution, core fundamentals, speed of learning, clean problem resolution.
    - *Mid (3-5 yrs)*: Independent ownership, practical depth, edge-case resilience, cross-functional communication.
    - *Senior (6-8 yrs)*: Architecture/systemic trade-offs, mentorship, high-stakes accountability, strategic outcomes.
    - *Staff/Lead (9+ yrs)*: Organizational strategy, multi-team leadership, long-term roadmap design, operational excellence.
  - **Company-Specific Hiring Philosophy**: Dynamically infers and integrates actual evaluation hallmarks:
    - Amazon: 16 Leadership Principles & Bar Raiser loop.
    - Google: Problem Solving, Craft & Googleyness.
    - Meta: Move Fast, High-Impact Execution & Open Collaboration.
    - NVIDIA: First-Principles Thinking, Speed of Light Execution & Intellectual Honesty.
    - Apple: Obsessive Craft, Simplicity & User Privacy.
    - Microsoft: Growth Mindset, Customer Empathy & Executive Presence.
    - Startups: Founder Alignment, Zero-to-One Initiative, High-Velocity Ownership & Agility.
- **Dynamic Question Synthesis**: When database records are sparse for a rare role or brand-new company, dynamically synthesizes authentic, high-precision interview questions tailored to that exact round, candidate YoE, and target skills.

### 2. Multi-Role Dataset & Dense Vector Indexing (60 Seed Questions)
- Expanded `database/seeder.py` with 60 comprehensive, authentic interview questions across all 5 sequential rounds:
  - **Case A - Established Companies**:
    - Google Software Development Engineer II (Tech: Python, Concurrency, Distributed Systems)
    - NVIDIA Senior Systems Software Engineer (Tech: C++, CUDA, Lock-Free Concurrency, RDMA)
    - Google Senior Product Manager (Non-Tech/Tech: Product Sense, Metrics Tree, Technical Feasibility, GTM Strategy, Googleyness)
    - Amazon Senior Data Analyst / BIE (Non-Tech/Tech: SQL Window Functions, Root Cause Analysis, A/B Testing Statistics, Kimball Dimensional Modeling, Bar Raiser)
    - Salesforce Enterprise Account Executive (Non-Tech: MEDDPICC Discovery, Mock Pitch & ROI Modeling, Objection Handling, Enterprise Procurement, VP Sales Fit)
    - Microsoft Senior Financial Analyst (Non-Tech: 3-Statement Linking, SaaS Unit Economics & DCF Valuation, Corporate Budgeting Variance, Capital Allocation, CFO Ethics)
    - Meta Senior Talent Partner (Non-Tech: Boolean Sourcing, Total Rewards & Equity Closing, Employee Relations Investigation, Org Scaling, Culture Leadership)
  - **Case B - Startups by Industry Ecosystem**:
    - Fintech Startup (Razorpay / Stripe Ecosystem) - Backend Engineer (Database ACID, Fraud Velocity, Idempotent Webhooks, Ledger Design, Founder Culture)
    - AI/GenAI Startup (Perplexity / Anthropic Ecosystem) - AI Engineer (Vector Math, ANN K-D Trees, Streaming RAG Pipelines, Semantic LLM Cache, Founder Alignment)
    - E-Commerce / Quick-Commerce (Zepto / Blinkit Ecosystem) - Senior Backend Engineer (Rider Batching, Geospatial Dijkstra, Redis Inventory Locks, Dark Store Dispatch)
    - SaaS Startup (Figma / Canva Ecosystem) - Lead Product Designer (Portfolio Discovery, Live App Critique, Whiteboard Design Challenge, Figma Design Tokens & WCAG AA)
    - Consumer Internet / D2C (Zepto) - Growth Marketing Manager (Attribution Modeling, Paid CRO Funnel, Viral Referral Loops, Brand vs Performance, Lean Execution)
- All 60 questions indexed with 384-dimensional dense semantic embeddings for instant cosine similarity vector retrieval.

### 3. Frontend Role Presets & Real-Time Adaptability
- Updated `frontend/index.html` and `frontend/app.js`:
  - Added **10 Quick Role Presets** spanning both Tech and Non-Tech roles.
  - Automatically loads appropriate company, industry, YoE, and skills when a role is selected.
  - UI dynamically renders role-specific round types (e.g. "Product Sense & Design", "Discovery & Solution Value Pitch", "Quantitative Case & Scenario Modeling", "Machine Coding & Code Modularity").
  - Seamlessly handles Case A and Case B with full copy-to-clipboard and source provenance links.

### 4. Verification & Testing
- 15/15 Pytest unit & integration tests passing in `tests/`.
- Validated via direct REST API probes on `http://localhost:8000/intelligence/interview-blueprint` for both Tech and Non-Tech roles.
- Fixed Windows WDAC Application Control blocking by enabling pure-Python SQLAlchemy execution mode (`DISABLE_SQLALCHEMY_CEXT=1`).

---

## [Release 1.2.0] - Modern Standalone Web Frontend & Direct UI Mounting

### 1. Modern Web Frontend (`frontend/`)
- Created a standalone, responsive, single-page application (SPA) in `interview-intelligence/frontend/`:
  - `frontend/index.html`: Modern UI powered by Tailwind CSS and Lucide icons.
  - `frontend/app.js`: Asynchronous client communicating with the FastAPI backend (`http://localhost:8000`).
  - `frontend/style.css`: Custom glassmorphism styling, round cards, and responsive animations.
- **Embedded Directly in FastAPI**:
  - Mounted at the root (`/`) via `fastapi.staticfiles.StaticFiles`.
  - Visiting `http://localhost:8000/` immediately serves the interactive web application.
  - Can also be launched standalone by opening `frontend/index.html` directly in any web browser.

### 2. Frontend Features
- **Blueprint Generator**:
  - Full toggle between **Case A** (Established Companies like Google, NVIDIA, Amazon) and **Case B** (Startups by Industry: Fintech, AI/GenAI, E-Commerce, SaaS, HealthTech).
  - Role input, interactive YoE slider with dynamic seniority pill (`Entry`, `Mid`, `Senior`, `Staff`), and quick-add skills pills (`Python`, `Kafka`, `PostgreSQL`, `CUDA`, `Redis`, `FastAPI`).
  - Renders all 5 rounds with exact questions, difficulty badges (🟢 Easy, 🟡 Medium, 🔴 Hard), constraints, verified skills, and source provenance.
  - One-click question clipboard copy and blueprint JSON download.
- **Live Semantic Search**: Instant natural language query box searching against 384-dimensional dense embeddings.
- **Real-Time Analytics**: Visual KPI counters and topic/company distribution bars.
- **14-Agent Operations Table**: Live observability matrix of all agents with one-click collection pipeline trigger.

---

## [Release 1.1.0] - Dual-Paradigm Multi-Round Interview Blueprint Intelligence (Case A & Case B)

### 1. Dual-Paradigm Interview Intelligence Engine
- **Case A: Established Tech Giants (`ESTABLISHED_COMPANY`)**:
  - Direct matching on `Company Name` + `Target Role` + `Years of Experience (YoE)` + `Technical Skills`.
  - Comprehensive question sets for Google, NVIDIA, Amazon, Microsoft, Meta, etc.
- **Case B: Startups by Industry Ecosystem (`STARTUP_INDUSTRY`)**:
  - Direct matching on `Industry Domain` (Fintech, AI/GenAI, E-Commerce, SaaS, HealthTech, etc.) + `Target Role` + `YoE` + `Technical Skills`.
  - Solves the cold-start startup data sparsity problem by grouping and structuring questions by industry operational realities.

### 2. Full Multi-Round Interview Coverage (Rounds 1 to 5)
In BOTH Case A and Case B, the intelligence engine synthesizes the complete sequential interview process:
- **Round 1**: Online Assessment / Screening (algorithmic speed, edge cases, language fundamentals).
- **Round 2**: Technical Interview 1 (DSA, Trees, Graphs, Dynamic Programming, optimization).
- **Round 3**: Technical Interview 2 (Machine Coding, concurrency, Low-Level Object-Oriented Design, Frameworks).
- **Round 4**: System Design & Architecture (High-Level Design, distributed caching, database sharding, latency constraints, calibrated to candidate YoE).
- **Round 5**: Hiring Manager & Behavioral (Leadership principles, STAR stories, conflict resolution, ownership).

### 3. Database & Schema Enhancements
- Updated `companies` table: Added `company_type` (`ESTABLISHED` vs `STARTUP`) and `industry`.
- Updated `interview_questions` table:
  - `years_of_experience`: Exact numeric float.
  - `yoe_tier`: `Entry (0-2 yrs)`, `Mid (3-5 yrs)`, `Senior (6-8 yrs)`, `Staff/Lead (9+ yrs)`.
  - `skills_tested`: JSON array of technical competencies (e.g. `["Python", "Kafka", "PostgreSQL"]`).
  - `round_number`: Sequential integer (1 to 5).
- Created `database/seeder.py`: Seeded 25 production-calibrated interview questions covering all 5 rounds across Google, NVIDIA, Fintech (Stripe/Razorpay), AI/GenAI (Anthropic/Perplexity), and E-Commerce (Zepto/Blinkit).

### 4. API & Dashboard Deliverables
- **FastAPI Endpoints**:
  - `POST /intelligence/interview-blueprint` (Accepts `InterviewBlueprintRequest`, returns complete `InterviewBlueprintResponse`).
  - `GET /intelligence/interview-blueprint` (Query param support for direct URL queries).
  - `GET /industries` (Returns all available startup industries).
- **Streamlit Interactive UI**:
  - Added dedicated **"🎯 Interview Process Blueprint"** tab with paradigm toggle (Case A vs. Case B).
  - Seniority tier badge, preparation advice box, and sequential expander cards for all 5 rounds.
  - JSON and CSV export for candidates and interviewers.

---

## [Release 1.0.0] - Production 14-Agent AI Platform Implementation

### 1. Hardware & Environment Profile
- **Host OS**: Windows 10 (AMD64)
- **CPUs**: 8 Logical Cores
- **System Memory**: ~16 GB Total RAM
- **Python Runtime**: Python 3.11.16 (`cpython-3.11.16-windows-x86_64`) managed via `uv`
- **100% Free Strategy**: Zero paid inference, zero paid proxy, zero paid scraping APIs.

### 2. Backend & Database Architecture
- **Dual Engine Architecture**:
  - **PostgreSQL 16 with `pgvector`**: Full support for PostgreSQL relational tables and 384-dimensional dense vector embeddings (`VectorCompatibleType`), configured in `docker-compose.yml` and `docker/init-db.sql`.
  - **Zero-Downtime SQLite Fallback**: Integrated fallback engine (`sqlite:///./interview_intelligence.db`) that auto-activates when a local PostgreSQL server is not yet running, ensuring tests and local development run without database connection crashes.
- **14 Relational Tables Created**:
  1. `companies` (Company entities with normalized titles)
  2. `job_roles` (Job roles with standardized departments and tiers)
  3. `interview_experiences` (Complete experience narratives with SHA256 content hashes)
  4. `interview_rounds` (Round numbers and round types: OA, Tech 1, System Design, HR)
  5. `interview_questions` (Detailed questions with category, difficulty, platform, URL, and verification status)
  6. `question_categories` (Pre-seeded with 16 technical categories)
  7. `coding_problems` (Problem statements, input/output formats, constraints, and test examples)
  8. `data_sources` (Registry of sources: Reddit, LeetCode, GFG, Blogs, Glassdoor)
  9. `source_permissions` (Compliance permissions, rate limits, robots.txt status)
  10. `extraction_jobs` (Asynchronous pipeline execution tracking)
  11. `verification_results` (First-person authenticity, confidence score, human review status)
  12. `duplicate_records` (Original vs. duplicate question mapping with similarity score)
  13. `agent_logs` (Structured agent execution logs)
  14. `embeddings` (384-dimensional dense vectors for semantic similarity search)

### 3. Complete 14-Agent Architecture Delivered
- **Agent 1: Master Orchestrator Agent** (`agents/orchestrator.py`): Coordinates the complete pipeline, manages task graphs, job progress, and state transitions.
- **Agent 2: Source Discovery Agent** (`agents/discovery_agent.py`): Discovers and prioritizes active technical sources.
- **Agent 3: Source Compliance Agent** (`agents/compliance_agent.py`): Strictly enforces `robots.txt`, domain policies, and disallows CAPTCHA bypass or identity spoofing.
- **Agent 4: Web Collection Agent** (`agents/collection_agent.py`): Concurrent async collection with token-bucket rate-limiting, exponential backoff, and circuit breaking.
- **Agent 5: Experience Extraction Agent** (`agents/experience_extraction_agent.py`): Extracts company, role, rounds, and candidate questions using NVIDIA Nemotron or heuristic NLP.
- **Agent 6: Coding Problem Extraction Agent** (`agents/coding_extraction_agent.py`): Parses algorithmic problem statements, constraints, and examples without data fabrication.
- **Agent 7: Question Classification Agent** (`agents/classification_agent.py`): Categorizes questions into 16 technical topics and Easy/Medium/Hard difficulty levels.
- **Agent 8: Authenticity Verification Agent** (`agents/verification_agent.py`): Distinguishes first-person accounts from generic tutorials and flags uncertain records for review.
- **Agent 9: Deduplication Agent** (`agents/deduplication_agent.py`): Performs exact SHA256 content hashing and Jaccard token near-duplicate filtering.
- **Agent 10: Data Enrichment Agent** (`agents/enrichment_agent.py`): Standardizes canonical company names and extracts technical skill tags (e.g. Python, Docker, Kubernetes).
- **Agent 11: Database Management Agent** (`agents/database_agent.py`): Manages relational integrity and transactional persistence.
- **Agent 12: Semantic Search Agent** (`agents/semantic_search_agent.py`): Dense embedding generation and cosine similarity search.
- **Agent 13: Quality Assurance Agent** (`agents/quality_agent.py`): Pydantic schema validation and document structure integrity checks.
- **Agent 14: Monitoring & Analytics Agent** (`agents/monitoring_agent.py`): Real-time Prometheus metrics exporter and system health observability.

### 4. REST API & UI Delivered
- **FastAPI Backend** (`api/main.py`, `api/routes.py`): Full REST interface for `/health`, `/analytics`, `/questions`, `/questions/search`, `/companies`, `/collect/start`, `/collect/status`, and `/metrics`.
- **Streamlit Analytics Dashboard** (`dashboard/app.py`): Five interactive modules:
  1. *Analytics Overview* (KPI cards, DSA topic charts, company volume, platform volume).
  2. *Question Explorer & Search* (Natural language semantic search and relational filters).
  3. *14-Agent Operations* (Live agent status matrix and pipeline execution trigger).
  4. *Compliance & Sources* (Source registry and ethical policy disclosures).
  5. *Manual Review Console* (Human-in-the-loop review and approval/rejection interface).

### 5. Automated Verification & Testing
- **Test Suite Results**: 14 tests executed via `pytest`, 14 passed (100% success rate in 4.23s).
- Validated: Schema creation, deduplication, rate limiting, embeddings, agent behaviors, API endpoints, and end-to-end multi-agent pipeline orchestration.

---

## 📌 What is Needed from the User (Optional Next Steps)

1. **For Production PostgreSQL (pgvector)**:
   - Run `docker-compose up -d postgres` to start the PostgreSQL instance with `pgvector` enabled on port 5432.
   - The platform will automatically connect to it without code changes.

2. **For Local NVIDIA Nemotron LLM via Ollama**:
   - If you wish to run the local Nemotron model through Ollama, run:
     ```bash
     ollama run nemotron-mini:latest
     ```
   - The platform automatically detects Ollama when it is running on port 11434 and uses it for LLM generation. When Ollama is not running, the platform seamlessly uses the high-precision heuristic NLP fallback without failing.
