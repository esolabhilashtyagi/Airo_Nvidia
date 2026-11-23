import os
os.environ["DISABLE_SQLALCHEMY_CEXT"] = "1"

from .models import (
    Base,
    Company,
    JobRole,
    InterviewExperience,
    InterviewRound,
    InterviewQuestion,
    QuestionCategory,
    CodingProblem,
    DataSource,
    SourcePermission,
    ExtractionJob,
    VerificationResult,
    DuplicateRecord,
    AgentLog,
    QuestionEmbedding,
)
from .repository import DatabaseRepository, get_db_repository

__all__ = [
    "Base",
    "Company",
    "JobRole",
    "InterviewExperience",
    "InterviewRound",
    "InterviewQuestion",
    "QuestionCategory",
    "CodingProblem",
    "DataSource",
    "SourcePermission",
    "ExtractionJob",
    "VerificationResult",
    "DuplicateRecord",
    "AgentLog",
    "QuestionEmbedding",
    "DatabaseRepository",
    "get_db_repository",
]
