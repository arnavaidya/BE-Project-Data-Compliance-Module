"""
routes/security.py
==================
FastAPI router for security-audit endpoints.

POST  /security/audit           – run a security audit
GET   /security/audits          – list past audits from the audit log
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.schemas import SecurityAuditRequest, SecurityAuditResult
from app.security_engine import run_security_audit
from app.services import audit_logger

router = APIRouter(prefix="/security", tags=["Security"])


# ---------------------------------------------------------------------------
# POST  /security/audit
# ---------------------------------------------------------------------------


@router.post("/audit", response_model=SecurityAuditResult, status_code=201)
async def run_audit(body: SecurityAuditRequest) -> SecurityAuditResult:
    """Execute a security-posture audit on a dataset.

    Toggle individual check categories via the boolean flags in the request body.
    """
    return run_security_audit(body)


# ---------------------------------------------------------------------------
# GET  /security/audits
# ---------------------------------------------------------------------------


@router.get("/audits")
async def list_past_audits(
    dataset_id: str | None = Query(default=None),
    limit: int = Query(default=20, le=200),
) -> dict:
    """Pull past security-audit events from the append-only audit log."""
    events = audit_logger.get_events(event_type="security_audit", dataset_id=dataset_id, limit=limit)
    return {"total": len(events), "audits": events}
