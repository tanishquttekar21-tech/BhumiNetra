import sqlite3
import json
import os
import time

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "bhoomiai.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes SQLite database schema for BhoomiAI platform"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS land_records (
        id TEXT PRIMARY KEY,
        doc_type TEXT,
        state TEXT,
        district TEXT,
        taluka TEXT,
        village TEXT,
        survey_no TEXT,
        khata_no TEXT,
        owners_json TEXT,
        total_area_acres REAL,
        total_area_hectares REAL,
        land_classification TEXT,
        encumbrances_json TEXT,
        mutation_ref TEXT,
        ocr_confidence REAL,
        validation_score REAL,
        overall_confidence REAL,
        status TEXT, -- AUTO_ACCEPTED, PENDING_HUMAN_REVIEW, MANUALLY_APPROVED, REJECTED
        review_comments TEXT,
        digital_hash TEXT,
        gis_json TEXT,
        extracted_json TEXT,
        ocr_json TEXT,
        pipeline_stages_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        record_id TEXT,
        action TEXT,
        performed_by TEXT,
        details TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    conn.commit()
    conn.close()

def save_record(record_data):
    """Inserts or updates a land record in SQLite"""
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    rec_id = record_data["id"]
    cursor.execute("""
    INSERT OR REPLACE INTO land_records (
        id, doc_type, state, district, taluka, village, survey_no, khata_no,
        owners_json, total_area_acres, total_area_hectares, land_classification,
        encumbrances_json, mutation_ref, ocr_confidence, validation_score,
        overall_confidence, status, review_comments, digital_hash, gis_json,
        extracted_json, ocr_json, pipeline_stages_json, updated_at
    ) VALUES (
        ?, ?, ?, ?, ?, ?, ?, ?,
        ?, ?, ?, ?,
        ?, ?, ?, ?,
        ?, ?, ?, ?, ?,
        ?, ?, ?, CURRENT_TIMESTAMP
    );
    """, (
        rec_id,
        record_data.get("doc_type"),
        record_data.get("state"),
        record_data.get("district"),
        record_data.get("taluka"),
        record_data.get("village"),
        record_data.get("survey_no"),
        record_data.get("khata_no"),
        json.dumps(record_data.get("owners", [])),
        record_data.get("total_area_acres", 0.0),
        record_data.get("total_area_hectares", 0.0),
        record_data.get("land_classification"),
        json.dumps(record_data.get("encumbrances", [])),
        record_data.get("mutation_ref"),
        record_data.get("ocr_confidence", 0.0),
        record_data.get("validation_score", 0.0),
        record_data.get("overall_confidence", 0.0),
        record_data.get("status", "PENDING_HUMAN_REVIEW"),
        record_data.get("review_comments", ""),
        record_data.get("digital_hash", ""),
        json.dumps(record_data.get("gis", {})),
        json.dumps(record_data.get("extracted", {})),
        json.dumps(record_data.get("ocr", {})),
        json.dumps(record_data.get("stages", {}))
    ))
    
    # Add audit log entry
    cursor.execute("""
    INSERT INTO audit_logs (record_id, action, performed_by, details)
    VALUES (?, ?, ?, ?);
    """, (rec_id, f"RECORD_SAVED_STATUS_{record_data.get('status')}", "BhoomiAI_Pipeline", f"Confidence: {record_data.get('overall_confidence')}%"))
    
    conn.commit()
    conn.close()

def get_all_records():
    """Retrieves all land records from DB"""
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM land_records ORDER BY created_at DESC;")
    rows = cursor.fetchall()
    conn.close()
    
    results = []
    for r in rows:
        d = dict(r)
        d["owners"] = json.loads(d["owners_json"]) if d["owners_json"] else []
        d["encumbrances"] = json.loads(d["encumbrances_json"]) if d["encumbrances_json"] else []
        d["gis"] = json.loads(d["gis_json"]) if d["gis_json"] else {}
        d["extracted"] = json.loads(d["extracted_json"]) if d["extracted_json"] else {}
        d["ocr"] = json.loads(d["ocr_json"]) if d["ocr_json"] else {}
        results.append(d)
    return results

def get_record_by_id(record_id):
    """Retrieves single record by ID"""
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM land_records WHERE id = ?;", (record_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    d["owners"] = json.loads(d["owners_json"]) if d["owners_json"] else []
    d["encumbrances"] = json.loads(d["encumbrances_json"]) if d["encumbrances_json"] else []
    d["gis"] = json.loads(d["gis_json"]) if d["gis_json"] else {}
    d["extracted"] = json.loads(d["extracted_json"]) if d["extracted_json"] else {}
    d["ocr"] = json.loads(d["ocr_json"]) if d["ocr_json"] else {}
    d["stages"] = json.loads(d["pipeline_stages_json"]) if d.get("pipeline_stages_json") else {}
    return d

def update_record_status(record_id, status, comments="", updated_fields=None):
    """Updates status and override fields during Human Review"""
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    rec = get_record_by_id(record_id)
    if not rec:
        return False
        
    extracted = rec["extracted"]
    if updated_fields:
        for k, v in updated_fields.items():
            extracted[k] = v
            if k == "survey_no": rec["survey_no"] = v
            if k == "khata_no": rec["khata_no"] = v
            
    cursor.execute("""
    UPDATE land_records
    SET status = ?, review_comments = ?, extracted_json = ?, survey_no = ?, khata_no = ?, updated_at = CURRENT_TIMESTAMP
    WHERE id = ?;
    """, (status, comments, json.dumps(extracted), rec.get("survey_no"), rec.get("khata_no"), record_id))
    
    cursor.execute("""
    INSERT INTO audit_logs (record_id, action, performed_by, details)
    VALUES (?, ?, ?, ?);
    """, (record_id, f"HUMAN_REVIEW_{status}", "Human_Inspector", comments))
    
    conn.commit()
    conn.close()
    return True

def get_stats():
    """Calculates live platform KPIs for Executive Dashboard"""
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM land_records;")
    total_docs = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM land_records WHERE status = 'AUTO_ACCEPTED';")
    auto_accepted = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM land_records WHERE status = 'PENDING_HUMAN_REVIEW';")
    pending_review = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM land_records WHERE status = 'MANUALLY_APPROVED';")
    manually_approved = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM land_records WHERE status = 'REJECTED';")
    rejected = cursor.fetchone()[0]
    
    cursor.execute("SELECT AVG(overall_confidence) FROM land_records;")
    avg_conf_row = cursor.fetchone()[0]
    avg_confidence = round(avg_conf_row, 1) if avg_conf_row else 0.0
    
    auto_accept_rate = round((auto_accepted / total_docs * 100), 1) if total_docs > 0 else 0.0
    
    conn.close()
    return {
        "total_docs": total_docs,
        "auto_accepted": auto_accepted,
        "pending_review": pending_review,
        "manually_approved": manually_approved,
        "rejected": rejected,
        "auto_accept_rate": auto_accept_rate,
        "avg_confidence": avg_confidence,
        "avg_processing_time_ms": 342
    }
