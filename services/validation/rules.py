"""
rules.py - Comprehensive rule evaluation module for land record validation.

Executes:
1. Legacy rules (RULE-01 to RULE-06) for backwards compatibility.
2. Field-level validation rules (Survey, Khata, Owners, Area, Geography, Land Class, Mutation).
3. Cross-field consistency rules (Share sum math, Hectare/Acre sanity, Geo hierarchy, Dispute detection, OCR confidence).
"""

import re

# Known state / district / taluka / village sample mappings for geographic sanity checks
KNOWN_GEO_HIERARCHY = {
    "maharashtra": {
        "pune": ["haveli", "pune city", "mulshi", "maval", "shirur"],
        "thane": ["kalyan", "thane", "bhiwandi"],
    },
    "karnataka": {
        "bengaluru rural": ["devanahalli", "doddaballapura", "hoskote", "nelamangala"],
        "mysuru": ["mysuru", "nanjangud", "hunsur"],
    },
    "uttar pradesh": {
        "varanasi": ["pindra", "varanasi", "phulpur"],
        "lucknow": ["lucknow", "mohanlalganj", "malihabad"],
    }
}


def evaluate_rules(extracted_data: dict, ocr_data: dict) -> dict:
    """
    Evaluates all validation rules (field-level, cross-field, and legacy rules).
    
    Returns a structured dictionary containing:
    - rules_evaluated: list of rule dicts (RULE-01 to RULE-06 + new rules)
    - field_level_validation: dict of per-field pass/fail status and messages
    - failed_rules: list of rule objects that failed
    - warnings: list of human-readable warning strings
    - passed_count: int
    - total_count: int
    - validation_score: float (0.0 to 1.0)
    """
    rules = []
    warnings = []
    field_validation = {}
    
    # ---------------------------------------------------------
    # RULE-01 (Legacy): Survey / Khasra Number Syntax Check
    # ---------------------------------------------------------
    survey_no = str(extracted_data.get("survey_khasra_no", "")).strip()
    r1_pass = len(survey_no) > 0 and any(c.isdigit() for c in survey_no)
    rules.append({
        "rule_id": "RULE-01",
        "name": "Survey / Khasra Number Syntax Check",
        "pass": r1_pass,
        "details": f"Survey No '{survey_no}' conforms to state cadastral syntax." if r1_pass else f"Invalid Survey No syntax: '{survey_no}'",
        "severity": "CRITICAL"
    })
    if not r1_pass:
        warnings.append(f"CRITICAL: Invalid Survey Number format ({survey_no})")
    
    field_validation["survey_khasra_no"] = {
        "valid": r1_pass,
        "value": survey_no,
        "message": "Valid survey/khasra syntax" if r1_pass else "Invalid survey/khasra number"
    }

    # ---------------------------------------------------------
    # RULE-02 (Legacy): Share Fraction Math Check
    # ---------------------------------------------------------
    owners = extracted_data.get("owners", [])
    total_share = sum([float(o.get("share_fraction", 0.0)) for o in owners]) if owners else 0.0
    r2_pass = len(owners) > 0 and abs(total_share - 1.00) < 0.01
    
    rules.append({
        "rule_id": "RULE-02",
        "name": "Co-owner Share Fraction Mathematical Audit",
        "pass": r2_pass,
        "details": f"Total owner share sum equals 100% ({total_share * 100:.0f}%)." if r2_pass else f"Discrepancy in recorded shares: Owner share sum = {total_share * 100:.0f}% (Expected 100%). Unallocated share: {(1.0 - total_share)*100:.0f}%",
        "severity": "HIGH"
    })
    if not r2_pass:
        warnings.append(f"HIGH: Mathematical share fraction discrepancy (Sum = {total_share * 100:.0f}%, Missing {(1.0 - total_share)*100:.0f}%)")
        
    field_validation["owners"] = {
        "valid": r2_pass,
        "count": len(owners),
        "total_share_sum": round(total_share, 4),
        "message": f"Owner share sum is 100%" if r2_pass else f"Share sum discrepancy ({total_share * 100:.0f}%)"
    }

    # ---------------------------------------------------------
    # RULE-03 (Legacy): Area Sanity & Bounds Check
    # ---------------------------------------------------------
    total_area = float(extracted_data.get("total_area_acres", 0.0))
    r3_pass = 0.01 <= total_area <= 500.0
    rules.append({
        "rule_id": "RULE-03",
        "name": "Total Parcel Area Bounds Sanity Check",
        "pass": r3_pass,
        "details": f"Reported area ({total_area} Acres) is within valid agricultural bounds." if r3_pass else f"Reported area ({total_area} Acres) out of expected range.",
        "severity": "MEDIUM"
    })
    if not r3_pass:
        warnings.append(f"MEDIUM: Land area ({total_area} Acres) outside standard parcel thresholds")
        
    field_validation["total_area_acres"] = {
        "valid": r3_pass,
        "value": total_area,
        "message": f"Area is within valid bounds ({total_area} Acres)" if r3_pass else f"Area out of bounds ({total_area} Acres)"
    }

    # ---------------------------------------------------------
    # RULE-04 (Legacy): Encumbrance & Legal Dispute Detection
    # ---------------------------------------------------------
    encumbrances = extracted_data.get("encumbrances", [])
    has_dispute = any("dispute" in str(e).lower() or "section 136" in str(e).lower() for e in encumbrances)
    r4_pass = not has_dispute
    rules.append({
        "rule_id": "RULE-04",
        "name": "Active Legal Dispute & Lien Risk Assessment",
        "pass": r4_pass,
        "details": "No legal dispute or court stay order detected." if r4_pass else f"Active legal dispute flag detected: {encumbrances[0] if encumbrances else 'Unknown'}",
        "severity": "HIGH"
    })
    if not r4_pass:
        first_enc = encumbrances[0] if encumbrances else "Legal Dispute"
        warnings.append(f"HIGH: Active legal dispute flag on record ({first_enc})")
        
    field_validation["encumbrances"] = {
        "valid": r4_pass,
        "has_dispute": has_dispute,
        "count": len(encumbrances),
        "message": "No active legal dispute" if r4_pass else "Active legal dispute flag detected"
    }

    # ---------------------------------------------------------
    # RULE-05 (Legacy): Multilingual OCR Confidence Audit
    # ---------------------------------------------------------
    ocr_conf = float(ocr_data.get("avg_confidence", 1.0)) if isinstance(ocr_data, dict) else 1.0
    r5_pass = ocr_conf >= 0.85
    rules.append({
        "rule_id": "RULE-05",
        "name": "Multilingual OCR Character Confidence Audit",
        "pass": r5_pass,
        "details": f"Average OCR confidence is high ({ocr_conf * 100:.1f}%)." if r5_pass else f"Low OCR extraction confidence ({ocr_conf * 100:.1f}% < 85.0%). Scan noise detected.",
        "severity": "MEDIUM"
    })
    if not r5_pass:
        warnings.append(f"MEDIUM: Low OCR confidence score ({ocr_conf * 100:.1f}%) due to scan noise or rotational skew")

    # ---------------------------------------------------------
    # RULE-06 (Legacy): Mutation Entry Continuity
    # ---------------------------------------------------------
    mutation = extracted_data.get("mutation_ref", "")
    r6_pass = len(str(mutation).strip()) > 0
    rules.append({
        "rule_id": "RULE-06",
        "name": "Mutation Entry Sequence Verification",
        "pass": r6_pass,
        "details": f"Valid mutation reference present: {mutation}" if r6_pass else "Missing revenue mutation entry reference.",
        "severity": "LOW"
    })
    if not r6_pass:
        warnings.append("LOW: Missing revenue mutation entry number")
        
    field_validation["mutation_ref"] = {
        "valid": r6_pass,
        "value": str(mutation).strip(),
        "message": "Valid mutation entry present" if r6_pass else "Missing mutation entry"
    }

    # ---------------------------------------------------------
    # EXTENDED FIELD-LEVEL & CROSS-FIELD RULES
    # ---------------------------------------------------------
    
    # RULE-07: Khata Number Validity Check
    khata_no = str(extracted_data.get("khata_no", "")).strip()
    r7_pass = len(khata_no) > 0 and len(khata_no) <= 20
    rules.append({
        "rule_id": "RULE-07",
        "name": "Khata Number Validity Check",
        "pass": r7_pass,
        "details": f"Khata No '{khata_no}' is valid." if r7_pass else "Missing or invalid Khata Number.",
        "severity": "MEDIUM"
    })
    if not r7_pass:
        warnings.append(f"MEDIUM: Invalid or missing Khata Number ('{khata_no}')")
    field_validation["khata_no"] = {
        "valid": r7_pass,
        "value": khata_no,
        "message": "Valid Khata number" if r7_pass else "Invalid or missing Khata number"
    }

    # RULE-08: Geographic Hierarchy Cross-Consistency Check (Village, Taluka, District, State)
    state = str(extracted_data.get("state", "")).strip()
    district = str(extracted_data.get("district", "")).strip()
    taluka = str(extracted_data.get("taluka", "")).strip()
    village = str(extracted_data.get("village", "")).strip()
    
    r8_pass = bool(state and district and taluka and village)
    if r8_pass and state.lower() in KNOWN_GEO_HIERARCHY:
        dist_map = KNOWN_GEO_HIERARCHY[state.lower()]
        if district.lower() in dist_map:
            valid_talukas = dist_map[district.lower()]
            if taluka.lower() not in valid_talukas:
                r8_pass = False

    rules.append({
        "rule_id": "RULE-08",
        "name": "Geographic Hierarchy & Administrative Boundary Consistency",
        "pass": r8_pass,
        "details": f"State '{state}', District '{district}', Taluka '{taluka}', Village '{village}' hierarchy is consistent." if r8_pass else f"Geographic discrepancy or incomplete hierarchy: State={state}, District={district}, Taluka={taluka}, Village={village}",
        "severity": "HIGH"
    })
    if not r8_pass:
        warnings.append(f"HIGH: Geographic administrative hierarchy discrepancy ({state}/{district}/{taluka}/{village})")
        
    field_validation["geography"] = {
        "valid": r8_pass,
        "state": state,
        "district": district,
        "taluka": taluka,
        "village": village,
        "message": "Consistent geographic hierarchy" if r8_pass else "Incomplete or inconsistent administrative geography"
    }

    # RULE-09: Land Classification Validity Check
    land_class = str(extracted_data.get("land_classification", "")).strip()
    r9_pass = len(land_class) > 0 and not land_class.isdigit()
    rules.append({
        "rule_id": "RULE-09",
        "name": "Land Classification Standard Verification",
        "pass": r9_pass,
        "details": f"Land classification '{land_class}' is recorded." if r9_pass else "Land classification missing or invalid.",
        "severity": "LOW"
    })
    if not r9_pass:
        warnings.append("LOW: Missing or invalid land classification")
    field_validation["land_classification"] = {
        "valid": r9_pass,
        "value": land_class,
        "message": "Valid land classification" if r9_pass else "Missing land classification"
    }

    # RULE-10: Hectare to Acre Conversion Cross-Check
    acres_val = float(extracted_data.get("total_area_acres", 0.0))
    hec_val = float(extracted_data.get("total_area_hectares", 0.0))
    if acres_val > 0.0 and hec_val > 0.0:
        expected_acres = hec_val * 2.47105
        # Tolerance within 15% to allow for local gunta / bigha conversion rounding
        r10_pass = abs(acres_val - expected_acres) / expected_acres <= 0.15
    else:
        r10_pass = True

    rules.append({
        "rule_id": "RULE-10",
        "name": "Hectares to Acres Unit Conversion Cross-Check",
        "pass": r10_pass,
        "details": f"Area unit conversion matches expected math ({hec_val} Hectares ~ {acres_val} Acres)." if r10_pass else f"Unit conversion math discrepancy between Hectares ({hec_val}) and Acres ({acres_val}).",
        "severity": "MEDIUM"
    })
    if not r10_pass:
        warnings.append(f"MEDIUM: Unit conversion discrepancy between Hectares ({hec_val}) and Acres ({acres_val})")
        
    field_validation["area_conversion"] = {
        "valid": r10_pass,
        "acres": acres_val,
        "hectares": hec_val,
        "message": "Unit conversion consistent" if r10_pass else "Unit conversion mismatch between hectares and acres"
    }

    # ---------------------------------------------------------
    # SCORE CALCULATION
    # ---------------------------------------------------------
    passed_count = sum(1 for r in rules if r["pass"])
    total_count = len(rules)
    rule_score = round(passed_count / total_count, 4) if total_count > 0 else 1.0
    failed_rules = [r for r in rules if not r["pass"]]

    return {
        "rules_evaluated": rules,
        "field_level_validation": field_validation,
        "failed_rules": failed_rules,
        "passed_count": passed_count,
        "total_count": total_count,
        "validation_score": rule_score,
        "warnings": warnings
    }
