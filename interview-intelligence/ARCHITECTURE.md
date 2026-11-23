# 14-Agent System Architecture & Pipeline Specification

## 1. System Architecture Overview

```mermaid
flowchart TD
    subgraph Master ["Agent 1: Orchestration & State Machine"]
        A1[Agent 1: Master Orchestrator Agent]
        WS[Workflow State Machine & Task Scheduler]
        A1 <--> WS
    end

    subgraph DiscoveryAndCompliance ["Discovery & Ethical Governance"]
        A2[Agent 2: Source Discovery Agent]
        A3[Agent 3: Source Compliance Agent]
        RP[Robots.txt & Policy Registry]
        RL[Token-Bucket Rate Limiter & Circuit Breaker]
        A2 --> A3
        A3 --> RP
        A3 --> RL
    end

    subgraph CollectionLayer ["Ethical Web Collection Layer"]
        A4[Agent 4: Web Collection Agent]
        RL --> A4
        C1[Reddit Connector] --> A4
        C2[LeetCode Connector] --> A4
        C3[GFG Connector] --> A4
        C4[Engineering Blogs Connector] --> A4
        C5[Glassdoor Ethical Restrictor] --> A4
    end

    subgraph ExtractionVerification ["Extraction & Verification Pipeline"]
        A13[Agent 13: Quality Assurance Agent]
        A5[Agent 5: Experience Extraction Agent]
        A6[Agent 6: Coding Problem Extraction Agent]
        A7[Agent 7: Question Classification Agent]
        A8[Agent 8: Authenticity Verification Agent]
        A9[Agent 9: Deduplication Agent]
        A10[Agent 10: Data Enrichment Agent]
        
        A4 --> A13
        A13 --> A5
        A5 --> A6
        A6 --> A7
        A7 --> A8
        A8 --> A9
        A9 --> A10
    end

    subgraph LocalAI ["Local NVIDIA AI Model Strategy"]
        NEMO[NVIDIA Nemotron Open-Weight Model\nnemotron-mini / 8B via Ollama]
        FALLBACK[Deterministic Heuristic NLP Model\n100% Offline / CPU Fallback]
        EMB[384-dim Dense Embedding Engine\nall-MiniLM-L6-v2]
        A5 <--> NEMO
        A7 <--> NEMO
        A8 <--> NEMO
        A5 -. fallback .-> FALLBACK
        A7 -. fallback .-> FALLBACK
        A8 -. fallback .-> FALLBACK
    end

    subgraph PersistenceAndSearch ["Database & Semantic Vector Indexing"]
        A11[Agent 11: Database Management Agent]
        A12[Agent 12: Semantic Search Agent]
        PG[(PostgreSQL + pgvector\nDual SQLite Fallback)]
        A10 --> A11
        A11 --> A12
        A11 --> PG
        A12 --> EMB
        A12 --> PG
    end

    subgraph ObservabilityAndUI ["Observability, API & Dashboard"]
        A14[Agent 14: Monitoring & Analytics Agent]
        PROM[Prometheus Metrics Exporter]
        FASTAPI[FastAPI REST Backend]
        STREAMLIT[Streamlit Interactive Dashboard]
        A14 --> PROM
        A1 <--> A14
        FASTAPI <--> PG
        STREAMLIT <--> PG
        STREAMLIT <--> FASTAPI
    end
```

## 2. The 14 Specialized Agents

| # | Agent Name | Technology | Operational Responsibility |
|---|---|---|---|
| **1** | **Master Orchestrator Agent** | Python / NeMo Agent State Machine | Manages task graph, dependencies, job lifecycle, fault recovery, and execution state. |
| **2** | **Source Discovery Agent** | Python / Scrapy Registry | Identifies public technical forums, engineering blogs, and authorized interview sources. |
| **3** | **Source Compliance Agent** | Python / RobotParser / Policy Engine | Validates `robots.txt`, enforces rate limits, rejects CAPTCHA/auth bypass, audits compliance. |
| **4** | **Web Collection Agent** | HTTPX Async / BeautifulSoup / Backoff | Concurrently fetches permitted content with token-bucket rate limiting and circuit breaking. |
| **5** | **Experience Extraction Agent** | NVIDIA Nemotron / Heuristic NLP | Extracts candidate role, experience level, rounds, question statements, and interview dates. |
| **6** | **Coding Problem Extraction Agent** | Python / Regex / Pydantic | Isolates problem statements, input/output formats, constraints, and test examples without fabricating data. |
| **7** | **Question Classification Agent** | Local Nemotron / Pattern Classifier | Classifies questions into 16 technical categories (DSA, Trees, DP, System Design, SQL, etc.) and difficulty. |
| **8** | **Authenticity Verification Agent** | Local AI / Experiential Heuristics | Distinguishes genuine first-person narratives from generic educational tutorials; scores confidence. |
| **9** | **Deduplication Agent** | SHA256 Hashing / Jaccard Similarity | Detects exact duplicates and near-duplicate variations while maintaining source attribution. |
| **10** | **Data Enrichment Agent** | Python / Normalization Maps | Standardizes company names, job titles, and extracts tech stack/skill tags. |
| **11** | **Database Management Agent** | SQLAlchemy / PostgreSQL / SQLite | Handles transactional persistence, foreign key relationships, and dual-engine compatibility. |
| **12** | **Semantic Search Agent** | Sentence Transformers (384-dim) / pgvector | Builds vector embeddings and performs cosine similarity search for natural language question queries. |
| **13** | **Quality Assurance Agent** | Pydantic v2 / Pytest | Validates document schemas, ensures non-null required attributes, and generates quality metrics. |
| **14** | **Monitoring & Analytics Agent** | Prometheus / Python Logging | Tracks processing latency, items collected, extracted, and duplicate counts. |

---

## 3. Database Schema (PostgreSQL + pgvector)

The relational model contains 14 tables:

1. `companies`: Company ID, name, canonical normalized name, industry, website, created timestamp.
2. `job_roles`: Role ID, standardized title, normalized title, department, experience tier.
3. `interview_experiences`: Experience ID, company foreign key, role foreign key, feedback, URL, content hash.
4. `interview_rounds`: Round ID, experience foreign key, round number, round type (OA, Tech 1, System Design, HR).
5. `interview_questions`: Question ID (UUID), company, role, text, category, difficulty, platform, URL, confidence, SHA256 content hash.
6. `question_categories`: Pre-seeded 16 technical and DSA categories.
7. `coding_problems`: Problem title, full statement, input/output specifications, constraints, examples JSON.
8. `data_sources`: Source name, base URL, collector type, active status.
9. `source_permissions`: Per-source compliance policy, rate limit RPS, robots.txt URL, policy audit notes.
10. `extraction_jobs`: Job ID, source name, status (PENDING, RUNNING, COMPLETED, FAILED), counts, errors.
11. `verification_results`: Question ID, first-person status, suspicion flag, confidence score, review status.
12. `duplicate_records`: Original question ID, duplicate ID, similarity score, duplicate type.
13. `agent_logs`: Agent name, execution ID, log level, message, metadata JSON.
14. `embeddings`: Question ID, model name (`all-MiniLM-L6-v2`), 384-dimensional dense vector (`pgvector`).
