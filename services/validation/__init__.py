"""
BhumiNetra Validation Package:
Provides data normalization, field-level rules, cross-field validation,
duplicate detection, anomaly detection, and explainable confidence scoring.
"""

from services.validation.engine import validate_land_record, ValidationEngine

__all__ = ["validate_land_record", "ValidationEngine"]
