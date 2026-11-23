"""
Database models for Interview Intelligence Platform.
Implements the 14 core relational tables required for interview question indexing,
verification, deduplication, and semantic search with dual PostgreSQL (pgvector) and SQLite compatibility.
"""

from datetime import datetime
import json
import uuid
from typing import List, Optional

from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    JSON,
    Enum,
    TypeDecorator,
)
from sqlalchemy.orm import declarative_base, relationship

try:
    from pgvector.sqlalchemy import Vector
    PGVECTOR_AVAILABLE = True
except ImportError:
    PGVECTOR_AVAILABLE = False


class VectorCompatibleType(TypeDecorator):
    """
    Transparent Vector type:
    - Uses pgvector Vector(dim) when connected to PostgreSQL.
    - Fallback to JSON array string when connected to SQLite.
    """
    impl = Text
    cache_ok = True

    def __init__(self, dim: int = 384, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dim = dim

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql" and PGVECTOR_AVAILABLE:
            return dialect.type_descriptor(Vector(self.dim))
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, list):
            if dialect.name == "postgresql" and PGVECTOR_AVAILABLE:
                return value
            return json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, str):
            try:
                return json.loads(value)
            except Exception:
                return value
        return value


Base = declarative_base()


class Company(Base):
    __tablename__ = "companies"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), unique=True, nullable=False, index=True)
    normalized_name = Column(String(255), index=True, nullable=False)
    company_type = Column(String(50), default="ESTABLISHED", index=True) # ESTABLISHED or STARTUP
    industry = Column(String(100), nullable=True, index=True) # Fintech, AI/GenAI, E-Commerce, SaaS, etc.
    website = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    experiences = relationship("InterviewExperience", back_populates="company", cascade="all, delete-orphan")


class JobRole(Base):
    __tablename__ = "job_roles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), unique=True, nullable=False, index=True)
    normalized_title = Column(String(255), index=True, nullable=False)
    role_family = Column(String(50), default="TECH", index=True) # TECH, PRODUCT, DATA, DESIGN, MARKETING, SALES, FINANCE, OPERATIONS, HR
    department = Column(String(100), nullable=True)
    experience_tier = Column(String(50), nullable=True) # Entry, Mid, Senior, Staff, Lead
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    experiences = relationship("InterviewExperience", back_populates="job_role", cascade="all, delete-orphan")


class InterviewExperience(Base):
    __tablename__ = "interview_experiences"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String(36), ForeignKey("companies.id"), nullable=True, index=True)
    role_id = Column(String(36), ForeignKey("job_roles.id"), nullable=True, index=True)
    candidate_experience_level = Column(String(50), nullable=True) # 0-2 yrs, 3-5 yrs, 5+ yrs
    offer_status = Column(String(50), nullable=True) # Offered, Rejected, Accepted, Pending
    difficulty_rating = Column(String(50), nullable=True) # Easy, Medium, Hard
    overall_feedback = Column(Text, nullable=True)
    source_platform = Column(String(100), nullable=False, index=True)
    original_url = Column(String(1024), nullable=False)
    publication_date = Column(DateTime, nullable=True)
    collected_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    content_hash = Column(String(64), unique=True, nullable=False, index=True)

    company = relationship("Company", back_populates="experiences")
    job_role = relationship("JobRole", back_populates="experiences")
    rounds = relationship("InterviewRound", back_populates="experience", cascade="all, delete-orphan")
    questions = relationship("InterviewQuestion", back_populates="experience", cascade="all, delete-orphan")


class InterviewRound(Base):
    __tablename__ = "interview_rounds"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    experience_id = Column(String(36), ForeignKey("interview_experiences.id"), nullable=False, index=True)
    round_number = Column(Integer, default=1)
    round_type = Column(String(100), nullable=False) # Online Assessment, Tech 1, Tech 2, System Design, HR
    duration_minutes = Column(Integer, nullable=True)
    feedback = Column(Text, nullable=True)

    experience = relationship("InterviewExperience", back_populates="rounds")
    questions = relationship("InterviewQuestion", back_populates="round")


class InterviewQuestion(Base):
    __tablename__ = "interview_questions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    experience_id = Column(String(36), ForeignKey("interview_experiences.id"), nullable=True, index=True)
    round_id = Column(String(36), ForeignKey("interview_rounds.id"), nullable=True, index=True)
    company_name = Column(String(255), nullable=False, index=True)
    company_type = Column(String(50), default="ESTABLISHED", index=True) # ESTABLISHED or STARTUP
    industry = Column(String(100), nullable=True, index=True) # Fintech, AI/GenAI, E-Commerce, SaaS, etc.
    job_role = Column(String(255), nullable=False, index=True)
    role_family = Column(String(50), default="TECH", index=True) # TECH, PRODUCT, DATA, DESIGN, MARKETING, SALES, FINANCE, OPERATIONS, HR
    experience_level = Column(String(100), nullable=True)
    years_of_experience = Column(Float, nullable=True, index=True) # Numeric YoE e.g. 1.0, 3.5, 6.0
    yoe_tier = Column(String(50), default="Mid (3-5 yrs)", index=True) # Entry, Mid, Senior, Staff/Lead
    skills_tested = Column(JSON, nullable=True) # e.g. ["Python", "FastAPI", "PostgreSQL", "Kafka"]
    interview_round = Column(String(100), nullable=True)
    round_number = Column(Integer, default=1, index=True) # 1 to 5 sequential round index
    question_text = Column(Text, nullable=False)
    question_category = Column(String(100), nullable=False, index=True) # DSA, System Design, etc.
    difficulty = Column(String(50), default="Medium", index=True) # Easy, Medium, Hard
    source_platform = Column(String(100), nullable=False, index=True)
    original_url = Column(String(1024), nullable=False)
    publication_date = Column(DateTime, nullable=True)
    collection_timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    verification_status = Column(String(50), default="UNVERIFIED", index=True) # VERIFIED, UNCERTAIN, REJECTED
    confidence_score = Column(Float, default=0.0)
    content_hash = Column(String(64), unique=True, nullable=False, index=True)

    experience = relationship("InterviewExperience", back_populates="questions")
    round = relationship("InterviewRound", back_populates="questions")
    coding_problem = relationship("CodingProblem", back_populates="question", uselist=False, cascade="all, delete-orphan")
    verification = relationship("VerificationResult", back_populates="question", uselist=False, cascade="all, delete-orphan")
    embedding = relationship("QuestionEmbedding", back_populates="question", uselist=False, cascade="all, delete-orphan")


class QuestionCategory(Base):
    __tablename__ = "question_categories"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), unique=True, nullable=False, index=True)
    parent_category = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)


class CodingProblem(Base):
    __tablename__ = "coding_problems"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    question_id = Column(String(36), ForeignKey("interview_questions.id"), unique=True, nullable=False)
    problem_title = Column(String(255), nullable=False, index=True)
    problem_statement = Column(Text, nullable=False)
    input_format = Column(Text, nullable=True)
    output_format = Column(Text, nullable=True)
    constraints = Column(Text, nullable=True)
    examples_json = Column(JSON, nullable=True)
    programming_languages = Column(String(255), nullable=True)
    algorithmic_concepts = Column(String(255), nullable=True)
    source_reference = Column(String(1024), nullable=True)

    question = relationship("InterviewQuestion", back_populates="coding_problem")


class DataSource(Base):
    __tablename__ = "data_sources"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), unique=True, nullable=False, index=True)
    base_url = Column(String(255), nullable=False)
    collector_type = Column(String(50), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    permission = relationship("SourcePermission", back_populates="source", uselist=False, cascade="all, delete-orphan")
    extraction_jobs = relationship("ExtractionJob", back_populates="source")


class SourcePermission(Base):
    __tablename__ = "source_permissions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_id = Column(String(36), ForeignKey("data_sources.id"), unique=True, nullable=False)
    can_collect = Column(Boolean, default=True)
    rate_limit_rps = Column(Float, default=1.0) # Requests per second
    requires_auth = Column(Boolean, default=False)
    robots_txt_url = Column(String(255), nullable=True)
    last_compliance_check = Column(DateTime, default=datetime.utcnow)
    policy_notes = Column(Text, nullable=True)

    source = relationship("DataSource", back_populates="permission")


class ExtractionJob(Base):
    __tablename__ = "extraction_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_id = Column(String(36), ForeignKey("data_sources.id"), nullable=True, index=True)
    source_name = Column(String(100), nullable=False)
    status = Column(String(50), default="PENDING", index=True) # PENDING, RUNNING, COMPLETED, FAILED
    items_collected = Column(Integer, default=0)
    items_extracted = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    source = relationship("DataSource", back_populates="extraction_jobs")


class VerificationResult(Base):
    __tablename__ = "verification_results"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    question_id = Column(String(36), ForeignKey("interview_questions.id"), unique=True, nullable=False)
    is_first_person = Column(Boolean, default=True)
    is_suspicious = Column(Boolean, default=False)
    confidence_score = Column(Float, default=0.8)
    verification_method = Column(String(50), default="NEMOTRON_RULE_HYBRID")
    flags_json = Column(JSON, nullable=True)
    review_status = Column(String(50), default="PENDING", index=True) # PENDING, APPROVED, REJECTED
    verified_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    question = relationship("InterviewQuestion", back_populates="verification")


class DuplicateRecord(Base):
    __tablename__ = "duplicate_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    original_question_id = Column(String(36), ForeignKey("interview_questions.id"), nullable=False, index=True)
    duplicate_question_id = Column(String(36), nullable=False, index=True)
    similarity_score = Column(Float, nullable=False)
    duplicate_type = Column(String(50), default="EXACT_HASH") # EXACT_HASH, SEMANTIC_NEAR, PARAPHRASE
    detected_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class AgentLog(Base):
    __tablename__ = "agent_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_name = Column(String(100), nullable=False, index=True)
    execution_id = Column(String(64), nullable=True, index=True)
    log_level = Column(String(20), default="INFO")
    message = Column(Text, nullable=False)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class QuestionEmbedding(Base):
    __tablename__ = "embeddings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    question_id = Column(String(36), ForeignKey("interview_questions.id"), unique=True, nullable=False)
    model_name = Column(String(100), default="all-MiniLM-L6-v2")
    embedding_vector = Column(VectorCompatibleType(dim=384), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    question = relationship("InterviewQuestion", back_populates="embedding")
