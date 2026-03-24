"""
routes/rbac.py
==============
POST  /rbac/audit   – run an RBAC policy audit
GET   /rbac/audits  – list past RBAC audits
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.rbac_engine import run_rbac_audit
from app.schemas import RBACPolicyRequest, RBACauditResult
from app.services import audit_logger

router = APIRouter(prefix="/rbac", tags=["RBAC"])


@router.post("/audit", response_model=RBACauditResult, status_code=201)
async def run_audit(body: RBACPolicyRequest) -> RBACauditResult:
    """Audit an RBAC policy for least-privilege violations and misconfigurations."""
    return run_rbac_audit(body)


@router.get("/audits")
async def list_past_audits(
    limit: int = Query(default=20, le=200),
) -> dict:
    """Pull past RBAC-audit events from the audit log."""
    events = audit_logger.get_events(event_type="rbac_audit", limit=limit)
    return {"total": len(events), "audits": events}
