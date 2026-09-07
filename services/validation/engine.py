"""
engine.py - Orchestrator for the Modular ML + Validation Engine.

Unites Data Normalization, Rule Evaluation, Duplicate Detection, Anomaly Detection,
and Explainable Confidence Scoring into a single unified API endpoint.
"""

from typing import Dict, Any, List, Optional
from services.validation.normalization import normalize_land_record
from services.validation.rules import evaluate_rules
from services.validation.duplicate_detector import DuplicateDetector
from services.validation.anomaly_detector import AnomalyDetector
from services.validation.confidence import ConfidenceCalculator
from services.validation.sample_dataset import get_sample_land_records


class ValidationEngine:
    """
    Main Validation Engine orchestrating ML and Rule-based validation pipelines.
    """

    def __init__(
        self,
        duplicate_threshold: float = 0.80,
        anomaly_threshold: float = 0.50,
        valid_threshold: float = 85.0,
        review_threshold: float = 50.0,
        train_anomaly_on_samples: bool = True
    ):
        self.duplicate_detector = DuplicateDetector(duplicate_threshold=duplicate_threshold)
        self.anomaly_detector = AnomalyDetector(anomaly_threshold=anomaly_threshold)
        self.confidence_calculator = ConfidenceCalculator(
            valid_threshold=valid_threshold,
            review_threshold=review_threshold
        )

        if train_anomaly_on_samples:
            samples = get_sample_land_records()
            self.anomaly_detector.fit(samples)

    def validate(
        self,
        extracted_data: Dict[str, Any],
        ocr_data: Dict[str, Any] = None,
        existing_records: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Executes complete validation pipeline:
        1. Normalization
        2. Rule evaluation (field-level + cross-field + legacy rules)
        3. Duplicate detection (RapidFuzz + TF-IDF cosine similarity)
        4. Anomaly detection (Isolation Forest + fallback)
        5. Explainable confidence scoring & decision classification
        """
        ocr_data = ocr_data or {}
        extracted_data = extracted_data or {}

        # STEP 1: Normalize input data
        normalized_data = normalize_land_record(extracted_data)

        # STEP 2: Evaluate rules
        rule_results = evaluate_rules(normalized_data, ocr_data)

        # STEP 3: Duplicate detection
        # Combine existing records with sample dataset if existing records are not provided
        records_to_compare = existing_records if existing_records is not None else get_sample_land_records()
        dup_results = self.duplicate_detector.detect_duplicate(normalized_data, records_to_compare)

        # STEP 4: Anomaly detection
        anom_results = self.anomaly_detector.compute_anomaly_score(normalized_data, ocr_data)

        # STEP 5: Confidence & Decision Calculation
        ocr_conf = float(ocr_data.get("avg_confidence", 1.0))
        ext_conf = float(normalized_data.get("extraction_confidence", 0.85))
        rule_score = float(rule_results["validation_score"])
        dup_prob = float(dup_results["duplicate_score"])
        anom_score = float(anom_results["anomaly_score"])

        confidence_res = self.confidence_calculator.calculate_confidence(
            ocr_confidence=ocr_conf,
            extraction_confidence=ext_conf,
            rule_score=rule_score,
            duplicate_score=dup_prob,
            anomaly_score=anom_score,
            failed_rules=rule_results["failed_rules"],
            warnings=rule_results["warnings"]
        )

        # Combine all reasons into explainable output
        all_reasons = []
        all_reasons.extend(confidence_res.get("reasons", []))
        if dup_results["is_duplicate"]:
            all_reasons.append(dup_results["details"])
        if anom_results["is_anomalous"]:
            all_reasons.extend(anom_results.get("reasons", []))

        # Preserve legacy warnings list + rule failures
        all_warnings = list(rule_results.get("warnings", []))

        # Assemble full output dictionary
        return {
            # ---------------------------------------------------------
            # NEW MODULAR VALIDATION API FIELDS (Requirements 8 & 9)
            # ---------------------------------------------------------
            "field_level_validation": rule_results["field_level_validation"],
            "failed_rules": rule_results["failed_rules"],
            "warnings": all_warnings,
            "duplicate_probability": dup_prob,
            "duplicate_details": dup_results,
            "anomaly_score": anom_score,
            "anomaly_details": anom_results,
            "overall_confidence": confidence_res["overall_confidence"],
            "decision": confidence_res["decision"],
            "decision_label": confidence_res["decision_label"],
            "status": confidence_res["status"],
            "review_required": confidence_res["review_required"],
            "reasons": all_reasons,
            "confidence_breakdown": confidence_res["breakdown"],

            # ---------------------------------------------------------
            # BACKWARDS COMPATIBILITY FIELDS (for app.py and legacy tests)
            # ---------------------------------------------------------
            "rules_evaluated": rule_results["rules_evaluated"],
            "passed_count": rule_results["passed_count"],
            "total_count": rule_results["total_count"],
            "validation_score": rule_score,
            "normalized_data": normalized_data
        }


# Global default engine instance for standalone helper function
_default_engine = ValidationEngine()


def validate_land_record(
    extracted_data: Dict[str, Any],
    ocr_data: Dict[str, Any] = None,
    existing_records: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Standalone validation function matching legacy signature.
    """
    return _default_engine.validate(extracted_data, ocr_data, existing_records)
