"""
main.py
=======
FastAPI application factory.

Run with:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import (
    audit,
    compliance,
    csv_upload,
    lineage,
    metadata,
    rbac,
    security,
)
from app.schemas import HealthResponse


# ---------------------------------------------------------------------------
# App creation
# ---------------------------------------------------------------------------


def create_app() -> FastAPI:
    application = FastAPI(
        title="AI Training-Data Compliance Backend",
        description=(
            "Checks AI-model training datasets against GDPR, HIPAA, CCPA, "
            "ISO 27001, and PCI-DSS using data-governance-checkup patterns. "
            "Provides lineage tracking, security auditing, RBAC validation, "
            "and a metadata catalog."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS – allow everything during local development
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---------------------------------------------------------------------------
    # Health endpoint
    # ---------------------------------------------------------------------------

    @application.get("/health", response_model=HealthResponse, tags=["Health"])
    async def health() -> HealthResponse:
        return HealthResponse(status="ok", timestamp=datetime.utcnow())

    # ---------------------------------------------------------------------------
    # Mount routers
    # ---------------------------------------------------------------------------

    application.include_router(compliance.router)
    application.include_router(csv_upload.router)
    application.include_router(lineage.router)
    application.include_router(security.router)
    application.include_router(rbac.router)
    application.include_router(metadata.router)
    application.include_router(audit.router)

    return application


# ---------------------------------------------------------------------------
# Module-level instance  (used by uvicorn)
# ---------------------------------------------------------------------------

app = create_app()
