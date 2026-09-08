from fastapi import FastAPI

from app.interfaces.http.admin.jobs import router as admin_jobs_router
from app.interfaces.http.admin.llm_providers import router as admin_llm_providers_router
from app.interfaces.http.admin.scheduler import router as admin_scheduler_router
from app.interfaces.http.admin.source_credentials import (
    router as admin_source_credentials_router,
)
from app.interfaces.http.admin.sources import router as admin_sources_router
from app.interfaces.http.admin.users import router as admin_users_router
from app.interfaces.http.auth import router as auth_router
from app.interfaces.http.digests import router as digests_router
from app.interfaces.http.favorites import router as favorites_router
from app.interfaces.http.following import router as following_router
from app.interfaces.http.health import router as health_router
from app.interfaces.http.library import router as library_router
from app.interfaces.http.library_chat import router as library_chat_router


def register_routes(app: FastAPI) -> None:
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(digests_router, prefix="/api/v1")
    app.include_router(following_router, prefix="/api/v1")
    app.include_router(favorites_router, prefix="/api/v1")
    app.include_router(library_router, prefix="/api/v1")
    app.include_router(library_chat_router, prefix="/api/v1")
    app.include_router(admin_users_router, prefix="/api/v1")
    app.include_router(admin_source_credentials_router, prefix="/api/v1")
    app.include_router(admin_sources_router, prefix="/api/v1")
    app.include_router(admin_llm_providers_router, prefix="/api/v1")
    app.include_router(admin_jobs_router, prefix="/api/v1")
    app.include_router(admin_scheduler_router, prefix="/api/v1")
