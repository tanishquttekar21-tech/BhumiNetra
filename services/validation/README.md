# BhumiNetra Modular ML + Validation Engine

## Overview
The `services/validation` module provides a comprehensive, explainable land-record validation architecture for BhumiNetra. It combines data normalization, field-level syntax checks, cross-field logical rules, fuzzy string matching + TF-IDF duplicate detection, Scikit-Learn Isolation Forest anomaly detection, and explainable confidence scoring.

---

## Architecture Overview

```
                          Extracted Land Record + OCR Data
                                         │
                                         ▼
                             [1. Data Normalization]
                       (Indic Digits -> ASCII, Clean Text, Area Units)
                                         │
                                         ▼
                            [2. Rule Evaluation Engine]
                       (Field Syntax + Cross-Field Consistency)
                                         │
                   ┌─────────────────────┼─────────────────────┐
                   ▼                     ▼                     ▼
        [3. Duplicate Detector]  [4. Anomaly Detector]  [5. Rules Score]
        (RapidFuzz + TF-IDF)     (Isolation Forest)     (Pass Ratio)
                   │                     │                     │
                   └─────────────────────┼─────────────────────┘
                                         ▼
                         [6. Confidence & Decision Calculator]
                     (Weighted Base Score - Risk Penalties)
                                         │
                                         ▼
                              Explainable JSON Output
                     (VALID / REVIEW_REQUIRED / INVALID)
```

---

## Integration Guide

### 1. Simple Function Call (Standard API)
```python
from services.validation import validate_land_record

extracted_fields = {
    "survey_khasra_no": "142/3A",
    "khata_no": "8842",
    "village": "Wagholi",
    "district": "Pune",
    "state": "Maharashtra",
    "total_area_acres": 4.05,
    "total_area_hectares": 1.64,
    "owners": [
        {"name": "Rameshwar Laxman Patil", "share_fraction": 0.50},
        {"name": "Sunita Rameshwar Patil", "share_fraction": 0.50}
    ],
    "encumbrances": [],
    "mutation_ref": "Mutation Entry No: 12480"
}

ocr_data = {"avg_confidence": 0.95}

# Validate record (pass optional existing_records for live duplicate detection)
result = validate_land_record(extracted_fields, ocr_data)
```

---

## JSON Response Schema Interpretation

The `validate_land_record` function returns a dictionary structured as follows:

```json
{
  "decision": "VALID",
  "status": "AUTO_ACCEPTED",
  "decision_label": "HIGH CONFIDENCE (Auto Accepted)",
  "review_required": false,
  "overall_confidence": 92.5,
  "validation_score": 1.0,
  "duplicate_probability": 0.05,
  "anomaly_score": 0.10,
  
  "field_level_validation": {
    "survey_khasra_no": { "valid": true, "value": "142/3A", "message": "Valid survey/khasra syntax" },
    "owners": { "valid": true, "count": 2, "total_share_sum": 1.0, "message": "Owner share sum is 100%" },
    "total_area_acres": { "valid": true, "value": 4.05, "message": "Area is within valid bounds (4.05 Acres)" },
    "encumbrances": { "valid": true, "has_dispute": false, "count": 0, "message": "No active legal dispute" },
    "mutation_ref": { "valid": true, "value": "Mutation Entry No: 12480", "message": "Valid mutation entry present" },
    "khata_no": { "valid": true, "value": "8842", "message": "Valid Khata number" },
    "geography": { "valid": true, "state": "Maharashtra", "district": "Pune", "taluka": "Haveli", "village": "Wagholi", "message": "Consistent geographic hierarchy" },
    "area_conversion": { "valid": true, "acres": 4.05, "hectares": 1.64, "message": "Unit conversion consistent" }
  },

  "failed_rules": [],
  "warnings": [],

  "reasons": [
    "Base score: 95.0% (OCR: 95.0%, Field Extraction: 85.0%, Rules: 100.0%).",
    "Record meets all validation standards and confidence thresholds."
  ],

  "confidence_breakdown": {
    "base_confidence_pct": 92.5,
    "ocr_confidence_pct": 95.0,
    "extraction_confidence_pct": 85.0,
    "rule_score_pct": 100.0,
    "duplicate_penalty_pct": 0.0,
    "anomaly_penalty_pct": 0.0
  },

  "rules_evaluated": [ ... ],
  "passed_count": 10,
  "total_count": 10
}
```

---

## Response Fields Summary

| Key | Type | Description |
|---|---|---|
| `decision` | `str` | `"VALID"`, `"REVIEW_REQUIRED"`, or `"INVALID"` |
| `status` | `str` | Mapped pipeline status (`"AUTO_ACCEPTED"`, `"PENDING_HUMAN_REVIEW"`, `"INVALID"`) |
| `review_required` | `bool` | `true` if human inspector review is required; `false` otherwise |
| `overall_confidence` | `float` | Explainable overall confidence percentage (`0.0` to `100.0`) |
| `duplicate_probability`| `float` | RapidFuzz + TF-IDF duplicate score (`0.0` to `1.0`) |
| `anomaly_score` | `float` | Scikit-Learn Isolation Forest anomaly score (`0.0` to `1.0`) |
| `field_level_validation`| `dict` | Per-field validation pass/fail breakdown |
| `failed_rules` | `list` | List of rule objects that failed |
| `warnings` | `list` | Human-readable warning messages |
| `reasons` | `list` | Detailed explainable reasoning behind decision & penalties |
