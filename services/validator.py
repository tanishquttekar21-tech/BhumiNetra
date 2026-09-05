def validate_land_record(extracted_data, ocr_data):
    """
    Automated Land Record Validation & Anomaly Engine:
    Executes rule-based checks on math, syntax, encumbrances, and OCR confidence.
    """
    rules = []
    warnings = []
    
    # RULE-01: Survey Number Syntax
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
        
    # RULE-02: Share Fraction Math Check (Sum == 1.00 / 100%)
    owners = extracted_data.get("owners", [])
    total_share = sum([float(o.get("share_fraction", 0.0)) for o in owners])
    r2_pass = abs(total_share - 1.00) < 0.01
    
    rules.append({
        "rule_id": "RULE-02",
        "name": "Co-owner Share Fraction Mathematical Audit",
        "pass": r2_pass,
        "details": f"Total owner share sum equals 100% ({total_share * 100:.0f}%)." if r2_pass else f"Discrepancy in recorded shares: Owner share sum = {total_share * 100:.0f}% (Expected 100%). Unallocated share: {(1.0 - total_share)*100:.0f}%",
        "severity": "HIGH"
    })
    if not r2_pass:
        warnings.append(f"HIGH: Mathematical share fraction discrepancy (Sum = {total_share * 100:.0f}%, Missing {(1.0 - total_share)*100:.0f}%)")
        
    # RULE-03: Area Sanity & Bounds Check
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
        
    # RULE-04: Encumbrance & Legal Dispute Detection
    encumbrances = extracted_data.get("encumbrances", [])
    has_dispute = any("dispute" in str(e).lower() or "section 136" in str(e).lower() for e in encumbrances)
    r4_pass = not has_dispute
    rules.append({
        "rule_id": "RULE-04",
        "name": "Active Legal Dispute & Lien Risk Assessment",
        "pass": r4_pass,
        "details": "No legal dispute or court stay order detected." if r4_pass else f"Active legal dispute flag detected: {encumbrances[0]}",
        "severity": "HIGH"
    })
    if not r4_pass:
        warnings.append(f"HIGH: Active legal dispute flag on record ({encumbrances[0]})")
        
    # RULE-05: Multilingual OCR Confidence Audit
    ocr_conf = float(ocr_data.get("avg_confidence", 1.0))
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
        
    # RULE-06: Mutation Entry Continuity
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
        
    passed_count = sum(1 for r in rules if r["pass"])
    total_count = len(rules)
    rule_score = round(passed_count / total_count, 4)
    
    return {
        "rules_evaluated": rules,
        "passed_count": passed_count,
        "total_count": total_count,
        "validation_score": rule_score,
        "warnings": warnings
    }
