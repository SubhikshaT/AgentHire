"""AgentHire FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from app.core.rate_limit import limiter
from app.database.session import engine


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(settings.debug)
    settings.upload_path.mkdir(parents=True, exist_ok=True)

    app = FastAPI(
        title="AgentHire API",
        version="0.1.0",
        description="AI-assisted recruitment, screening and interview evaluation. "
        "All AI scores are decision support; humans make hiring decisions.",
    )
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Content-Type"],
    )
    register_exception_handlers(app)
    app.include_router(api_router)

    @app.get("/api/health", tags=["health"])
    def health():
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "database": "ok", "vector_backend": settings.vector_backend}

    return app


app = create_app()
