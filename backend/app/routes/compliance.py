"""
routes/compliance.py
====================
FastAPI router for compliance-scan endpoints.

POST  /compliance/scan          – run a full multi-regulation scan
GET   /compliance/regulations   – list supported regulations
GET   /compliance/rules/{reg}   – list every rule under one regulation
GET   /compliance/scans         – paginated list of past scans (from audit log)
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app import presidio_wrapper as compliance_engine
from app.schemas import (
    ComplianceScanRequest,
    ComplianceScanResult,
    RegulationTag,
)
from app.services import audit_logger

router = APIRouter(prefix="/compliance", tags=["Compliance"])


# ---------------------------------------------------------------------------
# POST /compliance/scan
# ---------------------------------------------------------------------------


@router.post("/scan", response_model=ComplianceScanResult, status_code=201)
async def scan_dataset(body: ComplianceScanRequest) -> ComplianceScanResult:
    """Run compliance checks on a training dataset using Microsoft Presidio.

    * Uses Microsoft Presidio for industry-standard PII/PHI detection
    * Supports GDPR, HIPAA, CCPA, ISO 27001, PCI-DSS compliance checking
    * Defaults to scanning against **all** supported regulations.
    * Set ``strict_mode=true`` to promote warnings to violations.
    """
    return compliance_engine.run_scan(
        dataset=body.dataset,
        regulations=body.regulations,
        strict_mode=body.strict_mode,
    )


# ---------------------------------------------------------------------------
# GET /compliance/regulations
# ---------------------------------------------------------------------------


@router.get("/regulations")
async def list_regulations() -> dict:
    """Return every regulation tag the engine supports."""
    return {
        "regulations": [
            {"tag": "GDPR", "description": "General Data Protection Regulation (EU) - via Microsoft Presidio"},
            {"tag": "HIPAA", "description": "Health Insurance Portability and Accountability Act (US) - via Microsoft Presidio"},
            {"tag": "CCPA", "description": "California Consumer Privacy Act (US) - via Microsoft Presidio"},
            {"tag": "ISO27001", "description": "ISO/IEC 27001 Information Security - basic checks"},
            {"tag": "PCI_DSS", "description": "Payment Card Industry Data Security Standard - via Microsoft Presidio"},
        ]
    }


# ---------------------------------------------------------------------------
# GET /compliance/rules/{regulation}
# ---------------------------------------------------------------------------


@router.get("/rules/{regulation}")
async def list_rules(regulation: RegulationTag) -> dict:
    """Detail rules for a regulation.
    
    Note: Microsoft Presidio provides real-time PII/PHI detection with 
    customizable recognizers, so specific rules are applied dynamically.
    """
    rules_info = {
        RegulationTag.GDPR: {
            "regulation": "GDPR",
            "description": "Microsoft Presidio detects PII (emails, names, addresses, etc.) and checks GDPR data minimization, consent tracking, and right to erasure requirements.",
            "library": "Microsoft Presidio",
            "entity_types": ["EMAIL_ADDRESS", "PHONE_NUMBER", "PERSON", "LOCATION", "CREDIT_CARD", "US_SSN"]
        },
        RegulationTag.HIPAA: {
            "regulation": "HIPAA",
            "description": "Presidio detects PHI including patient identifiers, medical record numbers, and health information to ensure HIPAA compliance.",
            "library": "Microsoft Presidio",
            "entity_types": ["MEDICAL_LICENSE", "US_SSN", "PERSON", "DATE_TIME"]
        },
        RegulationTag.CCPA: {
            "regulation": "CCPA",
            "description": "Presidio identifies personal information subject to CCPA and validates opt-out and deletion support requirements.",
            "library": "Microsoft Presidio",
            "entity_types": ["EMAIL_ADDRESS", "PHONE_NUMBER", "PERSON", "IP_ADDRESS"]
        },
        RegulationTag.ISO_27001: {
            "regulation": "ISO 27001",
            "description": "Basic access control and risk assessment checks for information security management.",
            "library": "Internal"
        },
        RegulationTag.PCI_DSS: {
            "regulation": "PCI-DSS",
            "description": "Presidio detects credit card numbers (PANs) and validates encryption requirements for payment card data security.",
            "library": "Microsoft Presidio",
            "entity_types": ["CREDIT_CARD", "US_BANK_NUMBER"]
        }
    }
    
    if regulation not in rules_info:
        raise HTTPException(status_code=404, detail=f"No information for {regulation.value}")
    
    return rules_info[regulation]


# ---------------------------------------------------------------------------
# GET /compliance/scans  –  historical scan log
# ---------------------------------------------------------------------------


@router.get("/scans")
async def list_past_scans(
    dataset_id: str | None = Query(default=None),
    limit: int = Query(default=20, le=200),
) -> dict:
    """Pull past scan events from the audit log."""
    events = audit_logger.get_events(event_type="compliance_scan", dataset_id=dataset_id, limit=limit)
    return {"total": len(events), "scans": events}
