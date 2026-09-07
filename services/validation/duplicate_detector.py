"""
duplicate_detector.py - Modular Duplicate Detection Engine.

Uses:
1. RapidFuzz for fuzzy string similarity on cadastral identifiers (Survey No, Village, Khata, Owners).
2. Scikit-Learn TF-IDF Vectorizer & Cosine Similarity for OCR text variations and record text matching.
"""

import numpy as np
from typing import List, Dict, Any, Optional

try:
    from rapidfuzz import fuzz
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


class DuplicateDetector:
    """
    Detects potential duplicate land records using fuzzy string matching
    and TF-IDF cosine similarity.
    """

    def __init__(self, duplicate_threshold: float = 0.80):
        self.duplicate_threshold = duplicate_threshold

    def _fallback_string_similarity(self, s1: str, s2: str) -> float:
        """Simple Levenshtein ratio fallback if rapidfuzz is unavailable."""
        s1, s2 = str(s1 or "").lower().strip(), str(s2 or "").lower().strip()
        if not s1 and not s2:
            return 1.0
        if not s1 or not s2:
            return 0.0
        if s1 == s2:
            return 1.0
        # Character overlap ratio fallback
        set1, set2 = set(s1), set(s2)
        intersection = set1.intersection(set2)
        union = set1.union(set2)
        return len(intersection) / len(union) if union else 0.0

    def compute_fuzzy_similarity(self, str1: str, str2: str) -> float:
        """Computes similarity score between two strings (0.0 to 1.0)."""
        str1_clean = str(str1 or "").strip().lower()
        str2_clean = str(str2 or "").strip().lower()
        
        if not str1_clean or not str2_clean:
            return 0.0
        if str1_clean == str2_clean:
            return 1.0

        if RAPIDFUZZ_AVAILABLE:
            ratio = fuzz.ratio(str1_clean, str2_clean) / 100.0
            token_ratio = fuzz.token_sort_ratio(str1_clean, str2_clean) / 100.0
            return max(ratio, token_ratio)
        else:
            return self._fallback_string_similarity(str1_clean, str2_clean)

    def _build_record_text(self, record: Dict[str, Any]) -> str:
        """Constructs a composite text representation of a land record for TF-IDF."""
        survey = record.get("survey_no") or record.get("survey_khasra_no") or ""
        khata = record.get("khata_no") or ""
        village = record.get("village") or ""
        district = record.get("district") or ""
        state = record.get("state") or ""
        
        owners_list = record.get("owners") or []
        owner_names = []
        if isinstance(owners_list, list):
            for o in owners_list:
                if isinstance(o, dict):
                    owner_names.append(o.get("name", ""))
                elif isinstance(o, str):
                    owner_names.append(o)
                    
        owners_text = " ".join(owner_names)
        encumbrances = " ".join([str(e) for e in (record.get("encumbrances") or [])])
        mutation = record.get("mutation_ref") or ""

        return f"{survey} {khata} {village} {district} {state} {owners_text} {encumbrances} {mutation}".strip()

    def compute_tfidf_similarity(self, text1: str, text2: str) -> float:
        """Computes TF-IDF Cosine Similarity between two text documents (0.0 to 1.0)."""
        t1, t2 = text1.strip(), text2.strip()
        if not t1 or not t2:
            return 0.0
        if t1 == t2:
            return 1.0

        if SKLEARN_AVAILABLE:
            try:
                vectorizer = TfidfVectorizer().fit([t1, t2])
                tfidf_matrix = vectorizer.transform([t1, t2])
                sim = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
                return float(sim)
            except Exception:
                return self._fallback_string_similarity(t1, t2)
        else:
            return self._fallback_string_similarity(t1, t2)

    def detect_duplicate(
        self,
        target_record: Dict[str, Any],
        existing_records: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Compares target_record against a list of existing_records.
        
        Returns:
        - duplicate_score: float (0.0 to 1.0)
        - is_duplicate: bool
        - matched_record_id: str or None
        - metrics: dict of similarity components
        - details: str
        """
        if not existing_records:
            return {
                "duplicate_score": 0.0,
                "is_duplicate": False,
                "matched_record_id": None,
                "metrics": {"survey_sim": 0.0, "village_sim": 0.0, "tfidf_sim": 0.0},
                "details": "No existing records available for comparison."
            }

        target_survey = str(target_record.get("survey_khasra_no") or target_record.get("survey_no") or "").strip()
        target_village = str(target_record.get("village") or "").strip()
        target_khata = str(target_record.get("khata_no") or "").strip()
        target_text = self._build_record_text(target_record)

        best_score = 0.0
        best_match_id = None
        best_metrics = {}

        for rec in existing_records:
            # Skip comparing record with itself if ID matches
            target_id = target_record.get("id")
            rec_id = rec.get("id")
            if target_id and rec_id and target_id == rec_id:
                continue

            rec_survey = str(rec.get("survey_no") or rec.get("survey_khasra_no") or "").strip()
            rec_village = str(rec.get("village") or "").strip()
            rec_khata = str(rec.get("khata_no") or "").strip()
            rec_text = self._build_record_text(rec)

            survey_sim = self.compute_fuzzy_similarity(target_survey, rec_survey)
            village_sim = self.compute_fuzzy_similarity(target_village, rec_village)
            khata_sim = self.compute_fuzzy_similarity(target_khata, rec_khata)
            tfidf_sim = self.compute_tfidf_similarity(target_text, rec_text)

            # Combined duplicate score formula:
            # Survey No (35%) + Village (25%) + Khata (15%) + Composite Text TF-IDF (25%)
            composite_score = (survey_sim * 0.35) + (village_sim * 0.25) + (khata_sim * 0.15) + (tfidf_sim * 0.25)

            # Exact match boost: If survey, village, and khata match exactly -> high confidence duplicate
            if survey_sim >= 0.95 and village_sim >= 0.90 and (khata_sim >= 0.90 or not target_khata):
                composite_score = max(composite_score, 0.95)

            if composite_score > best_score:
                best_score = composite_score
                best_match_id = rec_id
                best_metrics = {
                    "survey_similarity": round(survey_sim, 3),
                    "village_similarity": round(village_sim, 3),
                    "khata_similarity": round(khata_sim, 3),
                    "tfidf_similarity": round(tfidf_sim, 3)
                }

        duplicate_score = round(float(best_score), 4)
        is_duplicate = duplicate_score >= self.duplicate_threshold

        if is_duplicate:
            details = f"Potential duplicate detected (Score: {duplicate_score * 100:.1f}%) matching Record ID '{best_match_id}'."
        else:
            details = f"Low duplicate risk (Highest match score: {duplicate_score * 100:.1f}%)."

        return {
            "duplicate_score": duplicate_score,
            "is_duplicate": is_duplicate,
            "matched_record_id": best_match_id,
            "metrics": best_metrics,
            "details": details
        }
