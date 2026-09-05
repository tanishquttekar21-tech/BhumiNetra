import os
import sys
import uuid
import json
import time
import hashlib
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

# Add services path
sys.path.append(os.path.dirname(__file__))

from services.image_processor import process_land_record_image
from services.ocr_engine import run_multilingual_ocr
from services.extractor import extract_fields_from_ocr
from services.validator import validate_land_record
from services.gis_engine import generate_gis_parcel_data
from services.db_storage import init_db, save_record, get_all_records, get_record_by_id, update_record_status, get_stats

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), "uploads")
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # 16 MB max limit
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize Database
init_db()

SAMPLE_DOCS_DIR = os.path.join(os.path.dirname(__file__), "sample_docs")

# Preset file map
PRESETS = {
    "maharashtra_712": {
        "doc_type": "712_maharashtra",
        "file": os.path.join(SAMPLE_DOCS_DIR, "maharashtra_712_clean.png"),
        "title": "Form 7/12 Satbara Extract (Maharashtra)",
        "subtitle": "Clean Record (High Confidence - Auto Accept Flow)"
    },
    "karnataka_rtc": {
        "doc_type": "rtc_karnataka",
        "file": os.path.join(SAMPLE_DOCS_DIR, "karnataka_rtc_low_conf.png"),
        "title": "RTC / Pahani (Karnataka)",
        "subtitle": "Noisy Scan & Share Discrepancy (Low Confidence - Human Review Flow)"
    },
    "up_khasra": {
        "doc_type": "up_khasra",
        "file": os.path.join(SAMPLE_DOCS_DIR, "up_khasra_clean.png"),
        "title": "Khasra-Khatauni (Uttar Pradesh)",
        "subtitle": "Devanagari Hindi Record (High Confidence Flow)"
    }
}

def compute_overall_confidence(ocr_conf, field_conf, val_score):
    """
    Confidence Formula:
    Weighted average = (OCR Confidence * 40%) + (Field Extraction * 30%) + (Validation Rule Score * 30%)
    """
    weighted = (ocr_conf * 0.40) + (field_conf * 0.30) + (val_score * 0.30)
    score_pct = round(weighted * 100, 1)
    
    if score_pct >= 85.0:
        decision = "AUTO_ACCEPTED"
        decision_label = "HIGH CONFIDENCE (Auto Accepted)"
    else:
        decision = "PENDING_HUMAN_REVIEW"
        decision_label = "LOW CONFIDENCE (Human Review Required)"
        
    return score_pct, decision, decision_label

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/presets')
def get_presets():
    return jsonify({
        "status": "success",
        "presets": [
            {"id": k, "title": v["title"], "subtitle": v["subtitle"]} for k, v in PRESETS.items()
        ]
    })

@app.route('/api/process', methods=['POST'])
def process_record():
    try:
        start_time = time.time()
        req_data = request.get_json(silent=True) or {}
        preset_id = req_data.get("preset_id")
        
        # Check if file upload or preset
        if preset_id and preset_id in PRESETS:
            preset = PRESETS[preset_id]
            file_path = preset["file"]
            doc_type_key = preset["doc_type"]
            rec_id = f"BH-{preset_id.upper()}-{uuid.uuid4().hex[:6]}"
        elif 'file' in request.files:
            file = request.files['file']
            if file.filename == '':
                return jsonify({"status": "error", "message": "No file selected"}), 400
            filename = secure_filename(file.filename)
            rec_id = f"BH-UPLOAD-{uuid.uuid4().hex[:6]}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{rec_id}_{filename}")
            file.save(file_path)
            doc_type_key = "custom_upload"
        else:
            # Default fallback to maharashtra_712 if not specified
            preset = PRESETS["maharashtra_712"]
            file_path = preset["file"]
            doc_type_key = preset["doc_type"]
            rec_id = f"BH-MAHA712-{uuid.uuid4().hex[:6]}"

        # STEP 1: OpenCV Image Processing
        opencv_res = process_land_record_image(file_path)
        
        # STEP 2: Multilingual OCR Engine
        ocr_res = run_multilingual_ocr(doc_type_key, opencv_res)
        
        # STEP 3: AI Field Extraction
        extracted_fields = extract_fields_from_ocr(ocr_res, doc_type_key)
        
        # STEP 4: Validation Engine
        validation_res = validate_land_record(extracted_fields, ocr_res)
        
        # STEP 5: Confidence Score & Branching
        score_pct, decision_status, decision_label = compute_overall_confidence(
            ocr_res["avg_confidence"],
            extracted_fields["extraction_confidence"],
            validation_res["validation_score"]
        )
        
        # STEP 6: Digital Signature & GIS Parcel Generation
        survey_no = extracted_fields.get("survey_khasra_no", "101/A")
        state = extracted_fields.get("state", "Maharashtra")
        village = extracted_fields.get("village", "Wagholi")
        
        gis_data = generate_gis_parcel_data(survey_no, state, village)
        
        raw_hash_str = f"{rec_id}-{survey_no}-{extracted_fields.get('khata_no')}-{score_pct}"
        digital_hash = f"SHA256:{hashlib.sha256(raw_hash_str.encode('utf-8')).hexdigest()[:24].upper()}"
        
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        full_record = {
            "id": rec_id,
            "doc_type": extracted_fields.get("document_type"),
            "state": state,
            "district": extracted_fields.get("district"),
            "taluka": extracted_fields.get("taluka"),
            "village": village,
            "survey_no": survey_no,
            "khata_no": extracted_fields.get("khata_no"),
            "owners": extracted_fields.get("owners", []),
            "total_area_acres": extracted_fields.get("total_area_acres", 0.0),
            "total_area_hectares": extracted_fields.get("total_area_hectares", 0.0),
            "land_classification": extracted_fields.get("land_classification"),
            "encumbrances": extracted_fields.get("encumbrances", []),
            "mutation_ref": extracted_fields.get("mutation_ref"),
            "ocr_confidence": ocr_res["confidence_percentage"],
            "validation_score": round(validation_res["validation_score"] * 100, 1),
            "overall_confidence": score_pct,
            "status": decision_status,
            "decision_label": decision_label,
            "digital_hash": digital_hash,
            "gis": gis_data,
            "extracted": extracted_fields,
            "ocr": ocr_res,
            "validation": validation_res,
            "stages": opencv_res["stages"],
            "opencv_meta": {
                "width": opencv_res["width"],
                "height": opencv_res["height"],
                "skew_angle": opencv_res["skew_angle"],
                "roi_count": opencv_res["roi_count"]
            },
            "processing_time_ms": processing_time_ms
        }
        
        # Save to SQLite Persistent Store
        save_record(full_record)
        
        return jsonify({
            "status": "success",
            "record": full_record
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/records', methods=['GET'])
def list_records():
    records = get_all_records()
    return jsonify({"status": "success", "count": len(records), "records": records})

@app.route('/api/records/<record_id>', methods=['GET'])
def get_record(record_id):
    rec = get_record_by_id(record_id)
    if not rec:
        return jsonify({"status": "error", "message": "Record not found"}), 404
    return jsonify({"status": "success", "record": rec})

@app.route('/api/review', methods=['POST'])
def review_record():
    try:
        data = request.json or {}
        rec_id = data.get("record_id")
        action = data.get("action") # MANUALLY_APPROVED, REJECTED, NEEDS_RESCAN
        comments = data.get("comments", "")
        updated_fields = data.get("updated_fields", {})
        
        if not rec_id or not action:
            return jsonify({"status": "error", "message": "Missing record_id or action"}), 400
            
        success = update_record_status(rec_id, action, comments, updated_fields)
        if success:
            return jsonify({"status": "success", "message": f"Record updated to {action}"})
        else:
            return jsonify({"status": "error", "message": "Failed to update record"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def platform_stats():
    stats = get_stats()
    return jsonify({"status": "success", "stats": stats})

if __name__ == '__main__':
    # Ensure sample docs exist
    if not os.path.exists(SAMPLE_DOCS_DIR) or len(os.listdir(SAMPLE_DOCS_DIR)) == 0:
        import sample_generator
        sample_generator.create_sample_712_maharashtra()
        sample_generator.create_sample_rtc_karnataka()
        sample_generator.create_sample_khasra_up()
        
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting BhumiNetra Platform Server on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=False)

