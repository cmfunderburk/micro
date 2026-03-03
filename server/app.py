"""FastAPI application factory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.catalog_service import catalog_router
from server.database import init_db
from server.manifest_service import manifest_router
from server.orchestrator_service import orchestrator_router
from server.routes import router
from server.websocket import ws_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Microecon Simulation API",
        description="Backend API for microecon agent-based simulation visualization",
        version="0.1.0",
    )

    # Initialize database tables
    init_db()

    # CORS configuration for frontend development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(router, prefix="/api")
    app.include_router(manifest_router, prefix="/api")
    app.include_router(orchestrator_router, prefix="/api")
    app.include_router(catalog_router, prefix="/api")
    app.include_router(ws_router)

    return app
