"""
routes/lineage.py
=================
FastAPI router for data-lineage endpoints.

POST  /lineage/source           – register a dataset source
POST  /lineage/transformation   – record a transformation step
POST  /lineage/destination      – record a downstream destination
GET   /lineage/{dataset_id}     – full lineage record for one dataset
GET   /lineage                  – all tracked datasets
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas import (
    LineageDestinationRequest,
    LineageGraphResponse,
    LineageRecord,
    LineageSourceRequest,
    LineageTransformRequest,
)
from app.services import lineage_tracker

router = APIRouter(prefix="/lineage", tags=["Lineage"])


# ---------------------------------------------------------------------------
# POST  /lineage/source
# ---------------------------------------------------------------------------


@router.post("/source", status_code=201)
async def add_source(body: LineageSourceRequest) -> dict:
    """Register or update the upstream source for a dataset."""
    lineage_tracker.add_source(data_id=body.dataset_id, source_details=body.source_details)
    return {"status": "ok", "dataset_id": body.dataset_id, "action": "source_added"}


# ---------------------------------------------------------------------------
# POST  /lineage/transformation
# ---------------------------------------------------------------------------


@router.post("/transformation", status_code=201)
async def add_transformation(body: LineageTransformRequest) -> dict:
    """Append a transformation step to a dataset's lineage history."""
    lineage_tracker.add_transformation(
        data_id=body.dataset_id,
        transformation=body.transformation,
        transformation_type=body.transformation_type.value,
        output_columns=body.output_columns,
    )
    return {"status": "ok", "dataset_id": body.dataset_id, "action": "transformation_added"}


# ---------------------------------------------------------------------------
# POST  /lineage/destination
# ---------------------------------------------------------------------------


@router.post("/destination", status_code=201)
async def add_destination(body: LineageDestinationRequest) -> dict:
    """Record a downstream destination (e.g. model training pipeline, warehouse)."""
    lineage_tracker.add_destination(data_id=body.dataset_id, destination_details=body.destination_details)
    return {"status": "ok", "dataset_id": body.dataset_id, "action": "destination_added"}


# ---------------------------------------------------------------------------
# GET  /lineage/{dataset_id}
# ---------------------------------------------------------------------------


@router.get("/lineage/{dataset_id}", response_model=LineageRecord)
async def get_lineage(dataset_id: str) -> LineageRecord:
    """Return the full lineage record for a single dataset."""
    record = lineage_tracker.get_lineage(dataset_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"No lineage data for dataset '{dataset_id}'")
    return LineageRecord(
        data_id=dataset_id,
        source=record.get("source"),
        transformations=record.get("transformations", []),
        destinations=record.get("destinations", []),
    )


# ---------------------------------------------------------------------------
# GET  /lineage  –  full graph
# ---------------------------------------------------------------------------


@router.get("/", response_model=LineageGraphResponse)
async def get_all_lineage() -> LineageGraphResponse:
    """Return lineage records for every tracked dataset."""
    all_data = lineage_tracker.get_all_lineage()
    records = [
        LineageRecord(
            data_id=ds_id,
            source=info.get("source"),
            transformations=info.get("transformations", []),
            destinations=info.get("destinations", []),
        )
        for ds_id, info in all_data.items()
    ]
    return LineageGraphResponse(dataset_id="*", records=records)
