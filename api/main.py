"""
Compliance Engine API v6.0
===========================
FastAPI application with router-based architecture.
Serves React frontend and provides REST API endpoints.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Depends
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
from services.backup_service import get_backup_service
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
    auth,
    graphs,
    data_sources,
    rbac,
)
from api.dependencies.auth import get_current_user, get_current_admin

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
        # Ensure indexes are created for performance
        try:
            from utils.graph_builder import RulesGraphBuilder
            builder = RulesGraphBuilder(db.get_rules_graph())
            builder._create_indexes()
            logger.info("Graph indexes verified/created for optimal query performance")
        except Exception as e:
            logger.warning(f"Failed to verify/create indexes: {e}")
    else:
        logger.warning("Database connection failed")

    get_cache_service()
    logger.info(f"Cache initialized (enabled={settings.cache.enable_cache})")

    # Initialize operational SQLite store (data sources, RBAC)
    try:
        from services.operational_store import get_operational_store
        get_operational_store().init()
        logger.info("Operational store initialized")
    except Exception as e:
        logger.warning(f"Operational store initialization failed: {e}")

    ai = get_ai_service()
    logger.info(f"AI service initialized (enabled={ai.is_enabled})")

    # Initialize graph registry
    from services.graph_registry import get_graph_registry
    registry = get_graph_registry()
    logger.info(f"Graph registry initialized with {len(registry.list_graphs())} graphs")

    backup = get_backup_service()
    backup.start_background_task()
    logger.info("Backup service initialized")

    # Validate graph has data (graph-native: no CSV reads at runtime)
    if db.check_connection():
        try:
            rules_count = db.execute_rules_query("MATCH (r:Rule) RETURN count(r) as cnt")
            country_count = db.execute_rules_query("MATCH (c:Country) RETURN count(c) as cnt")
            r_cnt = rules_count[0].get("cnt", 0) if rules_count else 0
            c_cnt = country_count[0].get("cnt", 0) if country_count else 0
            logger.info(f"Graph validation: {r_cnt} rules, {c_cnt} countries loaded")

            # Auto-build graph on first startup if empty
            if r_cnt == 0 or c_cnt == 0:
                logger.info("Graph is empty. Building graph automatically on first startup...")
                try:
                    from utils.graph_builder import build_rules_graph
                    build_rules_graph(clear_existing=True)
                    logger.info("RulesGraph build complete! Graph is now populated.")
                except Exception as build_error:
                    logger.error(f"Failed to auto-build graph: {build_error}")
                    logger.warning("You can manually build the graph with: python main.py --build-graph")
        except Exception as e:
            logger.warning(f"Graph validation skipped: {e}")

        # Migrate existing Rule nodes to add lifecycle fields if missing
        try:
            from datetime import date, datetime as dt
            today = date.today().isoformat()
            now = dt.utcnow().isoformat()
            db.execute_rules_query(
                "MATCH (r:Rule) WHERE r.valid_from IS NULL "
                f"SET r.valid_from = '{today}', r.status = 'live', r.version_id = 1, "
                f"r.workspace_id = 'default', r.created_at = '{now}', r.updated_at = '{now}'"
            )
            logger.info("Rule lifecycle migration complete")
        except Exception as e:
            logger.warning(f"Rule lifecycle migration skipped: {e}")

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

# Register public and auth routers
app.include_router(health.router)
app.include_router(auth.router)

# External endpoints (User-level access)
app.include_router(evaluation.router, dependencies=[Depends(get_current_user)])
app.include_router(metadata.router, dependencies=[Depends(get_current_user)])
app.include_router(rules_overview.router, dependencies=[Depends(get_current_user)])

# Internal endpoints (Admin-level access)
app.include_router(graph_data.router, dependencies=[Depends(get_current_admin)])
app.include_router(wizard.router, dependencies=[Depends(get_current_admin)])
app.include_router(sandbox.router, dependencies=[Depends(get_current_admin)])
# Note: agent_events SSE stream cannot use header-based auth (EventSource limitation)
# Session validation is handled inside the endpoint
app.include_router(agent_events.router)
app.include_router(admin.router, dependencies=[Depends(get_current_admin)])
app.include_router(rule_links.router, dependencies=[Depends(get_current_admin)])
app.include_router(jobs.router, dependencies=[Depends(get_current_admin)])
app.include_router(graphs.router, dependencies=[Depends(get_current_admin)])
app.include_router(data_sources.router, dependencies=[Depends(get_current_admin)])
app.include_router(rbac.router)

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
