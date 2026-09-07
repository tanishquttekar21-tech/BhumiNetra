"""
normalization.py - Data cleaning and normalization routines for land records.

Performs:
- Indic/Devanagari numeral to ASCII digit conversion.
- String trimming, noise removal, and capitalization.
- Cadastral / Survey / Khasra / Khata format standardization.
- Area conversion and precision alignment (Hectares <-> Acres).
- Owner share and name normalization.
"""

import re

# Devanagari and Indic digit maps to ASCII digits
INDIC_DIGIT_MAP = {
    '०': '0', '१': '1', '२': '2', '३': '3', '४': '4',
    '५': '5', '६': '6', '७': '7', '८': '8', '९': '9',
    '૦': '0', '૧': '1', '૨': '2', '૩': '3', '૪': '4',
    '૫': '5', '૬': '6', '૭': '7', '૮': '8', '૯': '9',
    '೦': '0', '೧': '1', '೨': '2', '೩': '3', '೪': '4',
    '೫': '5', '೬': '6', '೭': '7', '೮': '8', '೯': '9',
}

HECTARE_TO_ACRE = 2.47105
ACRE_TO_HECTARE = 0.404686


def normalize_indic_numerals(text: str) -> str:
    """Converts Indic/Devanagari/Kannada/Gujarati digits to ASCII digits ('0'-'9')."""
    if not isinstance(text, str):
        return str(text or "")
    
    chars = [INDIC_DIGIT_MAP.get(ch, ch) for ch in text]
    return "".join(chars)


def clean_text(text: str) -> str:
    """Strips leading/trailing whitespace, replaces multiple spaces with single space."""
    if text is None:
        return ""
    text = normalize_indic_numerals(str(text))
    # Remove control characters
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    # Standardize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def normalize_cadastral_no(no_str: str) -> str:
    """
    Standardizes Survey / Khasra number format:
    Converts Indic digits, trims noise, replaces backslashes/dashes with standard slashes where applicable.
    Example: '१४२ / ३A' -> '142/3A'
    """
    text = clean_text(no_str)
    if not text:
        return ""
    # Standardize separator spacing around '/' or '-'
    text = re.sub(r'\s*[\/\\]\s*', '/', text)
    text = re.sub(r'\s*\-\s*', '-', text)
    return text


def normalize_khata_no(khata_str: str) -> str:
    """Standardizes Khata number string."""
    text = clean_text(khata_str)
    # Strip leading zeros for numeric khata unless single '0'
    if text.isdigit() and len(text) > 1:
        text = text.lstrip('0')
    return text


def normalize_area(area_acres: float, area_hectares: float) -> tuple[float, float]:
    """
    Normalizes land area numeric values and calculates missing conversion values.
    Returns (normalized_acres, normalized_hectares).
    """
    try:
        acres = float(area_acres) if area_acres is not None else 0.0
    except (ValueError, TypeError):
        acres = 0.0

    try:
        hectares = float(area_hectares) if area_hectares is not None else 0.0
    except (ValueError, TypeError):
        hectares = 0.0

    acres = max(0.0, acres)
    hectares = max(0.0, hectares)

    if acres == 0.0 and hectares > 0.0:
        acres = round(hectares * HECTARE_TO_ACRE, 2)
    elif hectares == 0.0 and acres > 0.0:
        hectares = round(acres * ACRE_TO_HECTARE, 4)
        acres = round(acres, 2)
    else:
        acres = round(acres, 2)
        hectares = round(hectares, 4)

    return acres, hectares


def normalize_owners(owners_list: list) -> list:
    """
    Standardizes owner dictionaries:
    - Normalizes owner name (trims title noise like Shri/Smt/Shree if appropriate while preserving full name)
    - Coerces share_fraction to float [0.0, 1.0]
    """
    if not isinstance(owners_list, list):
        return []

    cleaned_owners = []
    for o in owners_list:
        if isinstance(o, dict):
            name = clean_text(o.get("name", ""))
            relation = clean_text(o.get("relation", "Owner"))
            try:
                share = float(o.get("share_fraction", 0.0))
            except (ValueError, TypeError):
                share = 0.0
            share = max(0.0, min(1.0, round(share, 4)))
            
            cleaned_owners.append({
                "name": name,
                "relation": relation or "Owner",
                "share_fraction": share,
                "share_percent": o.get("share_percent", f"{share * 100:.0f}%"),
                "area_allocated": clean_text(o.get("area_allocated", ""))
            })
        elif isinstance(o, str) and clean_text(o):
            cleaned_owners.append({
                "name": clean_text(o),
                "relation": "Owner",
                "share_fraction": 1.0 if len(owners_list) == 1 else 0.0,
                "share_percent": "100%" if len(owners_list) == 1 else "0%",
                "area_allocated": ""
            })

    return cleaned_owners


def normalize_land_record(extracted_data: dict) -> dict:
    """
    Applies complete normalization pipeline on an extracted land record dictionary.
    Returns a new normalized dictionary without mutating the original.
    """
    data = dict(extracted_data or {})
    
    survey_no = normalize_cadastral_no(data.get("survey_khasra_no", ""))
    khata_no = normalize_khata_no(data.get("khata_no", ""))
    
    acres, hectares = normalize_area(
        data.get("total_area_acres"),
        data.get("total_area_hectares")
    )
    
    owners = normalize_owners(data.get("owners", []))
    
    encumbrances = [clean_text(e) for e in data.get("encumbrances", []) if clean_text(e)]
    
    return {
        "document_type": clean_text(data.get("document_type", "")),
        "state": clean_text(data.get("state", "")),
        "district": clean_text(data.get("district", "")),
        "taluka": clean_text(data.get("taluka", "")),
        "village": clean_text(data.get("village", "")),
        "survey_khasra_no": survey_no,
        "khata_no": khata_no,
        "owners": owners,
        "total_area_acres": acres,
        "total_area_hectares": hectares,
        "land_classification": clean_text(data.get("land_classification", "")),
        "assessment_tax": clean_text(data.get("assessment_tax", "")),
        "encumbrances": encumbrances,
        "mutation_ref": clean_text(data.get("mutation_ref", "")),
        "digital_sign_hash": clean_text(data.get("digital_sign_hash", "")),
        "extraction_confidence": float(data.get("extraction_confidence", 0.85))
    }
