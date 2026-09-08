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
from services.db_storage import (
    init_db, save_record, create_record, get_all_records, get_record_by_id,
    update_record, delete_record_by_id, update_record_status, get_stats,
    get_dashboard_stats, get_pending_reviews, approve_record, reject_record,
    log_audit_event, get_audit_logs
)

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

        # AUDIT: Document Uploaded & Processing Started
        log_audit_event(rec_id, "DOCUMENT_UPLOADED", "System", f"Document type: {doc_type_key}")
        log_audit_event(rec_id, "PROCESSING_STARTED", "BhumiNetra_Pipeline", f"Pipeline execution started for {rec_id}")

        # STEP 1: OpenCV Image Processing
        opencv_res = process_land_record_image(file_path)
        
        # STEP 2: Multilingual OCR Engine
        ocr_res = run_multilingual_ocr(doc_type_key, opencv_res)
        
        # STEP 3: AI Field Extraction
        extracted_fields = extract_fields_from_ocr(ocr_res, doc_type_key)
        
        # AUDIT: Processing Completed
        processing_time_ms = int((time.time() - start_time) * 1000)
        log_audit_event(rec_id, "PROCESSING_COMPLETED", "BhumiNetra_Pipeline", f"Image processing and OCR completed in {processing_time_ms}ms")

        # STEP 4: Validation Engine & ML Audit
        existing_records = get_all_records()
        candidate_fields = dict(extracted_fields)
        candidate_fields["id"] = rec_id
        validation_res = validate_land_record(candidate_fields, ocr_res, existing_records=existing_records)
        
        # AUDIT: Validation Completed
        log_audit_event(rec_id, "VALIDATION_COMPLETED", "Validation_Engine", {
            "validation_score": validation_res["validation_score"],
            "passed_rules": f"{validation_res['passed_count']}/{validation_res['total_count']}",
            "warnings_count": len(validation_res.get("warnings", [])),
            "duplicate_probability": validation_res.get("duplicate_probability", 0.0),
            "anomaly_score": validation_res.get("anomaly_score", 0.0)
        })
        
        # STEP 5: Confidence Score & Branching
        score_pct = validation_res.get("overall_confidence")
        decision_status = validation_res.get("status")
        decision_label = validation_res.get("decision_label")
        
        if score_pct is None or decision_status is None:
            score_pct, decision_status, decision_label = compute_overall_confidence(
                ocr_res["avg_confidence"],
                extracted_fields["extraction_confidence"],
                validation_res["validation_score"]
            )
        
        if decision_status == "PENDING_HUMAN_REVIEW":
            log_audit_event(rec_id, "SENT_TO_REVIEW", "Validation_Engine", f"Confidence score ({score_pct}%) below auto-accept threshold (85.0%)")
        
        # STEP 6: Digital Signature & GIS Parcel Generation
        survey_no = extracted_fields.get("survey_khasra_no", "101/A")
        state = extracted_fields.get("state", "Maharashtra")
        village = extracted_fields.get("village", "Wagholi")
        
        gis_data = generate_gis_parcel_data(survey_no, state, village)
        
        raw_hash_str = f"{rec_id}-{survey_no}-{extracted_fields.get('khata_no')}-{score_pct}"
        digital_hash = f"SHA256:{hashlib.sha256(raw_hash_str.encode('utf-8')).hexdigest()[:24].upper()}"
        
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
        log_audit_event(rec_id, f"RECORD_SAVED", "BhumiNetra_Pipeline", f"Saved with status {decision_status}")
        
        return jsonify({
            "status": "success",
            "record": full_record
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/records', methods=['GET'])
def list_records():
    status = request.args.get('status')
    records = get_all_records(status_filter=status)
    return jsonify({"status": "success", "count": len(records), "records": records})

@app.route('/api/records/<record_id>', methods=['GET'])
def get_record(record_id):
    rec = get_record_by_id(record_id)
    if not rec:
        return jsonify({"status": "error", "message": f"Record with ID '{record_id}' not found"}), 404
    return jsonify({"status": "success", "record": rec})

@app.route('/api/records', methods=['POST'])
def create_record_api():
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"status": "error", "message": "Invalid or missing JSON payload"}), 400
            
        created = create_record(data)
        return jsonify({"status": "success", "record": created}), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/records/<record_id>', methods=['PUT'])
def update_record_api(record_id):
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"status": "error", "message": "Invalid or missing JSON payload"}), 400
            
        updated = update_record(record_id, data)
        if not updated:
            return jsonify({"status": "error", "message": f"Record with ID '{record_id}' not found"}), 404
        return jsonify({"status": "success", "record": updated}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/records/<record_id>', methods=['DELETE'])
def delete_record_api(record_id):
    try:
        success = delete_record_by_id(record_id)
        if not success:
            return jsonify({"status": "error", "message": f"Record with ID '{record_id}' not found"}), 404
        return jsonify({"status": "success", "message": f"Record '{record_id}' successfully deleted"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/dashboard/stats', methods=['GET'])
@app.route('/api/stats', methods=['GET'])
def platform_stats():
    stats = get_dashboard_stats()
    return jsonify({"status": "success", "stats": stats})

@app.route('/api/reviews/pending', methods=['GET'])
def pending_reviews_api():
    records = get_pending_reviews()
    return jsonify({"status": "success", "count": len(records), "records": records})

@app.route('/api/reviews/<record_id>/approve', methods=['POST'])
def approve_review_api(record_id):
    try:
        data = request.get_json(silent=True) or {}
        comments = data.get("comments", "")
        reviewer = data.get("reviewer", "Human_Inspector")
        updated_fields = data.get("updated_fields", {})
        
        success, message = approve_record(record_id, comments=comments, reviewer=reviewer, updated_fields=updated_fields)
        if not success:
            return jsonify({"status": "error", "message": message}), 404
            
        updated_rec = get_record_by_id(record_id)
        return jsonify({
            "status": "success",
            "message": message,
            "record": updated_rec
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/reviews/<record_id>/reject', methods=['POST'])
def reject_review_api(record_id):
    try:
        data = request.get_json(silent=True) or {}
        comments = data.get("comments", "")
        reviewer = data.get("reviewer", "Human_Inspector")
        
        success, message = reject_record(record_id, comments=comments, reviewer=reviewer)
        if not success:
            return jsonify({"status": "error", "message": message}), 404
            
        updated_rec = get_record_by_id(record_id)
        return jsonify({
            "status": "success",
            "message": message,
            "record": updated_rec
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/review', methods=['POST'])
def review_record():
    try:
        data = request.get_json(silent=True) or {}
        rec_id = data.get("record_id")
        action = data.get("action") # MANUALLY_APPROVED, REJECTED, NEEDS_RESCAN
        comments = data.get("comments", "")
        reviewer = data.get("reviewer", "Human_Inspector")
        updated_fields = data.get("updated_fields", {})
        
        if not rec_id or not action:
            return jsonify({"status": "error", "message": "Missing record_id or action"}), 400
            
        if action == "MANUALLY_APPROVED":
            success, msg = approve_record(rec_id, comments=comments, reviewer=reviewer, updated_fields=updated_fields)
        elif action == "REJECTED":
            success, msg = reject_record(rec_id, comments=comments, reviewer=reviewer)
        else:
            success = update_record_status(rec_id, action, comments, updated_fields)
            msg = f"Record updated to {action}"
            
        if success:
            return jsonify({"status": "success", "message": msg})
        else:
            return jsonify({"status": "error", "message": "Failed to update record"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/records/<record_id>/audit', methods=['GET'])
def get_record_audit_api(record_id):
    rec = get_record_by_id(record_id)
    if not rec:
        return jsonify({"status": "error", "message": f"Record with ID '{record_id}' not found"}), 404
        
    logs = get_audit_logs(record_id)
    return jsonify({
        "status": "success",
        "record_id": record_id,
        "count": len(logs),
        "audit_logs": logs
    }), 200

@app.route('/api/records/<record_id>/certificate', methods=['GET'])
@app.route('/api/records/<record_id>/certificate/download', methods=['GET'])
def download_certificate(record_id):
    rec = get_record_by_id(record_id)
    if not rec:
        return jsonify({"status": "error", "message": f"Record with ID '{record_id}' not found"}), 404
        
    logs = get_audit_logs(record_id)
    owners = rec.get("owners", [])
    owners_str = ", ".join([f"{o.get('name')} ({o.get('share_percent', '')})" for o in owners]) if owners else "N/A"
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BhumiNetra Audit Certificate - {rec.get('id')}</title>
    <style>
        body {{ font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 40px 20px; }}
        .cert-card {{ max-width: 820px; margin: 0 auto; background: #1e293b; border: 2px solid #06b6d4; border-radius: 14px; padding: 40px; box-shadow: 0 20px 40px rgba(0,0,0,0.6); }}
        .header {{ text-align: center; border-bottom: 2px solid #334155; padding-bottom: 24px; margin-bottom: 30px; }}
        .header h1 {{ color: #38bdf8; margin: 0; font-size: 24px; text-transform: uppercase; letter-spacing: 1.5px; }}
        .header p {{ color: #94a3b8; font-size: 14px; margin: 6px 0 0 0; }}
        .badge {{ display: inline-block; padding: 6px 14px; border-radius: 6px; font-weight: bold; font-size: 13px; text-transform: uppercase; }}
        .badge-pass {{ background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid #10b981; }}
        .badge-review {{ background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid #f59e0b; }}
        .section-title {{ font-size: 15px; font-weight: bold; color: #38bdf8; border-bottom: 1px solid #334155; padding-bottom: 6px; margin-top: 28px; margin-bottom: 14px; }}
        table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
        th, td {{ padding: 10px 14px; text-align: left; border-bottom: 1px solid #334155; font-size: 13px; }}
        th {{ background: #0f172a; color: #94a3b8; width: 35%; font-weight: 600; }}
        td {{ color: #f8fafc; }}
        .hash-box {{ background: #0f172a; border: 1px dashed #06b6d4; padding: 12px; font-family: monospace; font-size: 12px; color: #38bdf8; word-break: break-all; border-radius: 6px; margin-top: 8px; }}
        .footer {{ margin-top: 40px; text-align: center; border-top: 2px solid #334155; padding-top: 20px; font-size: 12px; color: #64748b; }}
        .print-bar {{ text-align: center; margin-bottom: 24px; }}
        .btn-print {{ background: #06b6d4; color: #0f172a; font-weight: bold; border: none; padding: 12px 28px; border-radius: 8px; cursor: pointer; font-size: 15px; transition: all 0.2s; }}
        .btn-print:hover {{ background: #22d3ee; box-shadow: 0 0 15px rgba(6, 182, 212, 0.4); }}
        @media print {{
            .print-bar {{ display: none; }}
            body {{ background: #fff; color: #000; padding: 0; }}
            .cert-card {{ background: #fff; color: #000; border: 2px solid #000; box-shadow: none; margin: 0; max-width: 100%; padding: 20px; }}
            th {{ background: #f1f5f9; color: #0f172a; border-color: #cbd5e1; }}
            td {{ color: #0f172a; border-color: #cbd5e1; }}
            .header h1 {{ color: #0284c7; }}
            .section-title {{ color: #0284c7; border-color: #cbd5e1; }}
            .hash-box {{ background: #f8fafc; color: #0284c7; border-color: #0284c7; }}
            .badge-pass {{ background: #dcfce7; color: #15803d; border-color: #16a34a; }}
        }}
    </style>
</head>
<body>
    <div class="print-bar">
        <button onclick="window.print()" class="btn-print">🖨️ Print / Save PDF Audit Certificate</button>
    </div>
    <div class="cert-card">
        <div class="header">
            <h1>Official Land Record Audit Certificate</h1>
            <p>BhumiNetra AI Digitization & Governance Validation System</p>
        </div>

        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
            <div>
                <span style="font-size: 12px; color: #94a3b8;">Certificate Reference:</span><br>
                <strong style="font-family: monospace; color: #38bdf8; font-size: 16px;">{rec.get('id')}</strong>
            </div>
            <div>
                <span class="badge {'badge-pass' if rec.get('status') in ['AUTO_ACCEPTED', 'MANUALLY_APPROVED'] else 'badge-review'}">
                    {rec.get('status')}
                </span>
            </div>
        </div>

        <div class="section-title">1. Digitized Land Attributes</div>
        <table>
            <tr><th>Document Type</th><td>{rec.get('doc_type', 'N/A')}</td></tr>
            <tr><th>State & District</th><td>{rec.get('state', 'N/A')} / {rec.get('district', 'N/A')}</td></tr>
            <tr><th>Taluka & Village</th><td>{rec.get('taluka', 'N/A')}, {rec.get('village', 'N/A')}</td></tr>
            <tr><th>Survey / Khasra No.</th><td><strong style="color: #38bdf8;">{rec.get('survey_no', 'N/A')}</strong></td></tr>
            <tr><th>Khata Account No.</th><td><strong style="color: #38bdf8;">{rec.get('khata_no', 'N/A')}</strong></td></tr>
            <tr><th>Recorded Owners</th><td>{owners_str}</td></tr>
            <tr><th>Total Land Area</th><td>{rec.get('total_area_acres', 0.0)} Acres ({rec.get('total_area_hectares', 0.0)} Hectares)</td></tr>
            <tr><th>Land Classification</th><td>{rec.get('land_classification', 'Agricultural')}</td></tr>
            <tr><th>Mutation Reference</th><td>{rec.get('mutation_ref', 'N/A')}</td></tr>
        </table>

        <div class="section-title">2. AI Pipeline & Validation Metrics</div>
        <table>
            <tr><th>OCR Engine Confidence</th><td>{rec.get('ocr_confidence', 0.0)}%</td></tr>
            <tr><th>Validation Score</th><td>{rec.get('validation_score', 0.0)}%</td></tr>
            <tr><th>Overall Governance Score</th><td><strong style="color: #34d399;">{rec.get('overall_confidence', 0.0)}%</strong></td></tr>
        </table>

        <div class="section-title">3. Digital Cryptographic Verification Stamp</div>
        <p style="font-size: 12px; color: #94a3b8; margin-bottom: 6px;">SHA-256 Digital Signature Hash:</p>
        <div class="hash-box">{rec.get('digital_hash', 'N/A')}</div>

        <div class="footer">
            <p>This certificate is digitally generated and validated by the <strong>BhumiNetra Land Record Platform</strong>.</p>
            <p>Generated at: {rec.get('created_at', '')} | Verification Standard: SIH-2026-BHUMINETRA</p>
        </div>
    </div>
</body>
</html>
"""
    return html_content, 200, {'Content-Type': 'text/html; charset=utf-8'}


@app.errorhandler(404)
def handle_404(e):
    return jsonify({"status": "error", "message": "Resource or endpoint not found"}), 404

@app.errorhandler(405)
def handle_405(e):
    return jsonify({"status": "error", "message": "Method not allowed for requested endpoint"}), 405

@app.errorhandler(500)
def handle_500(e):
    return jsonify({"status": "error", "message": "Internal server error occurred"}), 500

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

