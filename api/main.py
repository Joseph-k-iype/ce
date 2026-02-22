"""
Compliance Engine API v6.0
===========================
FastAPI application with router-based architecture.
Serves React frontend and provides REST API endpoints.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse

import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings
from models.schemas import ErrorResponse
from services.database import get_db_service
from services.cache import get_cache_service
from agents.ai_service import get_ai_service

# Import routers
from api.routers import (
    evaluation,
    metadata,
    rules_overview,
    graph_data,
    wizard,
    sandbox,
    agent_events,
    health,
    admin,
    rule_links,
    jobs,
)

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")

    # Initialize services
    db = get_db_service()
    if db.check_connection():
        logger.info("Database connection established")
    else:
        logger.warning("Database connection failed")

    get_cache_service()
    logger.info(f"Cache initialized (enabled={settings.cache.enable_cache})")

    ai = get_ai_service()
    logger.info(f"AI service initialized (enabled={ai.is_enabled})")

    # Validate graph has data (graph-native: no CSV reads at runtime)
    if db.check_connection():
        try:
            rules_count = db.execute_rules_query("MATCH (r:Rule) RETURN count(r) as cnt")
            country_count = db.execute_rules_query("MATCH (c:Country) RETURN count(c) as cnt")
            r_cnt = rules_count[0].get("cnt", 0) if rules_count else 0
            c_cnt = country_count[0].get("cnt", 0) if country_count else 0
            logger.info(f"Graph validation: {r_cnt} rules, {c_cnt} countries loaded")
            if r_cnt == 0:
                logger.warning("No rules found in graph. Run 'python main.py --build-graph' to populate.")
            if c_cnt == 0:
                logger.warning("No countries found in graph. Run 'python main.py --build-graph' to populate.")
        except Exception as e:
            logger.warning(f"Graph validation skipped: {e}")

    yield

    # Shutdown
    logger.info("Shutting down application")
    cache = get_cache_service()
    cache.clear()


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="Scalable compliance engine for cross-border data transfer evaluation",
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health.router)
app.include_router(evaluation.router)
app.include_router(metadata.router)
app.include_router(rules_overview.router)
app.include_router(graph_data.router)
app.include_router(wizard.router)
app.include_router(sandbox.router)
app.include_router(agent_events.router)
app.include_router(admin.router)
app.include_router(rule_links.router)
app.include_router(jobs.router)

# Serve React frontend static files
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="frontend-assets")

# Serve legacy static files if they exist
static_path = settings.paths.static_dir
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


# Serve React app for all non-API routes (SPA routing)
@app.get("/{full_path:path}")
async def serve_react_app(full_path: str):
    """Serve React frontend for all non-API routes."""
    # Don't intercept API routes, docs, or health
    if full_path.startswith(("api/", "docs", "redoc", "openapi.json", "health")):
        return JSONResponse(status_code=404, content={"error": "Not found"})

    index_file = frontend_dist / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))

    # Fallback if React not built yet
    return JSONResponse(
        content={
            "message": f"{settings.app_name} v{settings.app_version}",
            "docs": "/docs",
            "note": "React frontend not built. Run: cd frontend && npm run build"
        }
    )


# Error handlers
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            detail=str(exc) if settings.environment == "development" else None,
        ).model_dump()
    )


def run():
    """Run the API server."""
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=settings.api.host,
        port=settings.api.port,
        reload=settings.api.reload,
        workers=settings.api.workers if not settings.api.reload else 1,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    run()
