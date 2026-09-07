"""
sample_dataset.py - Synthetic Land Record Dataset for Validation & Anomaly Testing.

Contains realistic valid, invalid, duplicate, and anomalous land records.
Used for unit testing, offline verification, and Isolation Forest training.
"""

SAMPLE_LAND_RECORDS = [
    # ---------------------------------------------------------
    # 1. VALID RECORDS
    # ---------------------------------------------------------
    {
        "id": "SAMPLE-VAL-001",
        "document_type": "Village Form 7/12 (Satbara Extract)",
        "state": "Maharashtra",
        "district": "Pune",
        "taluka": "Haveli",
        "village": "Wagholi",
        "survey_khasra_no": "142/3A",
        "survey_no": "142/3A",
        "khata_no": "8842",
        "owners": [
            {"name": "Rameshwar Laxman Patil", "relation": "Self", "share_fraction": 0.50, "share_percent": "50%"},
            {"name": "Sunita Rameshwar Patil", "relation": "Co-owner / Spouse", "share_fraction": 0.50, "share_percent": "50%"}
        ],
        "total_area_acres": 4.05,
        "total_area_hectares": 1.64,
        "land_classification": "Jirayat (Dry Agricultural)",
        "assessment_tax": "₹ 29.00",
        "encumbrances": ["Mortgage registered with Bank of Maharashtra"],
        "mutation_ref": "Mutation Entry No: 12480 (14-Nov-2023)",
        "extraction_confidence": 0.96,
        "ocr_confidence": 95.0
    },
    {
        "id": "SAMPLE-VAL-002",
        "document_type": "Khasra / Khatauni Extract",
        "state": "Uttar Pradesh",
        "district": "Varanasi",
        "taluka": "Pindra",
        "village": "Phulpur",
        "survey_khasra_no": "512/1",
        "survey_no": "512/1",
        "khata_no": "00319",
        "owners": [
            {"name": "Shivkumar Nath Tiwari", "relation": "Sole Khatedar", "share_fraction": 1.00, "share_percent": "100%"}
        ],
        "total_area_acres": 1.34,
        "total_area_hectares": 0.542,
        "land_classification": "Irrigated Single Crop",
        "assessment_tax": "₹ 28.00",
        "encumbrances": [],
        "mutation_ref": "Order No: 881/Tehsildar Pindra",
        "extraction_confidence": 0.97,
        "ocr_confidence": 97.0
    },

    # ---------------------------------------------------------
    # 2. INVALID RECORDS
    # ---------------------------------------------------------
    {
        "id": "SAMPLE-INV-001",
        "document_type": "RTC / Pahani",
        "state": "Karnataka",
        "district": "Bengaluru Rural",
        "taluka": "Devanahalli",
        "village": "Vijayapura",
        "survey_khasra_no": "INVALID_SYNTAX_###",
        "survey_no": "INVALID_SYNTAX_###",
        "khata_no": "",
        "owners": [
            {"name": "Venkatachalapathy Gowda", "relation": "Primary Khatadar", "share_fraction": 0.40, "share_percent": "40%"},
            {"name": "Krishnappa Gowda", "relation": "Co-owner", "share_fraction": 0.30, "share_percent": "30%"}
        ],
        "total_area_acres": 2.50,
        "total_area_hectares": 1.01,
        "land_classification": "Agricultural",
        "assessment_tax": "₹ 18.20",
        "encumbrances": ["Active dispute notice filed under Section 136(2)"],
        "mutation_ref": "",
        "extraction_confidence": 0.50,
        "ocr_confidence": 55.0
    },

    # ---------------------------------------------------------
    # 3. DUPLICATE RECORD (Identical to SAMPLE-VAL-001)
    # ---------------------------------------------------------
    {
        "id": "SAMPLE-DUP-001",
        "document_type": "Village Form 7/12 (Satbara Extract)",
        "state": "Maharashtra",
        "district": "Pune",
        "taluka": "Haveli",
        "village": "Wagholi",
        "survey_khasra_no": "142/3A",
        "survey_no": "142/3A",
        "khata_no": "8842",
        "owners": [
            {"name": "Rameshwar Laxman Patil", "relation": "Self", "share_fraction": 0.50, "share_percent": "50%"},
            {"name": "Sunita Rameshwar Patil", "relation": "Co-owner / Spouse", "share_fraction": 0.50, "share_percent": "50%"}
        ],
        "total_area_acres": 4.05,
        "total_area_hectares": 1.64,
        "land_classification": "Jirayat (Dry Agricultural)",
        "assessment_tax": "₹ 29.00",
        "encumbrances": ["Mortgage registered with Bank of Maharashtra"],
        "mutation_ref": "Mutation Entry No: 12480 (14-Nov-2023)",
        "extraction_confidence": 0.95,
        "ocr_confidence": 94.0
    },

    # ---------------------------------------------------------
    # 4. ANOMALOUS RECORD (Extreme parcel size & share error)
    # ---------------------------------------------------------
    {
        "id": "SAMPLE-ANO-001",
        "document_type": "Land Title Deed",
        "state": "Maharashtra",
        "district": "Pune",
        "taluka": "Haveli",
        "village": "Wagholi",
        "survey_khasra_no": "9999/X",
        "survey_no": "9999/X",
        "khata_no": "7712",
        "owners": [],
        "total_area_acres": 450.0,
        "total_area_hectares": 0.50,
        "land_classification": "Unknown",
        "assessment_tax": "0",
        "encumbrances": [
            "Court stay order pending",
            "High Court dispute under Section 136(2)",
            "Bank attachment notice",
            "Tax default lien"
        ],
        "mutation_ref": "MUT-EX-999",
        "extraction_confidence": 0.60,
        "ocr_confidence": 62.0
    }
]


def get_sample_land_records() -> list:
    """Returns synthetic sample land records list."""
    return list(SAMPLE_LAND_RECORDS)
