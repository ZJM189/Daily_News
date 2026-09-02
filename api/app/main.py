from fastapi import FastAPI

from app.bootstrap.routes import register_routes
from app.shared.infrastructure.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Daily News API", version="0.1.0", debug=settings.debug)
    register_routes(app)
    return app
