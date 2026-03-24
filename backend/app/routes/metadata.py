"""
routes/metadata.py
==================
POST   /metadata/catalog              – upsert a catalog entry
GET    /metadata/catalog              – list entries (filterable)
GET    /metadata/catalog/{dataset_id} – single entry
DELETE /metadata/catalog/{dataset_id} – remove an entry
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.schemas import MetadataCatalogEntry, MetadataCatalogListResponse
from app.services import metadata_catalog

router = APIRouter(prefix="/metadata", tags=["Metadata"])


# ---------------------------------------------------------------------------
# POST  /metadata/catalog
# ---------------------------------------------------------------------------


@router.post("/catalog", response_model=MetadataCatalogEntry, status_code=201)
async def upsert_catalog_entry(entry: MetadataCatalogEntry) -> MetadataCatalogEntry:
    """Create or update a metadata catalog entry."""
    metadata_catalog.upsert(entry.model_dump())
    # Re-read to get server-set timestamps
    stored = metadata_catalog.get(entry.dataset_id)
    return MetadataCatalogEntry(**stored)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# GET  /metadata/catalog
# ---------------------------------------------------------------------------


@router.get("/catalog", response_model=MetadataCatalogListResponse)
async def list_catalog(
    classification: str | None = Query(default=None),
    tag: str | None = Query(default=None),
    limit: int = Query(default=100, le=500),
) -> MetadataCatalogListResponse:
    """List catalog entries with optional filters."""
    entries = metadata_catalog.list_all(classification=classification, tag=tag, limit=limit)
    return MetadataCatalogListResponse(
        total=len(entries),
        entries=[MetadataCatalogEntry(**e) for e in entries],
    )


# ---------------------------------------------------------------------------
# GET  /metadata/catalog/{dataset_id}
# ---------------------------------------------------------------------------


@router.get("/catalog/{dataset_id}", response_model=MetadataCatalogEntry)
async def get_catalog_entry(dataset_id: str) -> MetadataCatalogEntry:
    """Retrieve a single catalog entry by dataset ID."""
    entry = metadata_catalog.get(dataset_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"No catalog entry for '{dataset_id}'")
    return MetadataCatalogEntry(**entry)


# ---------------------------------------------------------------------------
# DELETE  /metadata/catalog/{dataset_id}
# ---------------------------------------------------------------------------


@router.delete("/catalog/{dataset_id}", status_code=204)
async def delete_catalog_entry(dataset_id: str) -> None:
    """Remove a catalog entry. Returns 404 if not found."""
    if not metadata_catalog.delete(dataset_id):
        raise HTTPException(status_code=404, detail=f"No catalog entry for '{dataset_id}'")
