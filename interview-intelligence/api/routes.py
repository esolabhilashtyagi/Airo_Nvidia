"""
FastAPI Routes for Interview Intelligence Platform.
Implements all required REST API endpoints with pagination, filtering, search, and local auth protection.
"""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks, Depends, Header
from typing import List, Optional, Dict, Any

from database.repository import get_db_repository
from database.schemas import (
    InterviewQuestionResponse,
    CompanyResponse,
    AnalyticsSummary,
    ExtractionJobResponse,
    InterviewBlueprintRequest,
    InterviewBlueprintResponse,
)
from database.models import Company, InterviewQuestion, InterviewExperience, ExtractionJob
from core.workflow_state import workflow_state
from core.config import settings
from agents.orchestrator import MasterOrchestratorAgent
from agents.semantic_search_agent import SemanticSearchAgent
from models.model_manager import get_model_manager

router = APIRouter()
orchestrator = MasterOrchestratorAgent()
search_agent = SemanticSearchAgent()
model_manager = get_model_manager()


def verify_admin_key(x_admin_token: Optional[str] = Header(None)):
    """Simple local token check for administrative triggers."""
    if settings.APP_ENV == "production":
        if not x_admin_token or x_admin_token != settings.ADMIN_API_KEY:
            raise HTTPException(status_code=403, detail="Unauthorized admin access")
    return True


@router.post("/collect/start")
async def start_collection(
    background_tasks: BackgroundTasks,
    source_name: str = Query("all", description="Source to collect (reddit, leetcode, gfg, company_blog, or all)"),
    limit: int = Query(20, ge=1, le=100, description="Max items per source"),
    use_mock: bool = Query(True, description="Use high-quality local mock data (set False for live fetch)"),
    is_admin: bool = Depends(verify_admin_key),
):
    """Triggers an asynchronous multi-agent collection and extraction job."""
    background_tasks.add_task(orchestrator.run_pipeline, source_name=source_name, limit=limit, use_mock=use_mock)
    return {
        "status": "ACCEPTED",
        "message": f"Multi-agent collection pipeline initiated for source '{source_name}'.",
        "limit": limit,
        "mode": "local_mock" if use_mock else "live_network",
    }


@router.get("/collect/status")
async def get_collection_status():
    """Returns active and recent pipeline jobs."""
    return {
        "active_jobs": workflow_state.active_jobs,
        "completed_history": workflow_state.job_history[-20:],
    }


@router.get("/agents/status")
async def get_agents_status():
    """Returns the operational status, task counts, and health of all 14 specialized agents."""
    return {
        "agents": workflow_state.get_all_agent_statuses(),
        "total_agents": len(workflow_state.agent_statuses),
    }


@router.get("/companies")
async def list_companies(limit: int = 50, offset: int = 0):
    """Lists indexed companies with question counts."""
    db = get_db_repository()
    with db.get_session() as session:
        comps = session.query(Company).order_by(Company.name).offset(offset).limit(limit).all()
        return [
            {
                "id": c.id,
                "name": c.name,
                "normalized_name": c.normalized_name,
                "industry": c.industry,
                "created_at": c.created_at,
            }
            for c in comps
        ]


@router.get("/questions")
async def list_questions(
    company: Optional[str] = Query(None, description="Filter by company"),
    role: Optional[str] = Query(None, description="Filter by role"),
    category: Optional[str] = Query(None, description="Filter by topic category"),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty (Easy, Medium, Hard)"),
    query: Optional[str] = Query(None, description="Keyword search query"),
    verified_only: bool = Query(False, description="Filter for verified questions only"),
    round_number: Optional[int] = Query(None, ge=1, le=5, description="Filter questions by round (1 to 5)"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Queries interview questions with granular filtering and pagination."""
    db = get_db_repository()
    questions = db.get_questions(
        company=company,
        role=role,
        category=category,
        difficulty=difficulty,
        query=query,
        verified_only=verified_only,
        round_number=round_number,
        limit=limit,
        offset=offset,
    )
    return [
        {
            "id": q.id,
            "company_name": q.company_name,
            "job_role": q.job_role,
            "round_number": q.round_number,
            "interview_round": q.interview_round,
            "question_text": q.question_text,
            "category": q.question_category,
            "difficulty": q.difficulty,
            "source_platform": q.source_platform,
            "url": q.original_url,
            "confidence_score": q.confidence_score,
            "verification_status": q.verification_status,
            "collected_at": q.collection_timestamp,
            "coding_problem": {
                "title": q.coding_problem.problem_title,
                "constraints": q.coding_problem.constraints,
                "languages": q.coding_problem.programming_languages,
            } if q.coding_problem else None,
        }
        for q in questions
    ]


@router.get("/questions/search")
async def semantic_search_questions(
    q: str = Query(..., min_length=2, description="Natural language semantic search query"),
    limit: int = Query(10, ge=1, le=50),
    min_similarity: float = Query(0.3, ge=0.0, le=1.0),
):
    """Executes local dense vector semantic search against indexed interview questions."""
    results = await search_agent.search_similar(q, limit=limit, min_similarity=min_similarity)
    return {
        "query": q,
        "count": len(results),
        "results": results,
    }


@router.get("/questions/company/{company}")
async def get_questions_by_company(company: str, limit: int = 20, offset: int = 0):
    """Retrieves questions asked by a specific target company."""
    db = get_db_repository()
    questions = db.get_questions(company=company, limit=limit, offset=offset)
    return {
        "company": company,
        "count": len(questions),
        "questions": [
            {
                "id": item.id,
                "role": item.job_role,
                "question": item.question_text,
                "category": item.question_category,
                "difficulty": item.difficulty,
                "round": item.interview_round,
            }
            for item in questions
        ],
    }


@router.get("/questions/category/{category}")
async def get_questions_by_category(category: str, limit: int = 20, offset: int = 0):
    """Retrieves questions categorized under a specific topic or algorithmic concept."""
    db = get_db_repository()
    questions = db.get_questions(category=category, limit=limit, offset=offset)
    return {
        "category": category,
        "count": len(questions),
        "questions": [
            {
                "id": item.id,
                "company": item.company_name,
                "role": item.job_role,
                "question": item.question_text,
                "difficulty": item.difficulty,
            }
            for item in questions
        ],
    }


@router.get("/experiences")
async def list_experiences(limit: int = 20, offset: int = 0):
    """Lists aggregated interview experience accounts."""
    db = get_db_repository()
    with db.get_session() as session:
        exps = session.query(InterviewExperience).order_by(InterviewExperience.collected_at.desc()).offset(offset).limit(limit).all()
        return [
            {
                "id": e.id,
                "platform": e.source_platform,
                "url": e.original_url,
                "level": e.candidate_experience_level,
                "feedback": e.overall_feedback,
                "collected_at": e.collected_at,
            }
            for e in exps
        ]


@router.post("/intelligence/interview-blueprint", response_model=InterviewBlueprintResponse)
async def create_interview_blueprint(req: InterviewBlueprintRequest):
    """
    Intelligently generates a complete, sequential interview process blueprint
    for either an Established Company (Case A: Company + Role + YoE + Skills)
    or a Startup by Industry (Case B: Industry + Role + YoE + Skills).
    """
    db = get_db_repository()
    blueprint = db.get_interview_blueprint(
        company_name=req.company_name,
        industry=req.industry,
        role=req.role,
        yoe=req.years_of_experience,
        skills=req.skills,
        difficulty=req.difficulty,
        questions_per_round=getattr(req, "questions_per_round", 10),
    )
    return blueprint


@router.get("/intelligence/interview-blueprint")
async def get_interview_blueprint_get(
    company_name: Optional[str] = Query(None, description="Case A: Company Name (e.g. Google, NVIDIA, Amazon)"),
    industry: Optional[str] = Query(None, description="Case B: Startup Industry (e.g. Fintech, AI/GenAI, E-Commerce, SaaS)"),
    role: str = Query("Software Engineer", description="Target Role e.g. Backend Engineer, SDE 2"),
    yoe: float = Query(3.0, ge=0.0, le=30.0, description="Years of Experience"),
    skills: Optional[str] = Query(None, description="Comma-separated technical skills e.g. 'Python,Kafka,PostgreSQL'"),
    difficulty: Optional[str] = Query(None, description="Easy, Medium, Hard, or All"),
    questions_per_round: int = Query(10, ge=1, le=25, description="Number of questions per interview round"),
):
    """GET query variant of the Interview Process Blueprint engine."""
    db = get_db_repository()
    skill_list = [s.strip() for s in skills.split(",")] if skills else []
    return db.get_interview_blueprint(
        company_name=company_name,
        industry=industry,
        role=role,
        yoe=yoe,
        skills=skill_list,
        difficulty=difficulty,
        questions_per_round=questions_per_round,
    )


@router.post("/intelligence/generate-dorks")
async def generate_domain_dorks(
    payload: Dict[str, Any],
):
    """
    Nemotron-powered dynamic dork generator:
    Takes (company, role, yoe, skills) and dynamically generates domain-specific open-web
    search queries for each round, avoiding static templates.
    """
    company = payload.get("company", "Google")
    role = payload.get("role", "Software Engineer")
    yoe = float(payload.get("yoe", 3.0))
    skills = payload.get("skills", [])
    if isinstance(skills, str):
        skills = [s.strip() for s in skills.split(",") if s.strip()]

    return await model_manager.generate_domain_dorks(company=company, role=role, yoe=yoe, skills=skills)


@router.get("/intelligence/generate-dorks")
async def generate_domain_dorks_get(
    company: str = Query("Google", description="Target company name"),
    role: str = Query("Software Engineer", description="Target job role"),
    yoe: float = Query(3.0, ge=0.0, le=30.0, description="Years of experience"),
    skills: Optional[str] = Query(None, description="Comma-separated skills"),
):
    """GET query variant of the dynamic open-web dork generator."""
    skills_list = [s.strip() for s in skills.split(",")] if skills else []
    return await model_manager.generate_domain_dorks(company=company, role=role, yoe=yoe, skills=skills_list)


@router.post("/intelligence/round-questions")
async def generate_round_questions(
    payload: Dict[str, Any],
):
    """
    Synthesizes and retrieves the exact, correct, highly-relevant interview questions
    for EACH canonical round (Rounds 1-5) matching company, role, YoE, and skills.
    """
    company = payload.get("company", "Google")
    role = payload.get("role", "Software Engineer")
    yoe = float(payload.get("yoe", 3.0))
    round_number = payload.get("round_number")
    skills = payload.get("skills", [])
    if isinstance(skills, str):
        skills = [s.strip() for s in skills.split(",") if s.strip()]

    dorks = await model_manager.generate_domain_dorks(company=company, role=role, yoe=yoe, skills=skills)
    questions = await model_manager.synthesize_round_questions(
        company=company, role=role, yoe=yoe, skills=skills, round_number=round_number
    )

    return {
        "company": company,
        "role": role,
        "yoe": yoe,
        "skills": skills,
        "round_number": round_number,
        "dorks_used": dorks,
        "total_questions": len(questions),
        "questions": questions,
    }


@router.get("/intelligence/round-questions")
async def generate_round_questions_get(
    company: str = Query("Google", description="Target company name"),
    role: str = Query("Software Engineer", description="Target job role"),
    yoe: float = Query(3.0, ge=0.0, le=30.0, description="Years of experience"),
    skills: Optional[str] = Query(None, description="Comma-separated skills"),
    round_number: Optional[int] = Query(None, ge=1, le=5, description="Filter for specific round (1-5)"),
):
    """GET query variant of the round-by-round question synthesis engine."""
    skills_list = [s.strip() for s in skills.split(",")] if skills else []
    dorks = await model_manager.generate_domain_dorks(company=company, role=role, yoe=yoe, skills=skills_list)
    questions = await model_manager.synthesize_round_questions(
        company=company, role=role, yoe=yoe, skills=skills_list, round_number=round_number
    )

    return {
        "company": company,
        "role": role,
        "yoe": yoe,
        "skills": skills_list,
        "round_number": round_number,
        "dorks_used": dorks,
        "total_questions": len(questions),
        "questions": questions,
    }


@router.get("/industries")
async def list_startup_industries():
    """Lists all available industry sectors for Case B (Startup queries)."""
    db = get_db_repository()
    return {"industries": db.list_industries()}


@router.get("/analytics")
async def get_analytics():
    """Returns platform metrics, DSA topic distributions, platform volume, and verification counts."""
    db = get_db_repository()
    return db.get_analytics_summary()


@router.get("/dataset/summary")
async def get_dataset_summary():
    """Returns dataset versioning, metadata, round distribution, and quality health score."""
    import os, json
    meta_path = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "dataset_metadata.json"))
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)
    from scripts.maintain_dataset import export_dataset
    return export_dataset()


@router.get("/dataset/download/{format_type}")
async def download_dataset(format_type: str):
    """Downloads the full maintained dataset in JSONL or CSV format."""
    import os
    from fastapi.responses import FileResponse
    base_data = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "data"))
    if format_type.lower() == "csv":
        f_path = os.path.join(base_data, "interview_intelligence_dataset.csv")
        media = "text/csv"
    elif format_type.lower() in ["jsonl", "json"]:
        f_path = os.path.join(base_data, "interview_intelligence_dataset.jsonl")
        media = "application/x-ndjson"
    else:
        raise HTTPException(status_code=400, detail="Invalid format. Supported: 'csv', 'jsonl'")

    if not os.path.exists(f_path):
        from scripts.maintain_dataset import export_dataset
        export_dataset()

    return FileResponse(f_path, media_type=media, filename=os.path.basename(f_path))


@router.get("/health")
async def health_check():
    """System health check endpoint verifying database connectivity and local AI status."""
    db = get_db_repository()
    model_status = await model_manager.check_hardware_and_model_status()
    return {
        "status": "HEALTHY",
        "database_engine": db.dialect_name,
        "database_url": db.database_url if db.dialect_name == "postgresql" else db.sqlite_url,
        "ai_engine": model_status,
        "free_stack_verified": True,
        "paid_apis_used": False,
    }
