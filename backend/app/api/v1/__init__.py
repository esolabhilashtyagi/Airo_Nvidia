from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.candidates import router as candidates_router
from app.api.v1.industries import router as industries_router
from app.api.v1.resumes import router as resumes_router
from app.api.v1.questions import router as questions_router
from app.api.v1.modules import router as modules_router
from app.api.v1.coach import router as coach_router
from app.api.v1.testing import router as testing_router
from app.api.v1.interviews import router as interviews_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.admin import router as admin_router
from app.api.v1.system import router as system_router
from app.api.v1.companies import router as companies_router
from app.api.v1.question_taxonomy import router as question_taxonomy_router
from app.api.v1.company_questions import router as company_questions_router
from app.api.v1.payments import router as payments_router

api_v1_router = APIRouter()

api_v1_router.include_router(auth_router)
api_v1_router.include_router(candidates_router)
api_v1_router.include_router(industries_router)
api_v1_router.include_router(resumes_router)
api_v1_router.include_router(company_questions_router)
api_v1_router.include_router(questions_router)
api_v1_router.include_router(modules_router)
api_v1_router.include_router(coach_router)
api_v1_router.include_router(testing_router)
api_v1_router.include_router(interviews_router)
api_v1_router.include_router(dashboard_router)
api_v1_router.include_router(admin_router)
api_v1_router.include_router(system_router)
api_v1_router.include_router(companies_router)
api_v1_router.include_router(question_taxonomy_router)
api_v1_router.include_router(payments_router)
