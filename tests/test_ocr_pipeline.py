"""
test_ocr_pipeline.py - Dedicated Unit Test Suite for BhumiNetra AI/OCR Pipeline.

Tests:
1. Image Preprocessing Pipeline (OpenCV stages, options, image_path preservation, non-destructive check).
2. Multilingual OCR Engine (Presets, Real Engine fallback, schema verification, reading order).
3. Safe Post-Processing & Devanagari/Marathi Unicode Preservation.
4. Confidence Scoring & Low-Confidence Block Filtering.
5. Extensible Handwriting Detection (HTR pathway).
"""

import os
import sys
import unittest
import numpy as np
import cv2

# Ensure repository root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.image_processor import (
    process_land_record_image, correct_illumination, remove_noise,
    upscale_if_low_res, clean_border_margins
)
from services.ocr_engine import (
    run_multilingual_ocr, safe_ocr_post_process, infer_script_from_text,
    infer_field_hint, detect_handwriting_features, recognize_handwritten_text
)

SAMPLE_DOCS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "sample_docs"))
TEST_IMAGE_PATH = os.path.join(SAMPLE_DOCS_DIR, "maharashtra_712_clean.png")


class TestImagePreprocessing(unittest.TestCase):

    def test_01_preprocessing_output_schema(self):
        if not os.path.exists(TEST_IMAGE_PATH):
            self.skipTest(f"Sample image not found at {TEST_IMAGE_PATH}")

        res = process_land_record_image(TEST_IMAGE_PATH)

        required_keys = ["image_path", "width", "height", "skew_angle", "roi_count", "rois", "stages"]
        for k in required_keys:
            self.assertIn(k, res, f"Missing key '{k}' in preprocessing output")

        stage_keys = ["raw", "grayscale", "binarized", "deskewed", "grid_overlay", "roi_overlay"]
        for sk in stage_keys:
            self.assertIn(sk, res["stages"], f"Missing stage '{sk}' in stages dictionary")
            self.assertTrue(res["stages"][sk].startswith("data:image/png;base64,"))

    def test_02_custom_preprocessing_options(self):
        if not os.path.exists(TEST_IMAGE_PATH):
            self.skipTest(f"Sample image not found at {TEST_IMAGE_PATH}")

        opts = {"clahe_clip": 3.0, "upscale": True, "fast_nlm": False, "margin_px": 10}
        res = process_land_record_image(TEST_IMAGE_PATH, options=opts)
        self.assertGreater(res["width"], 0)
        self.assertGreater(res["height"], 0)

    def test_03_original_file_unmodified(self):
        if not os.path.exists(TEST_IMAGE_PATH):
            self.skipTest(f"Sample image not found at {TEST_IMAGE_PATH}")

        mtime_before = os.path.getmtime(TEST_IMAGE_PATH)
        process_land_record_image(TEST_IMAGE_PATH)
        mtime_after = os.path.getmtime(TEST_IMAGE_PATH)
        self.assertEqual(mtime_before, mtime_after, "Original image file was modified on disk!")


class TestOCREngine(unittest.TestCase):

    def test_01_preset_ocr_schemas(self):
        presets = ["712_maharashtra", "rtc_karnataka", "up_khasra", "custom_upload"]

        for preset in presets:
            ocr_res = run_multilingual_ocr(preset)

            self.assertIn("script", ocr_res)
            self.assertIn("total_blocks", ocr_res)
            self.assertIn("avg_confidence", ocr_res)
            self.assertIn("confidence_percentage", ocr_res)
            self.assertIn("blocks", ocr_res)
            self.assertIn("low_confidence_blocks", ocr_res)
            self.assertIn("detected_languages", ocr_res)
            self.assertIn("has_handwriting", ocr_res)

            self.assertIsInstance(ocr_res["blocks"], list)
            self.assertTrue(len(ocr_res["blocks"]) > 0)

            for b in ocr_res["blocks"]:
                self.assertIn("id", b)
                self.assertIn("bbox", b)
                self.assertIn("text", b)
                self.assertIn("raw_text", b)
                self.assertIn("lang", b)
                self.assertIn("script", b)
                self.assertIn("conf", b)
                self.assertIn("is_handwritten", b)
                self.assertIn("field_hint", b)
                self.assertTrue(0.0 <= b["conf"] <= 1.0)

    def test_02_layout_reading_order(self):
        ocr_res = run_multilingual_ocr("712_maharashtra")
        blocks = ocr_res["blocks"]

        # Check top-to-bottom reading order (y coordinate)
        y_coords = [b["bbox"][1] for b in blocks]
        # Allow slight line-grouping tolerance
        grouped_y = [y // 20 for y in y_coords]
        self.assertEqual(grouped_y, sorted(grouped_y), "OCR blocks are not properly sorted in reading order!")

    def test_03_low_confidence_block_detection(self):
        ocr_res = run_multilingual_ocr("rtc_karnataka")
        low_conf = ocr_res["low_confidence_blocks"]
        self.assertTrue(len(low_conf) > 0, "Low-confidence blocks were not detected for rtc_karnataka preset!")
        for b in low_conf:
            self.assertLess(b["conf"], 0.85)


class TestSafePostProcessingAndUnicode(unittest.TestCase):

    def test_01_devanagari_marathi_unicode_preservation(self):
        devanagari_str = "VILLAGE FORM NO. 7/12 ( अधिकार अभिलेख पत्रक )"
        cleaned = safe_ocr_post_process(devanagari_str, lang="Devanagari")
        self.assertIn("अधिकार अभिलेख पत्रक", cleaned)

    def test_02_land_record_identifiers_unmodified(self):
        cadastral = "Survey / Khasra No: 142/3A"
        khata = "Khata No: 00319"
        cleaned_cad = safe_ocr_post_process(cadastral)
        cleaned_khata = safe_ocr_post_process(khata)
        self.assertEqual(cleaned_cad, cadastral)
        self.assertEqual(cleaned_khata, khata)

    def test_03_script_and_field_hint_inference(self):
        script_name, lang_name = infer_script_from_text("जिल्हा Pune")
        self.assertIn("Devanagari", script_name)

        hint = infer_field_hint("Khasra No: 512/1")
        self.assertEqual(hint, "survey_khasra_no")


class TestHandwritingPathway(unittest.TestCase):

    def test_01_handwriting_feature_analyzer(self):
        dummy_crop = np.ones((50, 100, 3), dtype=np.uint8) * 255
        is_hw, penalty = detect_handwriting_features(dummy_crop)
        self.assertIsInstance(is_hw, bool)
        self.assertIsInstance(penalty, float)

    def test_02_htr_model_recognizer_fallback(self):
        raw = "Handwritten Entry 104"
        res = recognize_handwritten_text(None, raw_ocr_text=raw)
        self.assertEqual(res, raw)


if __name__ == "__main__":
    unittest.main()
