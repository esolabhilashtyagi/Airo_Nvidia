from app.schemas.common import APIResponse, PaginationMeta, ErrorDetail
from app.schemas.auth import (
    UserRegisterRequest, UserLoginRequest, TokenResponse,
    RefreshTokenRequest, ForgotPasswordRequest, ResetPasswordRequest, UserResponse
)
from app.schemas.taxonomy import IndustryResponse, IndustryCategoryResponse, JobRoleResponse, SkillResponse, CompanyResponse
from app.schemas.candidate import (
    EducationCreate, EducationResponse, ExperienceCreate, ExperienceResponse,
    TargetCompanyCreate, TargetCompanyResponse, OnboardingStepRequest, CandidateProfileResponse
)
from app.schemas.resume import (
    ResumeResponse, ResumeVersionResponse, ResumeAnalysisResponse,
    ResumeSuggestionResponse, SuggestionActionRequest, ResumeATSReviewRequest, ResumeATSReviewResponse
)
from app.schemas.question import (
    QuestionCreate, QuestionUpdate, QuestionResponse, QuestionOption,
    QuestionPracticeRequest, QuestionPracticeResponse
)
from app.schemas.module import ModuleResponse, LessonResponse, RoadmapResponse, RoadmapTaskResponse
from app.schemas.assessment import (
    AssessmentConfigureRequest, AssessmentResponse, AssessmentStartResponse,
    CandidateAnswerSaveRequest, AssessmentResultResponse, AttemptHistoryItem
)
from app.schemas.interview import (
    InterviewSetupRequest, InterviewSessionResponse, InterviewRespondRequest, InterviewReportResponse
)
from app.schemas.coach import (
    SkillGapResponse, CoachChatRequest, CoachChatResponse, CoachMessageResponse
)
from app.schemas.dashboard import (
    DashboardOverviewResponse, AnalyticsResponse, DashboardMetricCard,
    ScoreHistoryItem, TopicPerformanceItem
)

__all__ = [
    "APIResponse",
    "PaginationMeta",
    "ErrorDetail",
    "UserRegisterRequest",
    "UserLoginRequest",
    "TokenResponse",
    "RefreshTokenRequest",
    "ForgotPasswordRequest",
    "ResetPasswordRequest",
    "UserResponse",
    "IndustryResponse",
    "IndustryCategoryResponse",
    "JobRoleResponse",
    "SkillResponse",
    "CompanyResponse",
    "EducationCreate",
    "EducationResponse",
    "ExperienceCreate",
    "ExperienceResponse",
    "TargetCompanyCreate",
    "TargetCompanyResponse",
    "OnboardingStepRequest",
    "CandidateProfileResponse",
    "ResumeResponse",
    "ResumeVersionResponse",
    "ResumeAnalysisResponse",
    "ResumeSuggestionResponse",
    "ResumeATSReviewRequest",
    "ResumeATSReviewResponse",
    "SuggestionActionRequest",
    "QuestionCreate",
    "QuestionUpdate",
    "QuestionResponse",
    "QuestionOption",
    "QuestionPracticeRequest",
    "QuestionPracticeResponse",
    "ModuleResponse",
    "LessonResponse",
    "RoadmapResponse",
    "RoadmapTaskResponse",
    "AssessmentConfigureRequest",
    "AssessmentResponse",
    "AssessmentStartResponse",
    "CandidateAnswerSaveRequest",
    "AssessmentResultResponse",
    "AttemptHistoryItem",
    "InterviewSetupRequest",
    "InterviewSessionResponse",
    "InterviewRespondRequest",
    "InterviewReportResponse",
    "SkillGapResponse",
    "CoachChatRequest",
    "CoachChatResponse",
    "CoachMessageResponse",
    "DashboardOverviewResponse",
    "AnalyticsResponse",
    "DashboardMetricCard",
    "ScoreHistoryItem",
    "TopicPerformanceItem",
]
