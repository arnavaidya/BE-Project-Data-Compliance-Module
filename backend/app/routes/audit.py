"""
routes/audit.py
===============
GET  /audit/events – unified query across the full audit log
GET  /audit/summary – quick count of events grouped by type
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.services import audit_logger

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("/events")
async def list_events(
    event_type: str | None = Query(default=None, description="Filter by event_type"),
    dataset_id: str | None = Query(default=None, description="Filter by dataset_id"),
    limit: int = Query(default=50, le=500),
) -> dict:
    """Retrieve recent audit events with optional filters."""
    events = audit_logger.get_events(event_type=event_type, dataset_id=dataset_id, limit=limit)
    return {"total": len(events), "events": events}


@router.get("/summary")
async def event_summary() -> dict:
    """Return a count of every event type currently in the log."""
    all_events = audit_logger.get_events(limit=10_000)
    counts: dict[str, int] = {}
    for ev in all_events:
        et = ev.get("event_type", "unknown")
        counts[et] = counts.get(et, 0) + 1
    return {"total_events": len(all_events), "by_type": counts}
