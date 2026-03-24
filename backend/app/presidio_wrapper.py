"""
presidio_wrapper.py
===================
Wrapper around Microsoft Presidio for PII/PHI detection and compliance checking.

Microsoft Presidio provides:
- Industry-standard PII detection (emails, phones, SSNs, credit cards, etc.)
- PHI detection (medical record numbers, patient IDs, health info)
- Multi-language support
- Customizable recognizers
- Data anonymization capabilities

This module translates Presidio's detection results into our ComplianceFinding
and ComplianceScanResult schemas so the frontend doesn't need to change.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import pandas as pd

from app.schemas import (
    ComplianceFinding,
    ComplianceScanResult,
    ComplianceStatus,
    DatasetMeta,
    RegulationTag,
    SeverityLevel,
)
from app.services import audit_logger, logger

# Try to import Presidio components
try:
    from presidio_analyzer import AnalyzerEngine
    from presidio_analyzer.nlp_engine import NlpEngineProvider
    
    # Initialize Presidio Analyzer
    nlp_configuration = {
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
    }
    nlp_engine = NlpEngineProvider(nlp_configuration=nlp_configuration).create_engine()
    analyzer = AnalyzerEngine(nlp_engine=nlp_engine)
    
    PRESIDIO_AVAILABLE = True
    logger.info("Microsoft Presidio loaded successfully")
except ImportError as e:
    PRESIDIO_AVAILABLE = False
    analyzer = None
    logger.warning(f"Presidio not available: {e}. Falling back to basic checks.")
except Exception as e:
    PRESIDIO_AVAILABLE = False
    analyzer = None
    logger.warning(f"Presidio initialization failed: {e}. Falling back to basic checks.")


# ---------------------------------------------------------------------------
# PII/PHI Entity Type Mappings
# ---------------------------------------------------------------------------

# Presidio entity types that constitute PII
PII_ENTITY_TYPES = {
    'EMAIL_ADDRESS', 'PHONE_NUMBER', 'PERSON', 'LOCATION', 'ADDRESS',
    'CREDIT_CARD', 'IBAN_CODE', 'US_SSN', 'US_DRIVER_LICENSE', 'US_PASSPORT',
    'UK_NHS', 'SG_NRIC_FIN', 'AU_ABN', 'AU_ACN', 'AU_TFN', 'AU_MEDICARE',
    'IP_ADDRESS', 'CRYPTO', 'DATE_TIME', 'US_BANK_NUMBER', 'US_ITIN'
}

# Presidio entity types that constitute PHI (Protected Health Information)
PHI_ENTITY_TYPES = {
    'MEDICAL_LICENSE', 'US_SSN', 'DATE_TIME',  # Can be PHI in medical context
    'PERSON',  # Patient names
    # Note: Presidio doesn't have dedicated PHI recognizers by default
    # but these can be inferred from context
}

# Severity mapping for different PII types
ENTITY_SEVERITY_MAP = {
    'US_SSN': SeverityLevel.CRITICAL,
    'CREDIT_CARD': SeverityLevel.CRITICAL,
    'US_PASSPORT': SeverityLevel.CRITICAL,
    'MEDICAL_LICENSE': SeverityLevel.CRITICAL,
    'US_BANK_NUMBER': SeverityLevel.CRITICAL,
    'EMAIL_ADDRESS': SeverityLevel.HIGH,
    'PHONE_NUMBER': SeverityLevel.HIGH,
    'PERSON': SeverityLevel.HIGH,
    'US_DRIVER_LICENSE': SeverityLevel.HIGH,
    'LOCATION': SeverityLevel.MEDIUM,
    'ADDRESS': SeverityLevel.MEDIUM,
    'DATE_TIME': SeverityLevel.MEDIUM,
    'IP_ADDRESS': SeverityLevel.LOW,
}


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def dataset_to_dataframe(dataset: DatasetMeta) -> pd.DataFrame:
    """Convert DatasetMeta to pandas DataFrame."""
    if not dataset.rows:
        return pd.DataFrame()
    return pd.DataFrame(dataset.rows)


def analyze_text_with_presidio(text: str, language: str = 'en') -> list[dict]:
    """Analyze text for PII/PHI using Presidio."""
    if not PRESIDIO_AVAILABLE or not analyzer or not text:
        return []
    
    try:
        # Analyze with Presidio
        results = analyzer.analyze(
            text=str(text),
            language=language,
            entities=None,  # Detect all entity types
            score_threshold=0.7  # Higher threshold to reduce false positives
        )
        
        # Convert to dict format
        return [
            {
                'type': result.entity_type,
                'start': result.start,
                'end': result.end,
                'score': result.score,
                'text': text[result.start:result.end] if result.start < len(text) else ''
            }
            for result in results
        ]
    except Exception as e:
        logger.warning(f"Presidio analysis failed: {e}")
        return []


def detect_pii_in_dataset(dataset: DatasetMeta) -> dict[str, set[str]]:
    """
    Detect PII across all columns using Presidio.
    Returns dict mapping entity_type -> set of column names.
    
    Strategy: Only flag HIGH-RISK PII entities that are always violations.
    Don't try to filter "safe" columns - let Presidio find real PII.
    """
    if not PRESIDIO_AVAILABLE:
        return {}
    
    df = dataset_to_dataframe(dataset)
    pii_findings = {}
    
    # HIGH-RISK PII TYPES ONLY - these are always violations
    HIGH_RISK_PII = {
        'EMAIL_ADDRESS',      # john@example.com
        'PHONE_NUMBER',       # 555-123-4567
        'US_SSN',            # 123-45-6789
        'CREDIT_CARD',       # 4111-1111-1111-1111
        'US_PASSPORT',       # A12345678
        'US_DRIVER_LICENSE', # D1234567
        'US_BANK_NUMBER',    # Account 123456789
        'IBAN_CODE',         # DE89370400440532013000
        'CRYPTO',            # Crypto wallet addresses
    }
    
    for column in df.columns:
        # Quick pre-check: skip if column dtype is numeric (can't be PII)
        if df[column].dtype in ['int64', 'float64', 'int32', 'float32']:
            continue
        
        # Sample only 10 rows (not 50) for speed
        sample_values = df[column].dropna().head(10).astype(str)
        
        if len(sample_values) == 0:
            continue
        
        # Quick pattern check BEFORE calling Presidio (much faster)
        sample_text = ' '.join(sample_values)
        
        # Skip if no potential PII patterns
        has_potential_pii = (
            '@' in sample_text or  # Email
            any(c.isdigit() for c in sample_text[:100])  # SSN/Phone/Card numbers
        )
        
        if not has_potential_pii:
            continue
        
        # Combine into single text for analysis
        column_text = ' | '.join(sample_values)
        
        # Analyze with Presidio (this is the slow part)
        entities = analyze_text_with_presidio(column_text)
        
        for entity in entities:
            entity_type = entity['type']
            
            # ONLY flag if it's a high-risk PII type
            if entity_type in HIGH_RISK_PII:
                if entity_type not in pii_findings:
                    pii_findings[entity_type] = set()
                pii_findings[entity_type].add(column)
                logger.info(f"Found {entity_type} in column: {column}")
                break  # Stop checking this column once we find PII
    
    return pii_findings


def detect_phi_in_dataset(dataset: DatasetMeta) -> set[str]:
    """
    Detect PHI columns using Presidio.
    Returns set of column names containing PHI.
    
    Strategy: Only flag columns with EXPLICIT medical terminology.
    """
    if not PRESIDIO_AVAILABLE:
        return set()
    
    df = dataset_to_dataframe(dataset)
    phi_columns = set()
    
    # Medical keywords that explicitly indicate PHI
    EXPLICIT_MEDICAL_KEYWORDS = [
        'patient', 'diagnosis', 'medical', 'health', 'prescription',
        'treatment', 'doctor', 'physician', 'hospital', 'clinic',
        'mrn', 'phi', 'lab', 'symptom', 'disease', 'medication',
        'procedure', 'surgery', 'icd', 'cpt', 'dob'  # medical codes
    ]
    
    for column in df.columns:
        col_lower = column.lower()
        
        # ONLY flag if column name has explicit medical terminology
        if any(kw in col_lower for kw in EXPLICIT_MEDICAL_KEYWORDS):
            phi_columns.add(column)
            logger.info(f"PHI detected in column name: {column}")
    
    # Don't scan column values - too many false positives
    # Only flag based on column names
    
    return phi_columns


# ---------------------------------------------------------------------------
# GDPR Compliance Checks
# ---------------------------------------------------------------------------

def check_gdpr_compliance(dataset: DatasetMeta) -> list[ComplianceFinding]:
    """Check GDPR compliance using Presidio PII detection."""
    findings = []
    
    # Detect PII using Presidio
    pii_findings = detect_pii_in_dataset(dataset)
    
    # GDPR-001: Data Minimization
    if pii_findings:
        all_pii_columns = set()
        high_risk_entities = []
        
        for entity_type, columns in pii_findings.items():
            all_pii_columns.update(columns)
            if ENTITY_SEVERITY_MAP.get(entity_type, SeverityLevel.MEDIUM) in (SeverityLevel.CRITICAL, SeverityLevel.HIGH):
                high_risk_entities.append(entity_type)
        
        severity = SeverityLevel.CRITICAL if high_risk_entities else SeverityLevel.HIGH
        
        findings.append(ComplianceFinding(
            regulation=RegulationTag.GDPR,
            rule_id='GDPR-001',
            rule_description='Data minimisation: dataset must not expose unnecessary PII.',
            status=ComplianceStatus.NON_COMPLIANT,
            severity=severity,
            affected_columns=sorted(all_pii_columns),
            details=f"PII detected via Presidio: {', '.join(high_risk_entities) if high_risk_entities else 'multiple types'}. "
                   f"Affected columns: {sorted(all_pii_columns)}",
            remediation="Anonymize or pseudonymize PII columns before including in training data. "
                       "Consider using Presidio's anonymizer to redact sensitive information."
        ))
    
    # GDPR-002: Consent Tracking
    has_pii = bool(pii_findings)
    consent_tag = any(t.lower() in ('consent_verified', 'lawful_basis') for t in dataset.tags)
    
    if has_pii and not consent_tag:
        findings.append(ComplianceFinding(
            regulation=RegulationTag.GDPR,
            rule_id='GDPR-002',
            rule_description='Consent / lawful-basis metadata must be present on datasets with personal data.',
            status=ComplianceStatus.NON_COMPLIANT,
            severity=SeverityLevel.HIGH,
            affected_columns=[],
            details="Dataset contains PII but no 'consent_verified' or 'lawful_basis' tag.",
            remediation="Add a 'consent_verified' tag after obtaining valid GDPR consent."
        ))
    
    # GDPR-003: Right to Erasure
    erasable_tag = any(t.lower() in ('erasable', 'deletion_supported') for t in dataset.tags)
    
    if has_pii and not erasable_tag:
        findings.append(ComplianceFinding(
            regulation=RegulationTag.GDPR,
            rule_id='GDPR-003',
            rule_description='Training data must be erasable: no irreversible embedding of personal data.',
            status=ComplianceStatus.NON_COMPLIANT,
            severity=SeverityLevel.CRITICAL,
            affected_columns=[],
            details="PII present but no 'erasable' or 'deletion_supported' tag.",
            remediation="Implement machine unlearning support or ensure PII is stripped before model training."
        ))
    
    # If no violations, add passing finding
    if not findings:
        findings.append(ComplianceFinding(
            regulation=RegulationTag.GDPR,
            rule_id='GDPR-PASS',
            rule_description='GDPR compliance check passed',
            status=ComplianceStatus.COMPLIANT,
            severity=SeverityLevel.LOW,
            affected_columns=[],
            details='No GDPR violations detected via Presidio analysis.',
            remediation=''
        ))
    
    return findings


# ---------------------------------------------------------------------------
# HIPAA Compliance Checks
# ---------------------------------------------------------------------------

def check_hipaa_compliance(dataset: DatasetMeta) -> list[ComplianceFinding]:
    """Check HIPAA compliance using Presidio PHI detection."""
    findings = []
    
    # Detect PHI using Presidio
    phi_columns = detect_phi_in_dataset(dataset)
    
    # HIPAA-001: PHI Detection
    if phi_columns:
        findings.append(ComplianceFinding(
            regulation=RegulationTag.HIPAA,
            rule_id='HIPAA-001',
            rule_description='Protected Health Information (PHI) must not be present in raw training data.',
            status=ComplianceStatus.NON_COMPLIANT,
            severity=SeverityLevel.CRITICAL,
            affected_columns=sorted(phi_columns),
            details=f"PHI detected via Presidio in columns: {sorted(phi_columns)}",
            remediation="De-identify or remove all 18 HIPAA identifiers before use. "
                       "Use Presidio anonymizer to redact PHI."
        ))
    
    # HIPAA-002: De-identification Tag
    health_tag = any(t.lower() in ('health', 'medical', 'clinical', 'hipaa') for t in dataset.tags)
    deidentified_tag = any(t.lower() in ('deidentified', 'safe_harbour', 'anonymized') for t in dataset.tags)
    
    if health_tag and not deidentified_tag:
        findings.append(ComplianceFinding(
            regulation=RegulationTag.HIPAA,
            rule_id='HIPAA-002',
            rule_description='Dataset must be tagged as de-identified if it originated from health records.',
            status=ComplianceStatus.NON_COMPLIANT,
            severity=SeverityLevel.HIGH,
            affected_columns=[],
            details="Dataset tagged as health-origin but missing de-identification tag.",
            remediation="Apply Safe Harbour de-identification and tag with 'safe_harbour' or 'deidentified'."
        ))
    
    # HIPAA-003: Minimum Necessary
    if phi_columns:
        findings.append(ComplianceFinding(
            regulation=RegulationTag.HIPAA,
            rule_id='HIPAA-003',
            rule_description='Only the minimum necessary PHI columns should be included.',
            status=ComplianceStatus.NON_COMPLIANT,
            severity=SeverityLevel.HIGH,
            affected_columns=sorted(phi_columns),
            details="PHI columns present. Verify minimum necessary justification.",
            remediation="Document clinical justification or remove the columns."
        ))
    
    # If no violations
    if not findings:
        findings.append(ComplianceFinding(
            regulation=RegulationTag.HIPAA,
            rule_id='HIPAA-PASS',
            rule_description='HIPAA compliance check passed',
            status=ComplianceStatus.COMPLIANT,
            severity=SeverityLevel.LOW,
            affected_columns=[],
            details='No HIPAA violations detected via Presidio analysis.',
            remediation=''
        ))
    
    return findings


# ---------------------------------------------------------------------------
# CCPA Compliance Checks
# ---------------------------------------------------------------------------

def check_ccpa_compliance(dataset: DatasetMeta) -> list[ComplianceFinding]:
    """Check CCPA compliance using Presidio PII detection."""
    findings = []
    
    pii_findings = detect_pii_in_dataset(dataset)
    has_pii = bool(pii_findings)
    
    # CCPA-001: Opt-out Rights
    optout_tag = any(t.lower() in ('opted_out_filtered', 'ccpa_compliant') for t in dataset.tags)
    
    if has_pii and not optout_tag:
        findings.append(ComplianceFinding(
            regulation=RegulationTag.CCPA,
            rule_id='CCPA-001',
            rule_description='Dataset must honour opt-out requests; verify no opted-out records remain.',
            status=ComplianceStatus.NON_COMPLIANT,
            severity=SeverityLevel.HIGH,
            affected_columns=[],
            details="Personal data present without opt-out filtering tag.",
            remediation="Filter out records where consumers have exercised CCPA opt-out rights."
        ))
    
    # CCPA-002: Deletion Support
    deletion_tag = any(t.lower() in ('deletion_supported', 'erasable') for t in dataset.tags)
    
    if has_pii and not deletion_tag:
        findings.append(ComplianceFinding(
            regulation=RegulationTag.CCPA,
            rule_id='CCPA-002',
            rule_description='Dataset must support consumer deletion requests.',
            status=ComplianceStatus.NON_COMPLIANT,
            severity=SeverityLevel.MEDIUM,
            affected_columns=[],
            details="Personal data present but deletion-support tag is missing.",
            remediation="Implement a deletion-request pipeline and tag with 'deletion_supported'."
        ))
    
    if not findings:
        findings.append(ComplianceFinding(
            regulation=RegulationTag.CCPA,
            rule_id='CCPA-PASS',
            rule_description='CCPA compliance check passed',
            status=ComplianceStatus.COMPLIANT,
            severity=SeverityLevel.LOW,
            affected_columns=[],
            details='No CCPA violations detected.',
            remediation=''
        ))
    
    return findings


# ---------------------------------------------------------------------------
# ISO 27001 Compliance Checks
# ---------------------------------------------------------------------------

def check_iso27001_compliance(dataset: DatasetMeta) -> list[ComplianceFinding]:
    """Check ISO 27001 compliance (basic checks, Presidio not needed)."""
    findings = []
    
    sensitive_cols = [c for c in dataset.columns 
                     if c.sensitivity.value in ("confidential", "restricted")]
    ac_tag = any(t.lower() in ("access_controlled", "rbac_enforced") for t in dataset.tags)
    
    if sensitive_cols and not ac_tag:
        findings.append(ComplianceFinding(
            regulation=RegulationTag.ISO_27001,
            rule_id="ISO27001-001",
            rule_description="Datasets classified CONFIDENTIAL or RESTRICTED must have access-control tags.",
            status=ComplianceStatus.NON_COMPLIANT,
            severity=SeverityLevel.HIGH,
            affected_columns=[c.name for c in sensitive_cols],
            details="Sensitive columns present without access-control tag.",
            remediation="Enforce RBAC on this dataset and tag with 'access_controlled'."
        ))
    else:
        findings.append(ComplianceFinding(
            regulation=RegulationTag.ISO_27001,
            rule_id="ISO27001-PASS",
            rule_description="ISO 27001 access control check passed",
            status=ComplianceStatus.COMPLIANT,
            severity=SeverityLevel.LOW,
            affected_columns=[],
            details="Access control properly configured.",
            remediation=""
        ))
    
    return findings


# ---------------------------------------------------------------------------
# PCI-DSS Compliance Checks
# ---------------------------------------------------------------------------

def check_pcidss_compliance(dataset: DatasetMeta) -> list[ComplianceFinding]:
    """Check PCI-DSS compliance using Presidio credit card detection."""
    findings = []
    
    pii_findings = detect_pii_in_dataset(dataset)
    
    # Check for credit card data
    card_columns = pii_findings.get('CREDIT_CARD', set())
    
    # Also check column names
    for col in dataset.columns:
        lower = col.name.lower()
        if any(kw in lower for kw in ("card", "pan", "ccn", "cvv", "cvc")):
            card_columns.add(col.name)
    
    if card_columns:
        findings.append(ComplianceFinding(
            regulation=RegulationTag.PCI_DSS,
            rule_id="PCIDSS-001",
            rule_description="Cardholder data (PANs, CVVs) must never appear in training datasets.",
            status=ComplianceStatus.NON_COMPLIANT,
            severity=SeverityLevel.CRITICAL,
            affected_columns=sorted(card_columns),
            details=f"Credit card data detected by Presidio in columns: {sorted(card_columns)}",
            remediation="Remove all cardholder data. If tokenized, verify tokens are PCI-compliant. "
                       "Never store full PANs in training sets."
        ))
    else:
        findings.append(ComplianceFinding(
            regulation=RegulationTag.PCI_DSS,
            rule_id="PCIDSS-PASS",
            rule_description="PCI-DSS cardholder data check passed",
            status=ComplianceStatus.COMPLIANT,
            severity=SeverityLevel.LOW,
            affected_columns=[],
            details="No cardholder data detected by Presidio.",
            remediation=""
        ))
    
    return findings


# ---------------------------------------------------------------------------
# Main Scan Function
# ---------------------------------------------------------------------------

def run_scan(
    dataset: DatasetMeta,
    regulations: list[RegulationTag],
    strict_mode: bool = False,
) -> ComplianceScanResult:
    """
    Run compliance scan using Microsoft Presidio for PII/PHI detection.
    
    This function maintains API compatibility with the original but uses
    Presidio under the hood for accurate PII/PHI detection.
    """
    scan_id = str(uuid.uuid4())
    findings: list[ComplianceFinding] = []
    
    logger.info(f"Starting Presidio compliance scan: {scan_id}")
    
    # Update dataset columns with Presidio detections
    if PRESIDIO_AVAILABLE:
        try:
            pii_findings = detect_pii_in_dataset(dataset)
            phi_columns = detect_phi_in_dataset(dataset)
            
            # Mark columns as containing PII/PHI
            for col in dataset.columns:
                if any(col.name in cols for cols in pii_findings.values()):
                    col.contains_pii = True
                if col.name in phi_columns:
                    col.contains_phi = True
        except Exception as e:
            logger.warning(f"Presidio detection failed: {e}")
    
    # Run regulation-specific checks
    for reg in regulations:
        try:
            if reg == RegulationTag.GDPR:
                findings.extend(check_gdpr_compliance(dataset))
            elif reg == RegulationTag.HIPAA:
                findings.extend(check_hipaa_compliance(dataset))
            elif reg == RegulationTag.CCPA:
                findings.extend(check_ccpa_compliance(dataset))
            elif reg == RegulationTag.ISO_27001:
                findings.extend(check_iso27001_compliance(dataset))
            elif reg == RegulationTag.PCI_DSS:
                findings.extend(check_pcidss_compliance(dataset))
        except Exception as e:
            logger.error(f"Error checking {reg.value}: {e}", exc_info=True)
    
    # Aggregate per-regulation status
    summary: dict[RegulationTag, ComplianceStatus] = {}
    for reg in regulations:
        reg_findings = [f for f in findings if f.regulation == reg]
        if any(f.status == ComplianceStatus.NON_COMPLIANT for f in reg_findings):
            summary[reg] = ComplianceStatus.NON_COMPLIANT
        elif all(f.status in (ComplianceStatus.COMPLIANT, ComplianceStatus.SKIPPED) for f in reg_findings):
            summary[reg] = ComplianceStatus.COMPLIANT
        else:
            summary[reg] = ComplianceStatus.PENDING
    
    overall = (
        ComplianceStatus.NON_COMPLIANT
        if ComplianceStatus.NON_COMPLIANT in summary.values()
        else ComplianceStatus.COMPLIANT
    )
    
    # Audit log
    audit_logger.log(
        "compliance_scan",
        {
            "scan_id": scan_id,
            "dataset_id": dataset.dataset_id,
            "regulations": [r.value for r in regulations],
            "strict_mode": strict_mode,
            "overall_status": overall.value,
            "finding_count": len(findings),
            "presidio_enabled": PRESIDIO_AVAILABLE
        },
    )
    
    logger.info(f"Scan {scan_id} complete: {overall.value}, {len(findings)} findings")
    
    return ComplianceScanResult(
        scan_id=scan_id,
        dataset_id=dataset.dataset_id,
        overall_status=overall,
        findings=findings,
        summary=summary,
    )