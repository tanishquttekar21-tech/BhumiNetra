"""
Gemini Client Module for Land Record Extraction
Extracts structured land record fields from raw OCR text using Google Generative AI (Gemini).
"""

import json
import os
import re
from dotenv import load_dotenv
import google.generativeai as genai
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

# Load environment variables from local .env if present
load_dotenv()

SYSTEM_PROMPT = """You are an expert AI parser specializing in Indian land records and cadastral documents (Bhulekh, Satbara 7/12, Pahani / RTC, Khasra / Khatauni, Title Deeds).

You will receive raw OCR text extracted from physical land records. The text may be noisy, fragmented, out of order, and contain multilingual revenue terminology in English, Devanagari (Marathi/Hindi), and Kannada (e.g., khasra, khata, khatauni, taluka, tehsil, hobli, gunta, bigha, biswa, pahani, jameenbadi, firka, etc.).

Your task is to extract the land record details and return ONLY a valid JSON object matching the EXACT schema provided below.

### Target JSON Schema:
{
  "document_type": string,        // e.g. "Village Form 7/12 (Satbara Extract)", "Record of Rights, Tenancy & Crops (RTC / Pahani)", "Khasra / Khatauni Extract", or title
  "state": string,                // State name (e.g. "Maharashtra", "Karnataka", "Uttar Pradesh")
  "district": string,             // District name
  "taluka": string,               // Taluka / Tehsil / Sub-district
  "village": string,              // Village / Mouza name
  "survey_khasra_no": string,     // Survey / Gut / Khasra number (e.g. "142/3A", "89/1B", "512/1")
  "khata_no": string,             // Khata / Khatauni account number (e.g. "8842", "4021", "00319")
  "owners": [
    {
      "name": string,             // Full name of the owner/khatedar
      "relation": string,         // Relationship or designation (e.g. "Self", "Co-owner", "Spouse", "s/o Ramswaroop", "Primary Khatadar")
      "share_fraction": float,    // Numeric share fraction (e.g. 0.50 for 50%, 1.00 for 100%, 0.40 for 40%)
      "share_percent": string,    // Human-readable percentage string (e.g. "50%", "100%", "40%")
      "area_allocated": string    // Allocated area string (e.g. "0.82.00 Hectares (2.02 Acres)", "1 Acre 20 Gunta")
    }
  ],
  "total_area_hectares": float,   // Total parcel area in hectares (float, 0.0 if not specified or unknown)
  "total_area_acres": float,      // Total parcel area in acres (float, 0.0 if not specified or unknown)
  "land_classification": string,  // Land / soil category (e.g. "Jirayat (Dry Agricultural)", "Red Soil Agricultural (Kari)", "Irrigated Single Crop")
  "assessment_tax": string,       // Assessment or land revenue tax amount (e.g. "₹ 29.00", or "" if none)
  "encumbrances": [string],       // Active bank loans, mortgages, dispute notices, legal stays, or liens. Empty list [] if clean record or none found
  "mutation_ref": string,         // Mutation entry number or revenue order reference (e.g. "Mutation Entry No: 12480 (14-Nov-2023)")
  "digital_sign_hash": string,    // Digital signature reference or placeholder formatted as f"{state[:2].upper()}-{khata_no}-SIG"
  "extraction_confidence": float  // Self-assessed extraction confidence between 0.0 and 1.0 based on OCR legibility and completeness
}

### Parsing Instructions:
1. STRICT JSON FORMAT: Output ONLY valid JSON matching the schema above. Do NOT output markdown fences (```json ... ```), headers, notes, or preamble.
2. MISSING DATA HANDLING: If any field cannot be determined or is absent from the text, use a sensible empty value ("" for strings, [] for lists, 0.0 for numbers). Do NOT invent, hallucinate, or extrapolate unmentioned facts. Lower extraction_confidence if key fields are missing or scan noise is severe.
3. CO-OWNER SHARE INTEGRITY:
   - When co-owners are listed, their share_fraction values should normally sum to ~1.0 (100%).
   - CRITICAL: If the source OCR text itself explicitly states an incomplete share allocation or math discrepancy (e.g., co-owners have 40% + 30% = 70% total), PRESERVE THE STATED VALUES FAITHFULLY. Never artificially adjust or "fix" the source data.
4. DIGITAL SIGNATURE HASH: If an explicit digital signature hash is extracted, use it. Otherwise, use the standard convention: f"{state[:2].upper()}-{khata_no}-SIG" (e.g. "MH-8842-SIG", "KA-4021-SIG", "UP-00319-SIG").
"""

FEW_SHOT_EXAMPLES = """
### Example 1 (Maharashtra 7/12 Satbara Extract):
[RAW OCR TEXT]
GOVERNMENT OF MAHARASHTRA
VILLAGE FORM NO. 7/12 ( अधिकार अभिलेख पत्रक )
District (जिल्हा): Pune
Taluka (तालुका): Haveli
Village (गावाचे नाव): Wagholi
Survey / Khasra No (सर्व्हे / गट क्र.): 142/3A
Khata No (खाता क्रमांक): 8842
1. Rameshwar Laxman Patil 0.50 (50%) 0.82.00 Hectares (2.02 Acres)
2. Sunita Rameshwar Patil 0.50 (50%) 0.82.00 Hectares (2.02 Acres)
TOTAL AREA (एकूण क्षेत्रफळ): 1.64.00 Hectares (4.05 Acres)
Land Use: Jirayat (Dry Agricultural)
Bank Charge: Mortgage registered with Bank of Maharashtra, Wagholi Branch
Loan Reference: BOM/AGRI/2023/9912 | Amount: ₹ 4,50,000
Mutation Entry No (फेरफार क्र.): 12480 (Date: 14-Nov-2023)

[OUTPUT JSON]
{
  "document_type": "Village Form 7/12 (Satbara Extract)",
  "state": "Maharashtra",
  "district": "Pune",
  "taluka": "Haveli",
  "village": "Wagholi",
  "survey_khasra_no": "142/3A",
  "khata_no": "8842",
  "owners": [
    {
      "name": "Rameshwar Laxman Patil",
      "relation": "Self",
      "share_fraction": 0.50,
      "share_percent": "50%",
      "area_allocated": "0.82.00 Hectares (2.02 Acres)"
    },
    {
      "name": "Sunita Rameshwar Patil",
      "relation": "Co-owner / Spouse",
      "share_fraction": 0.50,
      "share_percent": "50%",
      "area_allocated": "0.82.00 Hectares (2.02 Acres)"
    }
  ],
  "total_area_hectares": 1.64,
  "total_area_acres": 4.05,
  "land_classification": "Jirayat (Dry Agricultural)",
  "assessment_tax": "₹ 29.00",
  "encumbrances": [
    "Mortgage registered with Bank of Maharashtra, Wagholi Branch (Ref: BOM/AGRI/2023/9912 | Amount: ₹ 4,50,000)"
  ],
  "mutation_ref": "Mutation Entry No: 12480 (14-Nov-2023)",
  "digital_sign_hash": "MH-8842-SIG",
  "extraction_confidence": 0.96
}

### Example 2 (Karnataka RTC / Pahani with Share Discrepancy & Dispute):
[RAW OCR TEXT]
GOVERNMENT OF KARNATAKA - REVENUE DEPARTMENT
RECORD OF RIGHTS, TENANCY AND CROPS (RTC / Pahani)
District (ಜಿಲ್ಲೆ): Bengaluru Rural
Taluk (ತಾಲೂಕು): Devanahalli
Hobli/Village: Vijayapura
Survey No (ಸರ್ವೇ ನಂಬರ್): 89/1B
Khata No: 4021
1. Venkatachalapathy Gowda 1 Acre 20 Gunta 0.40 (40%)
2. Krishnappa Gowda (Co-owner) 1 Acre 00 Gunta 0.30 (30%)
TOTAL EXTENT: 2 Acres 20 Gunta (Discrepancy in recorded shares: Sum = 70%)
MR No: MR-109/2022-23 (Inheritance Partition)
Encumbrance Flag: Active dispute notice filed under Section 136(2) of KLR Act

[OUTPUT JSON]
{
  "document_type": "Record of Rights, Tenancy & Crops (RTC / Pahani)",
  "state": "Karnataka",
  "district": "Bengaluru Rural",
  "taluka": "Devanahalli",
  "village": "Vijayapura",
  "survey_khasra_no": "89/1B",
  "khata_no": "4021",
  "owners": [
    {
      "name": "Venkatachalapathy Gowda",
      "relation": "Primary Khatadar",
      "share_fraction": 0.40,
      "share_percent": "40%",
      "area_allocated": "1 Acre 20 Gunta"
    },
    {
      "name": "Krishnappa Gowda",
      "relation": "Co-owner",
      "share_fraction": 0.30,
      "share_percent": "30%",
      "area_allocated": "1 Acre 00 Gunta"
    }
  ],
  "total_area_hectares": 1.01,
  "total_area_acres": 2.50,
  "land_classification": "Red Soil Agricultural (Kari)",
  "assessment_tax": "₹ 18.20",
  "encumbrances": [
    "Active dispute notice filed under Section 136(2) of KLR Act (MR-109/2022-23)"
  ],
  "mutation_ref": "MR-109/2022-23 (Inheritance Partition)",
  "digital_sign_hash": "KA-4021-SIG",
  "extraction_confidence": 0.77
}
"""


def extract_land_record_fields(raw_text: str, doc_type_hint: str = "") -> dict:
    """
    Calls the Gemini API to parse raw OCR text into structured land record fields.

    Args:
        raw_text: Concatenated multiline text from OCR blocks.
        doc_type_hint: Context hint for the document type (e.g. "712_maharashtra").

    Returns:
        dict conforming to the land record output schema.

    Raises:
        RuntimeError: If the API key is missing, network communication fails,
                      or the response cannot be parsed into valid JSON.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY environment variable is not configured or empty.")

    genai.configure(api_key=api_key)
    model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    model_name = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

    user_prompt = f"""Context Document Type Hint: {doc_type_hint or 'Standard Indian Land Record'}

Input Raw OCR Text:
\"\"\"
{raw_text}
\"\"\"

Extract the structured land record fields matching the specified schema. Output ONLY valid JSON:"""

    try:
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=SYSTEM_PROMPT + "\n\n" + FEW_SHOT_EXAMPLES,
            generation_config={
                "response_mime_type": "application/json",
                "temperature": 0.1,
            }
        )
        response = model.generate_content(user_prompt)

        if not response or not response.text:
            raise ValueError("Gemini API returned an empty response.")

        response_text = response.text.strip()
        # Clean markdown code fences if inadvertently included
        if response_text.startswith("```"):
            response_text = re.sub(r"^```(?:json)?\s*", "", response_text)
            response_text = re.sub(r"\s*```$", "", response_text)

        parsed_data = json.loads(response_text)
        if not isinstance(parsed_data, dict):
            raise ValueError(f"Expected JSON dictionary from Gemini, got {type(parsed_data).__name__}")

        return parsed_data

    except Exception as exc:
        raise RuntimeError(f"Gemini API extraction failed: {str(exc)}") from exc

