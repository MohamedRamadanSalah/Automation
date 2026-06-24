"""FastAPI application factory."""
from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from trend_intel.config import get_settings
from trend_intel.core.errors import register_handlers
from trend_intel.core.logging import configure_logging, get_logger
from trend_intel.db.session import close_engine, get_engine
from trend_intel.schemas.common import Health

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    log.info("startup", model=settings.openrouter_default_model)
    # Touch the engine so the pool is warmed up
    get_engine()
    yield
    await close_engine()
    log.info("shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="AI Trend Intelligence Platform",
        version="0.1.0",
        lifespan=lifespan,
    )

    register_handlers(app)

    @app.get("/health", response_model=Health, tags=["health"])
    async def health() -> Health:
        from sqlalchemy.ext.asyncio import AsyncSession
        from trend_intel.db.session import get_session_factory

        db_status = "down"
        try:
            factory = get_session_factory()
            async with factory() as session:
                await session.execute(text("SELECT 1"))
            db_status = "up"
        except Exception as exc:
            log.warning("health_db_check_failed", error=str(exc))

        return Health(status="ok", db=db_status)

    # Register routers (imported lazily to avoid circular imports)
    from trend_intel.api.runs import router as runs_router
    from trend_intel.api.stages import router as stages_router
    from trend_intel.api.reports import router as reports_router
    from trend_intel.api.history import router as history_router
    from trend_intel.api.config import router as config_router

    app.include_router(runs_router)
    app.include_router(stages_router)
    app.include_router(reports_router)
    app.include_router(history_router)
    app.include_router(config_router)

    return app


app = create_app()
