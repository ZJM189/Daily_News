from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.infrastructure.config import get_settings
from app.interfaces.http.routes import register_routes


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Daily News API", version="0.1.0", debug=settings.debug)
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
        )
    register_routes(app)
    return app
