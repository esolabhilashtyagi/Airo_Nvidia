# ⚡ AI-Powered Interview Intelligence & Ethical Data Collection Platform

> **100% Free & Open-Source, Self-Hosted Multi-Agent Platform**  
> Powered by **14 Specialized Agents**, **NVIDIA Nemotron** Local Inference, **PostgreSQL + pgvector**, **FastAPI**, and **Streamlit**.  
> **Strict Policy: Zero Paid APIs. Zero Subscriptions. Zero Cloud Lock-In.**

---

## 🌟 Key Features

- **Complete 14-Agent Architecture**: Dedicated agents for Orchestration, Discovery, Compliance, Web Collection, Experience Extraction, Coding Problem Parsing, Classification, Authenticity Verification, Deduplication, Data Enrichment, Database Management, Semantic Vector Search, Quality Assurance, and Observability.
- **100% Free Local AI Models**: Optimized for open-weight **NVIDIA Nemotron** (`nemotron-mini:latest` or `nemotron-4-340b`), **Qwen2.5**, and **all-MiniLM-L6-v2** embeddings running locally via Ollama or PyTorch, with zero-dependency deterministic heuristic fallback.
- **Production Dual Database Engine**:
  - **PostgreSQL with `pgvector`** for scalable vector search in production and Docker.
  - **Zero-Configuration SQLite Fallback** for immediate local development and offline test execution.
- **Strict Ethical Web Data Collection**:
  - Full adherence to `robots.txt` and domain policies.
  - Token-bucket rate limiting and circuit breakers.
  - Automatic `HTTP 429` backoff and `Retry-After` header handling.
  - **Never** bypasses CAPTCHAs, authentication walls, or spoofed proxy rotation.
- **Full REST API (FastAPI)**: Comprehensive endpoints for search, filtering, analytics, job triggering, and Prometheus `/metrics`.
- **Interactive Web Frontend & Streamlit Dashboard**:
  - **Embedded Web Frontend** (`frontend/`): Served directly at `http://localhost:8000/` with Tailwind CSS, Lucide icons, live Case A / Case B blueprint generation, semantic search, and copy-to-clipboard.
  - **Streamlit Analytics Dashboard** (`dashboard/`): Advanced data engineering review console at `http://localhost:8501`.

---

## 🏗️ Project Structure

```
interview-intelligence/
├── agents/                           # 14 Specialized AI & Deterministic Agents
│   ├── orchestrator.py               # Agent 1: Master Orchestrator Agent
│   ├── discovery_agent.py            # Agent 2: Source Discovery Agent
│   ├── compliance_agent.py           # Agent 3: Source Compliance Agent
│   ├── collection_agent.py           # Agent 4: Web Collection Agent
│   ├── experience_extraction_agent.py# Agent 5: Experience Extraction Agent
│   ├── coding_extraction_agent.py    # Agent 6: Coding Problem Extraction Agent
│   ├── classification_agent.py       # Agent 7: Question Classification Agent
│   ├── verification_agent.py         # Agent 8: Authenticity Verification Agent
│   ├── deduplication_agent.py        # Agent 9: Deduplication Agent
│   ├── enrichment_agent.py           # Agent 10: Data Enrichment Agent
│   ├── database_agent.py             # Agent 11: Database Management Agent
│   ├── semantic_search_agent.py      # Agent 12: Semantic Search Agent
│   ├── quality_agent.py              # Agent 13: Quality Assurance Agent
│   └── monitoring_agent.py           # Agent 14: Monitoring & Analytics Agent
│
├── collectors/                       # Ethical Async Web Scrapers
│   ├── base_collector.py             # Base HTTP client with rate-limiting & backoff
│   ├── reddit_collector.py           # Authorized Reddit public JSON reader
│   ├── leetcode_collector.py         # Public LeetCode question explorer
│   ├── gfg_collector.py              # GeeksforGeeks interview archive collector
│   ├── glassdoor_collector.py        # Compliance restrictor (disallows unauthorized scraping)
│   └── company_blog_collector.py     # Public engineering blog collector
│
├── models/                           # Local Model Inference Engine
│   ├── nemotron_client.py            # Local NVIDIA Nemotron inference client (Ollama)
│   ├── fallback_models.py            # High-accuracy offline heuristic NLP model
│   ├── embedding_model.py            # 384-dim dense embedding generator (all-MiniLM-L6-v2)
│   └── model_manager.py              # Dynamic hardware evaluator and fallback router
│
├── core/                             # Core Systems & Infrastructure
│   ├── config.py                     # Pydantic Settings & environment config
│   ├── permissions.py                # robots.txt parser & compliance audit log
│   ├── rate_limiter.py               # Token-bucket rate limiter & circuit breaker
│   ├── scheduler.py                  # Async task queue & background scheduler
│   ├── logging.py                    # Structured JSON & console logger
│   └── workflow_state.py             # Workflow state tracker & agent heartbeats
│
├── database/                         # Relational Persistence Layer
│   ├── models.py                     # 14 SQLAlchemy tables with pgvector/SQLite dual type
│   ├── schemas.py                    # Pydantic validation schemas & request models
│   └── repository.py                 # Transactional repository with dual engine fallback
│
├── pipelines/                        # Modular Pipeline Processing Stages
│   ├── extraction.py                 # Experience & coding extraction stage
│   ├── classification.py             # 16-topic categorization stage
│   ├── verification.py               # Authenticity & first-person validation stage
│   ├── deduplication.py              # SHA256 & Jaccard token deduplication stage
│   └── indexing.py                   # Dense vector indexing stage
│
├── api/                              # FastAPI Backend
│   ├── main.py                       # FastAPI application & Prometheus exporter
│   └── routes.py                     # All REST endpoints with pagination & filtering
│
├── dashboard/                        # Streamlit User Interface
│   └── app.py                        # Analytics charts, question search & review console
│
├── docker/
│   └── init-db.sql                   # PostgreSQL pgvector extension initializer
├── tests/                            # 100% Automated Pytest Suite
├── requirements.txt                  # Full Python package dependencies
├── docker-compose.yml                # Production multi-service container orchestration
├── Dockerfile                        # Multi-stage container definition
├── pytest.ini                        # Pytest configuration
├── .env.example                      # Configuration template
├── ARCHITECTURE.md                   # Full system architecture & Mermaid diagrams
└── README.md                         # Project documentation
```

---

## 🚀 Quick Start Guide

### 1. Local Setup with `uv` (Recommended)

```bash
# Clone the repository and navigate into the directory
cd interview-intelligence

# Install all free dependencies into your environment
uv pip install -r requirements.txt

# Run the full automated test suite (14/14 tests)
python -m pytest tests -v
```

### 2. Start the FastAPI Backend

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```
- API Documentation (Swagger UI): `http://localhost:8000/docs`
- Prometheus Metrics: `http://localhost:8000/metrics`
- System Health Check: `http://localhost:8000/health`

### 3. Launch the Streamlit Dashboard

```bash
streamlit run dashboard/app.py
```
- Open `http://localhost:8501` to view live analytics, search questions by topic, explore company distribution, and approve/reject unverified questions.

---

## 🐳 Docker Deployment (PostgreSQL + pgvector + Ollama)

To deploy the entire production stack with a single command:

```bash
docker-compose up --build -d
```

Services started:
1. `postgres`: PostgreSQL 16 with `pgvector` pre-installed on port `5432`.
2. `ollama`: Free local AI model runtime on port `11434`.
3. `api`: FastAPI backend on port `8000`.
4. `dashboard`: Streamlit interactive dashboard on port `8501`.

To download the NVIDIA Nemotron model inside Ollama:
```bash
docker exec -it interview_intelligence_ollama ollama pull nemotron-mini:latest
```

---

## 📡 REST API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/collect/start` | Trigger background multi-agent collection (`?source_name=all&limit=5`) |
| `GET` | `/collect/status` | List running and completed extraction jobs |
| `GET` | `/agents/status` | Get real-time health and task throughput for all 14 agents |
| `GET` | `/companies` | List all indexed companies |
| `GET` | `/questions` | List questions with pagination and filters (`company`, `role`, `category`, `difficulty`) |
| `GET` | `/questions/search` | Natural language semantic vector search (`?q=distributed+rate+limiter`) |
| `GET` | `/questions/company/{company}` | Filter questions by company |
| `GET` | `/questions/category/{category}` | Filter questions by technical/DSA topic |
| `GET` | `/experiences` | Retrieve full interview experience narratives |
| `GET` | `/analytics` | Platform KPI statistics, topic distributions, and platform volume |
| `GET` | `/health` | Verify database engine status and local AI engine availability |

---

## 🧪 Testing & Verification

Run the test suite at any time:
```bash
python -m pytest tests -v
```

The suite validates:
- Schema persistence and foreign key cascades.
- SHA256 content deduplication and Jaccard token similarity.
- Strict robots.txt compliance and rate-limiting circuit breakers.
- Deterministic 384-dimensional unit vector embedding generation.
- FastAPI endpoint responses and schemas.
- Full end-to-end multi-agent pipeline orchestration.
