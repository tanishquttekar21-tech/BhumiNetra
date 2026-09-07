"""
confidence.py - Explainable Confidence Scoring and Decision Engine.

Combines:
- OCR character confidence
- Rule-based evaluation score
- Duplicate probability penalty
- Anomaly score penalty

Classifies land records into:
- VALID (AUTO_ACCEPTED)
- REVIEW_REQUIRED (PENDING_HUMAN_REVIEW)
- INVALID (REJECTED / INVALID)
"""

from typing import List, Dict, Any, Tuple


class ConfidenceCalculator:
    """
    Computes an explainable overall confidence score and decision status.
    """

    def __init__(self, valid_threshold: float = 85.0, review_threshold: float = 50.0):
        self.valid_threshold = valid_threshold
        self.review_threshold = review_threshold

    def calculate_confidence(
        self,
        ocr_confidence: float,
        extraction_confidence: float,
        rule_score: float,
        duplicate_score: float,
        anomaly_score: float,
        failed_rules: List[Dict[str, Any]] = None,
        warnings: List[str] = None
    ) -> Dict[str, Any]:
        """
        Calculates overall confidence percentage (0.0% to 100.0%) and decision.
        """
        failed_rules = failed_rules or []
        warnings = warnings or []

        # Ensure values are floats in [0.0, 1.0]
        ocr_conf = max(0.0, min(1.0, float(ocr_confidence)))
        if ocr_conf > 1.0:
            ocr_conf = ocr_conf / 100.0
            
        ext_conf = max(0.0, min(1.0, float(extraction_confidence)))
        r_score = max(0.0, min(1.0, float(rule_score)))
        dup_score = max(0.0, min(1.0, float(duplicate_score)))
        anom_score = max(0.0, min(1.0, float(anomaly_score)))

        # Weighted base confidence calculation
        # (OCR Conf * 35%) + (Extraction Conf * 25%) + (Rule Validation * 40%)
        base_confidence = (ocr_conf * 0.35) + (ext_conf * 0.25) + (r_score * 0.40)

        # Risk Penalties
        # Penalty for potential duplicate: up to -30%
        # Penalty for anomaly: up to -25%
        duplicate_penalty = dup_score * 0.30
        anomaly_penalty = anom_score * 0.25

        net_confidence = base_confidence - duplicate_penalty - anomaly_penalty
        overall_confidence_pct = round(max(0.0, min(100.0, net_confidence * 100.0)), 1)

        # Explainable Reasons Assembly
        reasons = []
        reasons.append(f"Base score: {base_confidence * 100:.1f}% (OCR: {ocr_conf*100:.1f}%, Field Extraction: {ext_conf*100:.1f}%, Rules: {r_score*100:.1f}%).")
        
        if duplicate_penalty > 0.05:
            reasons.append(f"Applied duplicate risk penalty: -{duplicate_penalty*100:.1f}% (Duplicate probability: {dup_score*100:.1f}%).")
            
        if anomaly_penalty > 0.05:
            reasons.append(f"Applied anomaly risk penalty: -{anomaly_penalty*100:.1f}% (Anomaly risk score: {anom_score*100:.1f}%).")

        has_critical_failure = any(r.get("severity") == "CRITICAL" for r in failed_rules)
        critical_count = sum(1 for r in failed_rules if r.get("severity") == "CRITICAL")
        high_count = sum(1 for r in failed_rules if r.get("severity") == "HIGH")

        if has_critical_failure:
            reasons.append("CRITICAL rule failure detected (e.g. invalid Survey/Khasra number syntax).")

        if high_count > 0:
            reasons.append(f"Detected {high_count} HIGH severity rule warning(s).")

        # -----------------------------------------------------
        # DECISION LOGIC
        # -----------------------------------------------------
        if overall_confidence_pct >= self.valid_threshold and not has_critical_failure and dup_score < 0.80 and anom_score < 0.70:
            decision = "VALID"
            status = "AUTO_ACCEPTED"
            decision_label = "HIGH CONFIDENCE (Auto Accepted)"
            review_required = False
            reasons.append("Record meets all validation standards and confidence thresholds.")
        elif overall_confidence_pct >= self.review_threshold or has_critical_failure or dup_score >= 0.80 or anom_score >= 0.50:
            decision = "REVIEW_REQUIRED"
            status = "PENDING_HUMAN_REVIEW"
            decision_label = "LOW CONFIDENCE (Human Review Required)"
            review_required = True
            reasons.append("Record flagged for human inspector verification.")
        else:
            decision = "INVALID"
            status = "INVALID"
            decision_label = "INVALID / REJECTED RECORD"
            review_required = True
            reasons.append("Record score below minimum validity threshold.")

        return {
            "overall_confidence": overall_confidence_pct,
            "decision": decision,
            "status": status,
            "decision_label": decision_label,
            "review_required": review_required,
            "breakdown": {
                "base_confidence_pct": round(base_confidence * 100.0, 1),
                "ocr_confidence_pct": round(ocr_conf * 100.0, 1),
                "extraction_confidence_pct": round(ext_conf * 100.0, 1),
                "rule_score_pct": round(r_score * 100.0, 1),
                "duplicate_penalty_pct": round(duplicate_penalty * 100.0, 1),
                "anomaly_penalty_pct": round(anomaly_penalty * 100.0, 1)
            },
            "reasons": reasons
        }
