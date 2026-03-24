"""
Pydantic request / response models for the Compliance Backend.

Every route handler imports its types from here so that the
OpenAPI docs are fully self-documenting and the validation layer
is kept in one place.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class SeverityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ComplianceStatus(str, Enum):
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PENDING = "pending"
    SKIPPED = "skipped"


class RegulationTag(str, Enum):
    GDPR = "GDPR"
    HIPAA = "HIPAA"
    CCPA = "CCPA"
    ISO_27001 = "ISO27001"
    PCI_DSS = "PCI_DSS"


class DataClassification(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class TransformationType(str, Enum):
    FILTER = "filter"
    ANONYMIZE = "anonymize"
    AGGREGATE = "aggregate"
    JOIN = "join"
    CUSTOM = "custom"


# ---------------------------------------------------------------------------
# Dataset (input)
# ---------------------------------------------------------------------------


class DatasetColumn(BaseModel):
    """Schema-level description of a single column in a training dataset."""

    name: str
    dtype: str = Field(default="string", description="Inferred or declared column type")
    contains_pii: bool = False
    contains_phi: bool = False
    sensitivity: DataClassification = DataClassification.PUBLIC
    sample_values: list[Any] = Field(default_factory=list, max_length=5)


class DatasetMeta(BaseModel):
    """Top-level metadata envelope that wraps the actual row data."""

    dataset_id: str
    name: str
    source: str = Field(description="Origin system / file path / URL")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    owner: str = ""
    columns: list[DatasetColumn] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Compliance scan (request + response)
# ---------------------------------------------------------------------------


class ComplianceScanRequest(BaseModel):
    """Body sent to POST /compliance/scan."""

    dataset: DatasetMeta
    regulations: list[RegulationTag] = Field(
        default_factory=lambda: list(RegulationTag),
        description="Which frameworks to check; defaults to all supported",
    )
    strict_mode: bool = Field(
        default=False,
        description="When True any warning is promoted to a violation",
    )


class ComplianceFinding(BaseModel):
    """A single finding produced by one regulation checker."""

    regulation: RegulationTag
    rule_id: str
    rule_description: str
    status: ComplianceStatus
    severity: SeverityLevel
    affected_columns: list[str] = Field(default_factory=list)
    details: str = ""
    remediation: str = ""


class ComplianceScanResult(BaseModel):
    """Aggregated output returned to the caller after a full scan."""

    scan_id: str
    dataset_id: str
    scanned_at: datetime = Field(default_factory=datetime.utcnow)
    overall_status: ComplianceStatus
    findings: list[ComplianceFinding]
    summary: dict[RegulationTag, ComplianceStatus] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Lineage (request + response)
# ---------------------------------------------------------------------------


class LineageSourceRequest(BaseModel):
    dataset_id: str
    source_details: dict[str, Any]


class LineageTransformRequest(BaseModel):
    dataset_id: str
    transformation: str
    transformation_type: TransformationType = TransformationType.CUSTOM
    output_columns: list[str] = Field(default_factory=list)


class LineageDestinationRequest(BaseModel):
    dataset_id: str
    destination_details: dict[str, Any]


class LineageRecord(BaseModel):
    data_id: str
    source: dict[str, Any] | None = None
    transformations: list[dict[str, Any]] = Field(default_factory=list)
    destinations: list[dict[str, Any]] = Field(default_factory=list)


class LineageGraphResponse(BaseModel):
    """Full lineage graph for a dataset – nodes + edges."""

    dataset_id: str
    records: list[LineageRecord]


# ---------------------------------------------------------------------------
# Security audit (request + response)
# ---------------------------------------------------------------------------


class SecurityAuditRequest(BaseModel):
    dataset: DatasetMeta
    check_encryption: bool = True
    check_access_controls: bool = True
    check_data_retention: bool = True
    check_logging: bool = True


class SecurityFinding(BaseModel):
    category: str  # encryption | access_control | retention | logging
    severity: SeverityLevel
    description: str
    recommendation: str
    is_critical: bool = False


class SecurityAuditResult(BaseModel):
    audit_id: str
    dataset_id: str
    audited_at: datetime = Field(default_factory=datetime.utcnow)
    findings: list[SecurityFinding]
    overall_risk: SeverityLevel
    passed: bool


# ---------------------------------------------------------------------------
# RBAC audit (request + response)
# ---------------------------------------------------------------------------


class RBACRole(BaseModel):
    role_name: str
    permissions: list[str]
    datasets_accessible: list[str] = Field(default_factory=list)


class RBACUserEntry(BaseModel):
    user_id: str
    roles: list[str]


class RBACPolicyRequest(BaseModel):
    roles: list[RBACRole]
    users: list[RBACUserEntry]
    datasets: list[str]


class RBACViolation(BaseModel):
    user_id: str
    dataset_id: str
    granted_permission: str
    violation_reason: str
    severity: SeverityLevel


class RBACauditResult(BaseModel):
    audit_id: str
    audited_at: datetime = Field(default_factory=datetime.utcnow)
    violations: list[RBACViolation]
    compliant: bool


# ---------------------------------------------------------------------------
# Metadata catalog (request + response)
# ---------------------------------------------------------------------------


class MetadataCatalogEntry(BaseModel):
    dataset_id: str
    name: str
    description: str = ""
    owner: str = ""
    classification: DataClassification = DataClassification.PUBLIC
    columns: list[DatasetColumn] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    tags: list[str] = Field(default_factory=list)


class MetadataCatalogListResponse(BaseModel):
    total: int
    entries: list[MetadataCatalogEntry]


# ---------------------------------------------------------------------------
# Health / generic
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str = "ok"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
