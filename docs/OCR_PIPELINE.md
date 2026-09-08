# BhumiNetra AI/OCR Pipeline Architecture & Reference

This document provides a detailed overview of the enhanced **AI/OCR Pipeline** for land-record digitization in BhumiNetra (Person 1 - AI/OCR Lead responsibility).

---

## 1. Pipeline Overview

```
Document Upload / Image
         │
         ▼
┌────────────────────────────────────────────────────────┐
│ 1. Image Preprocessing (services/image_processor.py)   │
│    - Grayscale & Illumination Correction               │
│    - Noise Removal (Gaussian / Fast NLM) & CLAHE       │
│    - Adaptive Otsu Thresholding & Margin Cleanup       │
│    - Low-Res Upscaling (INTER_CUBIC)                   │
│    - Skew Angle Detection & Affine Rotation            │
│    - Table Grid & ROI Extraction                       │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ 2. Multilingual OCR Engine (services/ocr_engine.py)   │
│    - Priority Scripts: Devanagari (Marathi/Hindi),    │
│      English, Devanagari/English mixed, Kannada        │
│    - Multi-Tier Architecture:                          │
│        Tier 1: Real Engine (Tesseract / PaddleOCR)     │
│        Tier 2: OpenCV Layout & Region Detection        │
│        Tier 3: Preset Demo Fallback (100% Zero-Crash)  │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ 3. Safe Post-Processing & HTR Detection                │
│    - Unicode Normalization (NFC) for Devanagari        │
│    - Safe Whitespace & Typo Cleanup                    │
│    - Raw Text Preservation (`raw_text` vs `text`)      │
│    - Extensible HTR Stroke Feature Detection           │
│    - Layout Reading Order Sorting (y, x)               │
│    - Downstream Field Evidence Tagging (`field_hint`)  │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
             Existing Extractor (Person 2)
                         │
                         ▼
             Validation Engine (Person 3)
```

---

## 2. Image Preprocessing Pipeline (`services/image_processor.py`)

### Public Function
`process_land_record_image(image_path, options=None)`

### Key Preprocessing Stages
1. **Original Safety**: Reads the image into memory; NEVER overwrites the file on disk.
2. **Illumination Correction**: Uses morphological closing with a 25x25 structuring element to estimate background lighting and normalize uneven scanner shadows.
3. **Denoising & CLAHE**: Removes scan noise while enhancing local contrast via Contrast Limited Adaptive Histogram Equalization (`clipLimit=2.5`, `tileGridSize=(8,8)`).
4. **Adaptive Thresholding & Margin Cleanup**: Binarizes text regions and strips dark scanner border margins.
5. **Low-Resolution Upscaling**: Scales up small scanned documents (< 1200px minimum dimension) using cubic interpolation (`cv2.INTER_CUBIC`).
6. **Deskewing**: Calculates rotation matrix via minimum area bounding rectangle on inverted binary mask; caps skew correction to realistic limits `[-15°, 15°]`.
7. **Grid & ROI Extraction**: Extracts table grid lines via morphological horizontal/vertical kernels and outlines region of interest (ROI) bounding boxes.

### Configuration Parameters (`options` dictionary)
- `clahe_clip` (default `2.5`): Contrast enhancement threshold.
- `upscale` (default `True`): Enable/disable intelligent upscaling for low-res scans.
- `fast_nlm` (default `False`): Toggle Fast Non-Local Means Denoising.
- `margin_px` (default `8`): Pixel width for outer margin border cleanup.

---

## 3. Multilingual OCR Engine (`services/ocr_engine.py`)

### Public Function
`run_multilingual_ocr(doc_type="712_maharashtra", image_meta=None, image_path=None)`

### Output Data Schema
```json
{
  "script": "Devanagari (Marathi) & English",
  "total_blocks": 18,
  "avg_confidence": 0.9611,
  "confidence_percentage": 96.1,
  "has_handwriting": false,
  "detected_languages": ["Devanagari (Marathi/Hindi)", "English"],
  "low_confidence_blocks": [],
  "blocks": [
    {
      "id": "b1",
      "bbox": [150, 45, 600, 35],
      "text": "GOVERNMENT OF MAHARASHTRA",
      "raw_text": "GOVERNMENT OF MAHARASHTRA",
      "lang": "English",
      "script": "Latin",
      "conf": 0.98,
      "is_handwritten": false,
      "field_hint": "header"
    }
  ]
}
```

---

## 4. Unicode & Safe Post-Processing Rules

### Devanagari Preservation
- Uses **NFC Normalization** (`unicodedata.normalize("NFC", text)`).
- Matras, halant conjuncts, and Devanagari numerals (`०-९`) are strictly preserved without lossy transliteration.

### Identifier Protection Rules
- **NEVER** apply regex typo corrections to:
  - Owner names
  - Survey / Khasra numbers (e.g. `142/3A`, `512/1`)
  - Khata numbers (e.g. `8842`, `00319`)
  - Area measurements (e.g. `1.64.00 Hectares`)
  - Mutation entry references (e.g. `12480`)
  - Village, Taluka, and District names
- Original OCR text is ALWAYS preserved in the `raw_text` field.

---

## 5. Downstream Integration Guides

### For Person 2 (Field Extraction Engine)
- Bounding boxes `[x, y, w, h]` are provided for spatial layout analysis.
- Reading order is pre-sorted top-to-bottom, left-to-right.
- `field_hint` metadata tag assists field identification (e.g. `"survey_khasra_no"`, `"khata_no"`, `"owner_name"`, `"area"`, `"mutation_ref"`).

### For Person 3 (Validation Module)
- Block confidence `conf` and overall document `avg_confidence` metrics are provided.
- `low_confidence_blocks` (< 0.85 confidence threshold) are explicitly isolated in the root JSON response to trigger human review rules.
