"""
test_validation_engine.py - Unit Test Suite for Modular ML + Validation Engine.

Tests:
1. Data Normalization (Indic numerals, string cleaning, cadastral formatting, area unit conversions).
2. Field-Level Validation Rules.
3. Cross-Field Consistency Checks.
4. Duplicate Detection (RapidFuzz & TF-IDF Cosine Similarity).
5. Anomaly Detection (Isolation Forest & Fallback).
6. Confidence Score & Decision Classification.
7. Engine Integration & Sample Dataset.
"""

import unittest
import os
import sys

# Add repository root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.validation.normalization import (
    normalize_indic_numerals, clean_text, normalize_cadastral_no,
    normalize_khata_no, normalize_area, normalize_owners, normalize_land_record
)
from services.validation.rules import evaluate_rules
from services.validation.duplicate_detector import DuplicateDetector
from services.validation.anomaly_detector import AnomalyDetector
from services.validation.confidence import ConfidenceCalculator
from services.validation.engine import ValidationEngine, validate_land_record
from services.validation.sample_dataset import get_sample_land_records


class TestNormalization(unittest.TestCase):

    def test_indic_numeral_conversion(self):
        self.assertEqual(normalize_indic_numerals("१४२/३A"), "142/3A")
        self.assertEqual(normalize_indic_numerals("८८४२"), "8842")
        self.assertEqual(normalize_indic_numerals("೦೧೨೩"), "0123")

    def test_text_cleaning(self):
        self.assertEqual(clean_text("  Rameshwar   Patil \n "), "Rameshwar Patil")

    def test_cadastral_normalization(self):
        self.assertEqual(normalize_cadastral_no(" १४२ / ३A "), "142/3A")
        self.assertEqual(normalize_cadastral_no("512 \\ 1"), "512/1")

    def test_khata_normalization(self):
        self.assertEqual(normalize_khata_no(" 00319 "), "319")
        self.assertEqual(normalize_khata_no("0"), "0")

    def test_area_unit_normalization(self):
        # Convert Hectares to Acres if Acres missing
        acres, hec = normalize_area(0.0, 1.0)
        self.assertAlmostEqual(acres, 2.47, places=2)
        self.assertEqual(hec, 1.0)

        # Convert Acres to Hectares if Hectares missing
        acres2, hec2 = normalize_area(2.47105, 0.0)
        self.assertEqual(acres2, 2.47)
        self.assertAlmostEqual(hec2, 1.0, places=2)

    def test_owner_normalization(self):
        raw_owners = [
            {"name": "  Shri Rameshwar Patil ", "share_fraction": "0.50"},
            {"name": "Sunita Patil", "share_fraction": 0.50}
        ]
        owners = normalize_owners(raw_owners)
        self.assertEqual(len(owners), 2)
        self.assertEqual(owners[0]["name"], "Shri Rameshwar Patil")
        self.assertEqual(owners[0]["share_fraction"], 0.50)


class TestValidationRules(unittest.TestCase):

    def test_valid_record_rules(self):
        valid_rec = {
            "survey_khasra_no": "142/3A",
            "khata_no": "8842",
            "state": "Maharashtra",
            "district": "Pune",
            "taluka": "Haveli",
            "village": "Wagholi",
            "total_area_acres": 4.05,
            "total_area_hectares": 1.64,
            "land_classification": "Jirayat",
            "owners": [
                {"name": "Owner A", "share_fraction": 0.50},
                {"name": "Owner B", "share_fraction": 0.50}
            ],
            "encumbrances": [],
            "mutation_ref": "MUT-12345"
        }
        ocr_data = {"avg_confidence": 0.95}

        res = evaluate_rules(valid_rec, ocr_data)
        self.assertEqual(res["validation_score"], 1.0)
        self.assertEqual(len(res["failed_rules"]), 0)
        self.assertEqual(res["passed_count"], res["total_count"])

    def test_share_fraction_and_dispute_failures(self):
        invalid_rec = {
            "survey_khasra_no": "101",
            "khata_no": "500",
            "state": "Karnataka",
            "district": "Bengaluru Rural",
            "taluka": "Devanahalli",
            "village": "Vijayapura",
            "total_area_acres": 2.50,
            "total_area_hectares": 1.01,
            "owners": [
                {"name": "Owner A", "share_fraction": 0.40},
                {"name": "Owner B", "share_fraction": 0.30}  # Sum = 0.70 != 1.0
            ],
            "encumbrances": ["Active dispute notice under Section 136"],
            "mutation_ref": "MR-109"
        }
        ocr_data = {"avg_confidence": 0.75}

        res = evaluate_rules(invalid_rec, ocr_data)
        self.assertLess(res["validation_score"], 1.0)
        failed_ids = [r["rule_id"] for r in res["failed_rules"]]
        self.assertIn("RULE-02", failed_ids)  # Share fraction check
        self.assertIn("RULE-04", failed_ids)  # Legal dispute check
        self.assertIn("RULE-05", failed_ids)  # Low OCR confidence


class TestDuplicateDetector(unittest.TestCase):

    def setUp(self):
        self.detector = DuplicateDetector(duplicate_threshold=0.80)
        self.existing_records = get_sample_land_records()

    def test_exact_duplicate_detection(self):
        target = {
            "survey_khasra_no": "142/3A",
            "khata_no": "8842",
            "village": "Wagholi",
            "district": "Pune",
            "state": "Maharashtra",
            "owners": [{"name": "Rameshwar Laxman Patil"}]
        }
        res = self.detector.detect_duplicate(target, self.existing_records)
        self.assertTrue(res["is_duplicate"])
        self.assertGreaterEqual(res["duplicate_score"], 0.85)

    def test_unique_record_detection(self):
        target = {
            "survey_khasra_no": "9999/UNIQUE",
            "khata_no": "777777",
            "village": "NonExistentVillage",
            "district": "UniqueDistrict",
            "state": "UnknownState",
            "owners": [{"name": "Unique Owner Person"}]
        }
        res = self.detector.detect_duplicate(target, self.existing_records)
        self.assertFalse(res["is_duplicate"])
        self.assertLess(res["duplicate_score"], 0.50)


class TestAnomalyDetector(unittest.TestCase):

    def setUp(self):
        self.detector = AnomalyDetector(anomaly_threshold=0.50)
        self.detector.fit(get_sample_land_records())

    def test_normal_record_anomaly_score(self):
        normal_rec = {
            "total_area_acres": 4.05,
            "total_area_hectares": 1.64,
            "owners": [{"share_fraction": 0.5}, {"share_fraction": 0.5}],
            "encumbrances": [],
            "extraction_confidence": 0.95
        }
        ocr_data = {"avg_confidence": 0.95}
        res = self.detector.compute_anomaly_score(normal_rec, ocr_data)
        self.assertFalse(res["is_anomalous"])
        self.assertLess(res["anomaly_score"], 0.50)

    def test_extreme_anomalous_record(self):
        anomalous_rec = {
            "total_area_acres": 450.0,
            "total_area_hectares": 0.50,
            "owners": [],  # Zero owners
            "encumbrances": ["Dispute", "Stay order", "Lien attachment"],
            "extraction_confidence": 0.50
        }
        ocr_data = {"avg_confidence": 0.50}
        res = self.detector.compute_anomaly_score(anomalous_rec, ocr_data)
        self.assertTrue(res["is_anomalous"])
        self.assertGreaterEqual(res["anomaly_score"], 0.50)


class TestConfidenceCalculator(unittest.TestCase):

    def setUp(self):
        self.calc = ConfidenceCalculator(valid_threshold=85.0, review_threshold=50.0)

    def test_high_confidence_valid(self):
        res = self.calc.calculate_confidence(
            ocr_confidence=0.95,
            extraction_confidence=0.95,
            rule_score=1.0,
            duplicate_score=0.0,
            anomaly_score=0.0
        )
        self.assertEqual(res["decision"], "VALID")
        self.assertEqual(res["status"], "AUTO_ACCEPTED")
        self.assertFalse(res["review_required"])
        self.assertGreaterEqual(res["overall_confidence"], 85.0)

    def test_low_confidence_pending_review(self):
        res = self.calc.calculate_confidence(
            ocr_confidence=0.70,
            extraction_confidence=0.75,
            rule_score=0.60,
            duplicate_score=0.20,
            anomaly_score=0.30
        )
        self.assertEqual(res["decision"], "REVIEW_REQUIRED")
        self.assertEqual(res["status"], "PENDING_HUMAN_REVIEW")
        self.assertTrue(res["review_required"])
        self.assertLess(res["overall_confidence"], 85.0)


class TestValidationEngineIntegration(unittest.TestCase):

    def test_engine_returns_all_required_keys(self):
        engine = ValidationEngine()
        sample = get_sample_land_records()[0]
        res = engine.validate(sample, {"avg_confidence": 0.95})

        required_keys = [
            "field_level_validation",
            "failed_rules",
            "warnings",
            "duplicate_probability",
            "anomaly_score",
            "overall_confidence",
            "review_required",
            "reasons",
            "decision",
            "status",
            "rules_evaluated",
            "passed_count",
            "total_count",
            "validation_score"
        ]

        for k in required_keys:
            self.assertIn(k, res, f"Missing key '{k}' in engine response")

        self.assertIsInstance(res["field_level_validation"], dict)
        self.assertIsInstance(res["failed_rules"], list)
        self.assertIsInstance(res["warnings"], list)
        self.assertIsInstance(res["duplicate_probability"], float)
        self.assertIsInstance(res["anomaly_score"], float)
        self.assertIsInstance(res["overall_confidence"], float)
        self.assertIsInstance(res["review_required"], bool)
        self.assertIsInstance(res["reasons"], list)

    def test_standalone_validate_land_record_function(self):
        sample = get_sample_land_records()[0]
        res = validate_land_record(sample, {"avg_confidence": 0.95}, existing_records=[])
        self.assertIn("overall_confidence", res)
        self.assertEqual(res["decision"], "VALID")


if __name__ == "__main__":
    unittest.main()
