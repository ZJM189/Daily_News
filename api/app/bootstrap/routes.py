from fastapi import FastAPI

from app.shared.interfaces.http.health import router as health_router


def register_routes(app: FastAPI) -> None:
    app.include_router(health_router, prefix="/api/v1")
