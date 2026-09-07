"""
validator.py - Main Land Record Validation Entry Point.

Delegates execution to the modular validation engine (services.validation).
Preserves existing API signatures while adding data normalization, extended field rules,
cross-field consistency, RapidFuzz duplicate detection, Isolation Forest anomaly scoring,
and explainable confidence score calculation.
"""

from services.validation.engine import validate_land_record as modular_validate_land_record


def validate_land_record(extracted_data, ocr_data, existing_records=None):
    """
    Automated Land Record Validation & Anomaly Engine:
    Executes rule-based checks, data normalization, duplicate detection,
    Isolation Forest anomaly scoring, and explainable confidence calculations.
    """
    return modular_validate_land_record(extracted_data, ocr_data, existing_records=existing_records)
