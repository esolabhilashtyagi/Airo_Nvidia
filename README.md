# ⚡ Airo Nvidia - AI-Powered Interview Intelligence Platform

> **100% Free & Open-Source, Self-Hosted Multi-Agent Platform**  
> Powered by **14 Specialized Agents**, **NVIDIA Nemotron** Local Inference, **PostgreSQL + pgvector** / **SQLite**, **FastAPI**, and **Streamlit**.  
> **Strict Policy: Zero Paid APIs. Zero Subscriptions. Zero Cloud Lock-In.**

---

## 🌟 Key Capabilities

- **⚡ Startups & MNCs Intelligence**: Instant, unified interview blueprint breakdown for **Top MNCs & Tech Giants** (Google, Meta, Amazon, Microsoft, Apple, NVIDIA, Netflix, Uber) and **High-Growth Startups & Unicorns** (Stripe, Databricks, OpenAI, Figma, Snowflake, Airbnb, DoorDash, Palantir).
- **🎯 5-Round Structured Breakdown**:
  - **Round 1**: Online Assessment (OA)
  - **Round 2**: Core Coding & Problem Solving (DSA)
  - **Round 3**: Machine Coding & Concurrency (LLD)
  - **Round 4**: Large-Scale System Design (HLD)
  - **Round 5**: Behavioral & Leadership (HR)
- **🧹 Zero Synthetic Spam & Numerical Deduplication**: Strict canonical whitelist classification, wrapper prefix stripping, and number masking `<NUM>` hash deduplication.
- **🌐 Unlimited Ethical Web Scraping**: Live multi-source crawler across public developer repositories and engineering archives without artificial caps.
- **📊 Interactive Streamlit Dashboard**: Served at `http://localhost:8501` with 1-click parameters, live relevance scoring, round breakdowns, and CSV export.
- **🚀 High-Performance FastAPI Backend**: Served at `http://localhost:8000/docs` with dual SQLite/PostgreSQL support.

---

## 🏗️ Architecture & Modules

```
aairo_nvidia/
├── CHANGELOG.md                      # Complete system release notes & feature changelog
├── interview-intelligence/
│   ├── agents/                       # 14 Specialized AI & Deterministic Agents
│   ├── collectors/                   # Live Web Scrapers & Harvester
│   ├── core/                         # Configuration, Logging, Rate Limiter
│   ├── dashboard/                    # Streamlit Interactive Dashboard (app.py)
│   ├── database/                     # Dual PostgreSQL/SQLite Repository & Models
│   ├── frontend/                     # Embedded Web App
│   ├── models/                       # NVIDIA Nemotron, Local Embeddings & Fallback NLP
│   ├── pipelines/                    # Scheduled Orchestration Pipelines
│   ├── scripts/                      # Seeders, Sanitizers & Diagnostic Tools
│   ├── tests/                        # Comprehensive Pytest Suite
│   ├── Dockerfile                    # Containerization Spec
│   ├── docker-compose.yml            # Full Stack Compose
│   └── requirements.txt              # Python Dependencies
```

---

## 🚀 Quickstart

### 1. Install Dependencies
```bash
cd interview-intelligence
pip install -r requirements.txt
```

### 2. Start the FastAPI Engine
```bash
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### 3. Launch the Streamlit Dashboard
```bash
python -m streamlit run dashboard/app.py --server.port 8501
```

Access the dashboard at `http://localhost:8501`.
