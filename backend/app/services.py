"""
Singleton service instances.

Every router that needs shared state pulls it from here.
The objects are module-level so they survive for the lifetime of the
FastAPI process (one per worker).  If you ever move to multi-worker
you will want to swap these for a Redis-backed or DB-backed layer.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Any

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logger = logging.getLogger("compliance_backend")
logger.setLevel(logging.INFO)

_handler = logging.StreamHandler()
_handler.setFormatter(
    logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
)
logger.addHandler(_handler)


# ---------------------------------------------------------------------------
# AuditLogger  –  append-only compliance event log
# ---------------------------------------------------------------------------


class AuditLogger:
    """Append-only log of every compliance / security / RBAC action.

    In production you would persist to PostgreSQL, S3, or a SIEM.
    The in-memory list is fine for development and testing.
    """

    def __init__(self) -> None:
        self._events: list[dict[str, Any]] = []

    # -- public API ----------------------------------------------------------

    def log(self, event_type: str, payload: dict[str, Any]) -> str:
        """Record an event and return its unique event_id."""
        event_id = str(uuid.uuid4())
        entry = {
            "event_id": event_id,
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            **payload,
        }
        self._events.append(entry)
        logger.info("audit_event type=%s id=%s", event_type, event_id)
        return event_id

    def get_events(
        self,
        event_type: str | None = None,
        dataset_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Query the log with optional filters."""
        results = self._events
        if event_type:
            results = [e for e in results if e["event_type"] == event_type]
        if dataset_id:
            results = [e for e in results if e.get("dataset_id") == dataset_id]
        return results[-limit:]

    def __len__(self) -> int:
        return len(self._events)


# ---------------------------------------------------------------------------
# DataLineageTracker  –  wraps data_governance_checkup.lineage
# ---------------------------------------------------------------------------


class DataLineageTracker:
    """Thin wrapper that mirrors the ``DataLineageTracker`` class from the
    ``data_governance_checkup`` library.

    The wrapper exists so that:
      1. We add FastAPI-friendly error handling.
      2. We log every mutation through AuditLogger.
      3. Tests can swap the underlying implementation without touching routes.

    Internal state is a dict keyed by ``data_id`` that stores sources,
    transformation history, and destinations – exactly the shape the
    library uses internally.
    """

    def __init__(self, audit_logger: AuditLogger) -> None:
        self._store: dict[str, dict[str, Any]] = {}
        self._audit = audit_logger

    # -- sources -------------------------------------------------------------

    def add_source(self, data_id: str, source_details: dict[str, Any]) -> None:
        self._store.setdefault(data_id, {"source": None, "transformations": [], "destinations": []})
        self._store[data_id]["source"] = source_details
        self._audit.log(
            "lineage_source_added",
            {"dataset_id": data_id, "source_details": source_details},
        )

    # -- transformations -----------------------------------------------------

    def add_transformation(
        self,
        data_id: str,
        transformation: str,
        transformation_type: str = "custom",
        output_columns: list[str] | None = None,
    ) -> None:
        self._store.setdefault(data_id, {"source": None, "transformations": [], "destinations": []})
        record = {
            "description": transformation,
            "type": transformation_type,
            "output_columns": output_columns or [],
            "applied_at": datetime.utcnow().isoformat(),
        }
        self._store[data_id]["transformations"].append(record)
        self._audit.log(
            "lineage_transformation_added",
            {"dataset_id": data_id, "transformation": record},
        )

    # -- destinations --------------------------------------------------------

    def add_destination(self, data_id: str, destination_details: dict[str, Any]) -> None:
        self._store.setdefault(data_id, {"source": None, "transformations": [], "destinations": []})
        self._store[data_id]["destinations"].append(destination_details)
        self._audit.log(
            "lineage_destination_added",
            {"dataset_id": data_id, "destination_details": destination_details},
        )

    # -- queries -------------------------------------------------------------

    def get_lineage(self, data_id: str) -> dict[str, Any] | None:
        return self._store.get(data_id)

    def get_all_lineage(self) -> dict[str, dict[str, Any]]:
        return dict(self._store)

    def dataset_ids(self) -> list[str]:
        return list(self._store.keys())


# ---------------------------------------------------------------------------
# MetadataCatalog  –  wraps data_governance_checkup metadata management
# ---------------------------------------------------------------------------


class MetadataCatalog:
    """In-memory catalog.  Mirrors the metadata management module shipped
    with ``data_governance_checkup``.

    Real deployments should back this with a relational store or
    Apache Atlas / OpenMetadata.
    """

    def __init__(self, audit_logger: AuditLogger) -> None:
        self._catalog: dict[str, dict[str, Any]] = {}
        self._audit = audit_logger

    def upsert(self, entry: dict[str, Any]) -> None:
        dataset_id: str = entry["dataset_id"]
        now = datetime.utcnow().isoformat()
        if dataset_id in self._catalog:
            entry["created_at"] = self._catalog[dataset_id].get("created_at", now)
        else:
            entry.setdefault("created_at", now)
        entry["updated_at"] = now
        self._catalog[dataset_id] = entry
        self._audit.log("metadata_upsert", {"dataset_id": dataset_id})

    def get(self, dataset_id: str) -> dict[str, Any] | None:
        return self._catalog.get(dataset_id)

    def list_all(
        self,
        classification: str | None = None,
        tag: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        entries = list(self._catalog.values())
        if classification:
            entries = [e for e in entries if e.get("classification") == classification]
        if tag:
            entries = [e for e in entries if tag in e.get("tags", [])]
        return entries[:limit]

    def delete(self, dataset_id: str) -> bool:
        if dataset_id in self._catalog:
            del self._catalog[dataset_id]
            self._audit.log("metadata_delete", {"dataset_id": dataset_id})
            return True
        return False

    def __len__(self) -> int:
        return len(self._catalog)


# ---------------------------------------------------------------------------
# Module-level singletons  (import these everywhere)
# ---------------------------------------------------------------------------

audit_logger = AuditLogger()
lineage_tracker = DataLineageTracker(audit_logger)
metadata_catalog = MetadataCatalog(audit_logger)
