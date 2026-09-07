"""
anomaly_detector.py - Modular Anomaly Detection Engine.

Uses:
1. Scikit-Learn Isolation Forest model when sufficient training samples exist.
2. Statistical z-score / IQR boundary fallback for zero-downtime operations on small datasets.
"""

import numpy as np
from typing import List, Dict, Any, Tuple

try:
    from sklearn.ensemble import IsolationForest
    SKLEARN_IFOREST_AVAILABLE = True
except ImportError:
    SKLEARN_IFOREST_AVAILABLE = False


class AnomalyDetector:
    """
    Detects statistical and structural anomalies in land records using
    Isolation Forest or fallback heuristic rules.
    """

    def __init__(self, anomaly_threshold: float = 0.50):
        self.anomaly_threshold = anomaly_threshold
        self.model = None
        self.is_fitted = False

    def _extract_feature_vector(self, record: Dict[str, Any], ocr_data: Dict[str, Any] = None) -> List[float]:
        """
        Extracts 7 key numerical features for anomaly scoring:
        1. total_area_acres
        2. total_area_hectares
        3. owner_count
        4. total_share_sum
        5. ocr_confidence
        6. extraction_confidence
        7. encumbrance_count
        """
        ocr_data = ocr_data or {}
        
        acres = float(record.get("total_area_acres", 0.0))
        hectares = float(record.get("total_area_hectares", 0.0))
        
        owners = record.get("owners", [])
        owner_count = len(owners) if isinstance(owners, list) else 0
        
        total_share = sum([float(o.get("share_fraction", 0.0)) for o in owners]) if isinstance(owners, list) else 0.0
        
        ocr_conf = float(ocr_data.get("avg_confidence", record.get("ocr_confidence", 85.0)))
        if ocr_conf > 1.0:
            ocr_conf = ocr_conf / 100.0
            
        ext_conf = float(record.get("extraction_confidence", 0.85))
        
        encumbrances = record.get("encumbrances", [])
        enc_count = len(encumbrances) if isinstance(encumbrances, list) else 0

        return [
            acres,
            hectares,
            float(owner_count),
            float(total_share),
            float(ocr_conf),
            float(ext_conf),
            float(enc_count)
        ]

    def fit(self, dataset: List[Dict[str, Any]]):
        """Fits IsolationForest if sklearn is available and dataset has >= 5 records."""
        if not SKLEARN_IFOREST_AVAILABLE or not dataset or len(dataset) < 5:
            self.is_fitted = False
            return

        try:
            X = np.array([self._extract_feature_vector(rec) for rec in dataset])
            # Train Isolation Forest with contamination=0.15
            self.model = IsolationForest(n_estimators=50, contamination=0.15, random_state=42)
            self.model.fit(X)
            self.is_fitted = True
        except Exception:
            self.is_fitted = False

    def compute_anomaly_score(
        self,
        extracted_data: Dict[str, Any],
        ocr_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Computes anomaly score (0.0 to 1.0) and explainable reasons.
        """
        features = self._extract_feature_vector(extracted_data, ocr_data)
        acres, hectares, owner_count, total_share, ocr_conf, ext_conf, enc_count = features

        reasons = []
        anomaly_components = []

        # -----------------------------------------------------
        # Feature 1: Area Anomaly Check
        # -----------------------------------------------------
        if acres <= 0.0:
            anomaly_components.append(0.8)
            reasons.append("Zero or negative land area recorded.")
        elif acres > 100.0:
            anomaly_components.append(0.6)
            reasons.append(f"Unusually large agricultural parcel area ({acres} Acres).")
        elif abs(acres - (hectares * 2.47105)) > 1.0:
            anomaly_components.append(0.4)
            reasons.append(f"Inconsistent hectare-to-acre ratio ({hectares} Ha vs {acres} Ac).")

        # -----------------------------------------------------
        # Feature 2: Owner & Share Anomaly Check
        # -----------------------------------------------------
        if owner_count == 0:
            anomaly_components.append(0.9)
            reasons.append("No recorded owners present in document.")
        elif abs(total_share - 1.0) >= 0.05:
            anomaly_components.append(0.7)
            reasons.append(f"Co-owner share discrepancy (Total share sum = {total_share * 100:.0f}%).")
        elif owner_count > 15:
            anomaly_components.append(0.4)
            reasons.append(f"Unusually high co-owner count ({owner_count} owners).")

        # -----------------------------------------------------
        # Feature 3: OCR & Extraction Quality Anomaly Check
        # -----------------------------------------------------
        if ocr_conf < 0.60:
            anomaly_components.append(0.7)
            reasons.append(f"Severely low OCR character confidence ({ocr_conf * 100:.1f}%).")
        elif ocr_conf < 0.80:
            anomaly_components.append(0.3)
            reasons.append(f"Moderate OCR scan noise ({ocr_conf * 100:.1f}%).")

        # -----------------------------------------------------
        # Feature 4: Encumbrance & Legal Dispute Anomaly Check
        # -----------------------------------------------------
        encumbrances = extracted_data.get("encumbrances", [])
        has_legal_stay = any("dispute" in str(e).lower() or "stay" in str(e).lower() or "section 136" in str(e).lower() for e in encumbrances)
        if has_legal_stay:
            anomaly_components.append(0.8)
            reasons.append("Active court dispute or Section 136 stay order attached to parcel.")
        elif enc_count >= 3:
            anomaly_components.append(0.5)
            reasons.append(f"High number of active encumbrances/liens ({enc_count}).")

        # -----------------------------------------------------
        # ML Isolation Forest Scoring (if trained model available)
        # -----------------------------------------------------
        ml_anomaly_score = 0.0
        method_used = "StatisticalFallback"

        if self.is_fitted and self.model:
            try:
                X_val = np.array([features])
                # decision_function returns negative values for anomalies
                raw_score = self.model.decision_function(X_val)[0]
                # Normalize raw decision score to [0.0, 1.0] anomaly score
                ml_anomaly_score = max(0.0, min(1.0, float(0.5 - raw_score)))
                method_used = "IsolationForest"
            except Exception:
                method_used = "StatisticalFallback"

        # Combine heuristic score with ML score
        heuristic_score = max(anomaly_components) if anomaly_components else 0.0
        
        if method_used == "IsolationForest":
            final_anomaly_score = round(0.5 * heuristic_score + 0.5 * ml_anomaly_score, 4)
        else:
            final_anomaly_score = round(heuristic_score, 4)

        is_anomalous = final_anomaly_score >= self.anomaly_threshold

        return {
            "anomaly_score": final_anomaly_score,
            "is_anomalous": is_anomalous,
            "method_used": method_used,
            "reasons": reasons if reasons else ["No structural anomalies detected."]
        }
