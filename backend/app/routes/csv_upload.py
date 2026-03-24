"""
routes/csv_upload.py
====================
New router for CSV file uploads and processing.

POST /csv/scan - Upload CSV file, auto-detect schema, run compliance scan
"""

from __future__ import annotations

import io
import csv
from datetime import datetime
from typing import Any

from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse

from app.schemas import (
    DatasetMeta,
    DatasetColumn,
    DataClassification,
    RegulationTag,
)
from app import presidio_wrapper as compliance_engine
from app.services import logger

router = APIRouter(prefix="/csv", tags=["CSV Upload"])


def infer_column_type(values: list[Any]) -> str:
    """Infer data type from sample values."""
    # Remove None/empty values
    clean_values = [v for v in values if v is not None and str(v).strip() != '']
    if not clean_values:
        return "string"
    
    # Try to detect numeric
    try:
        [float(v) for v in clean_values[:5]]
        return "float" if any('.' in str(v) for v in clean_values[:5]) else "integer"
    except:
        pass
    
    # Try to detect date
    sample = str(clean_values[0]).lower()
    if any(word in sample for word in ['date', 'time', '202', '/']):
        return "datetime"
    
    return "string"


def detect_pii_phi(column_name: str, sample_values: list[Any]) -> tuple[bool, bool, DataClassification]:
    """
    Detect if column contains PII/PHI based on name and values.
    
    Strategy: Default to PUBLIC. Only mark as sensitive if EXPLICIT high-risk indicators.
    """
    name_lower = column_name.lower()
    
    # HIGH-RISK PII keywords (always violations)
    HIGH_RISK_PII_KEYWORDS = ['email', 'phone', 'ssn', 'social_security', 'passport', 
                              'driver_license', 'credit_card', 'card_number', 'cvv', 'ccn']
    contains_pii = any(kw in name_lower for kw in HIGH_RISK_PII_KEYWORDS)
    
    # EXPLICIT PHI keywords (medical data only)
    PHI_KEYWORDS = ['patient', 'diagnosis', 'medical', 'prescription', 
                    'treatment', 'doctor', 'physician', 'mrn', 'phi', 'icd']
    contains_phi = any(kw in name_lower for kw in PHI_KEYWORDS)
    
    # Check sample values ONLY for email patterns (most obvious PII)
    sample_str = ' '.join(str(v) for v in sample_values[:5] if v)
    if '@' in sample_str and any(kw in name_lower for kw in ['email', 'contact', 'address']):
        contains_pii = True
    
    # Determine sensitivity
    if contains_phi:
        sensitivity = DataClassification.RESTRICTED
    elif contains_pii:
        sensitivity = DataClassification.CONFIDENTIAL
    else:
        # DEFAULT TO PUBLIC for business data
        sensitivity = DataClassification.PUBLIC
    
    return contains_pii, contains_phi, sensitivity


def parse_csv_to_dataset(
    file_content: bytes,
    dataset_id: str,
    dataset_name: str,
    source: str,
    owner: str,
    tags: list[str]
) -> DatasetMeta:
    """Parse CSV file into DatasetMeta format."""
    
    # Decode CSV
    text = file_content.decode('utf-8-sig')  # Handle BOM
    reader = csv.DictReader(io.StringIO(text))
    
    # Read rows (limit to 100 for performance)
    rows = []
    for i, row in enumerate(reader):
        if i >= 100:  # Stop after 100 rows
            break
        # Clean up the row - remove empty string values
        clean_row = {k: v for k, v in row.items() if v is not None and str(v).strip() != ''}
        if clean_row:  # Only add non-empty rows
            rows.append(clean_row)
    
    if not rows:
        raise ValueError("CSV file is empty or contains no valid data")
    
    # Get column names
    column_names = list(rows[0].keys())
    
    # Build column metadata
    columns = []
    for col_name in column_names:
        # Collect values for this column
        col_values = [row.get(col_name) for row in rows if row.get(col_name)]
        sample_values = col_values[:5]
        
        # Infer type
        dtype = infer_column_type(col_values)
        
        # Detect PII/PHI
        contains_pii, contains_phi, sensitivity = detect_pii_phi(col_name, col_values)
        
        columns.append(DatasetColumn(
            name=col_name,
            dtype=dtype,
            contains_pii=contains_pii,
            contains_phi=contains_phi,
            sensitivity=sensitivity,
            sample_values=sample_values
        ))
    
    # Create dataset metadata
    return DatasetMeta(
        dataset_id=dataset_id,
        name=dataset_name,
        source=source,
        owner=owner,
        columns=columns,
        tags=tags,
        rows=rows[:100],  # Limit to first 100 rows for processing
        created_at=datetime.utcnow()
    )


# ---------------------------------------------------------------------------
# POST /csv/scan
# ---------------------------------------------------------------------------


@router.post("/scan")
async def scan_csv_file(
    file: UploadFile = File(..., description="CSV file to scan"),
    dataset_name: str = Form(default="", description="Optional dataset name"),
    owner: str = Form(default="", description="Optional owner/team name"),
    tags: str = Form(default="", description="Comma-separated tags"),
    regulations: str = Form(
        default="GDPR,HIPAA,CCPA,ISO27001,PCI_DSS",
        description="Comma-separated regulation tags"
    ),
    strict_mode: bool = Form(default=False, description="Enable strict mode")
):
    """
    Upload a CSV file and run compliance scan.
    
    The endpoint will:
    1. Parse the CSV file
    2. Auto-detect column types and PII/PHI
    3. Run compliance checks across all specified regulations
    4. Return a full scan result
    
    Example usage with curl:
    ```bash
    curl -X POST http://localhost:8000/csv/scan \
      -F "file=@training_data.csv" \
      -F "dataset_name=Customer Training Data" \
      -F "owner=ml-team" \
      -F "tags=production,training"
    ```
    """
    
    # Validate file type
    if not file.filename or not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a .csv file")
    
    try:
        # Read file content
        content = await file.read()
        
        # Generate dataset ID from filename
        dataset_id = f"csv_{file.filename.replace('.csv', '').replace(' ', '_').replace('.', '_')}"
        
        # Use filename as dataset name if not provided
        if not dataset_name:
            dataset_name = file.filename.replace('.csv', '').replace('_', ' ').title()
        
        # Parse tags
        tag_list = [t.strip() for t in tags.split(',') if t.strip()] if tags else []
        
        # Parse regulations
        reg_list = []
        if regulations:
            for reg in regulations.split(','):
                reg = reg.strip().upper()
                # Map ISO27001 to ISO_27001 (enum uses underscore)
                if reg == 'ISO27001':
                    reg = 'ISO_27001'
                # Map PCI_DSS variations
                if reg == 'PCI-DSS' or reg == 'PCIDSS':
                    reg = 'PCI_DSS'
                # Try to get the regulation enum
                try:
                    reg_list.append(RegulationTag[reg])
                except KeyError:
                    logger.warning(f"Unknown regulation: {reg}, skipping")
        
        if not reg_list:
            reg_list = list(RegulationTag)  # Default to all
        
        logger.info(f"Processing CSV upload: {file.filename} ({len(content)} bytes)")
        
        # Parse CSV to dataset
        dataset = parse_csv_to_dataset(
            file_content=content,
            dataset_id=dataset_id,
            dataset_name=dataset_name,
            source=f"csv_upload:{file.filename}",
            owner=owner,
            tags=tag_list
        )
        
        logger.info(f"Parsed dataset: {len(dataset.rows)} rows, {len(dataset.columns)} columns")
        
        # Run compliance scan using Microsoft Presidio
        result = compliance_engine.run_scan(
            dataset=dataset,
            regulations=reg_list,
            strict_mode=strict_mode
        )
        
        logger.info(f"Scan complete: {result.overall_status.value}, {len(result.findings)} findings")
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing CSV: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process CSV: {str(e)}")