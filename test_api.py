import urllib.request
import json

def check(url, method='GET', data=None):
    req = urllib.request.Request(url, headers={'Content-Type': 'application/json'}, method=method)
    payload = json.dumps(data).encode('utf-8') if data else None
    res = urllib.request.urlopen(req, data=payload)
    val = json.loads(res.read().decode('utf-8'))
    print(f"[{method}] {url} -> HTTP {res.status} OK | Keys: {list(val.keys())}")
    return val

print("=== VERIFYING BHUMINETRA REST APIS ===")

# 1. Presets Endpoint
check("http://127.0.0.1:5000/api/presets")

# 2. High Confidence Maharashtra 7/12 Preset Process
r1 = check("http://127.0.0.1:5000/api/process", "POST", {"preset_id": "maharashtra_712"})
rec1 = r1["record"]
print(f"   -> Record ID: {rec1['id']}")
print(f"   -> Status: {rec1['status']} ({rec1['decision_label']})")
print(f"   -> Overall Confidence: {rec1['overall_confidence']}%")
print(f"   -> Survey No: {rec1['survey_no']}, Khata No: {rec1['khata_no']}")
print(f"   -> OpenCV Stages: {list(rec1['stages'].keys())}")
print(f"   -> OCR script: {rec1['ocr']['script']} ({rec1['ocr']['confidence_percentage']}%)")
print(f"   -> Validation Passed: {rec1['validation']['passed_count']}/{rec1['validation']['total_count']} Rules")

print("\n--- Testing Low-Confidence Karnataka RTC Preset ---")
# 3. Low Confidence Karnataka RTC Preset Process (Triggers HITL Flow)
r2 = check("http://127.0.0.1:5000/api/process", "POST", {"preset_id": "karnataka_rtc"})
rec2 = r2["record"]
print(f"   -> Record ID: {rec2['id']}")
print(f"   -> Status: {rec2['status']} ({rec2['decision_label']})")
print(f"   -> Overall Confidence: {rec2['overall_confidence']}%")
print(f"   -> Anomaly Warnings: {rec2['validation']['warnings']}")

print("\n--- Testing Human-in-the-Loop Review Override ---")
# 4. Human Review Override Action
r3 = check("http://127.0.0.1:5000/api/review", "POST", {
    "record_id": rec2['id'],
    "action": "MANUALLY_APPROVED",
    "comments": "Verified owner share fraction & approved by Inspector.",
    "updated_fields": {"survey_no": "89/1B-REV"}
})
print(f"   -> Review Result: {r3['message']}")

print("\n--- Testing Database & Stats Endpoints ---")
stats = check("http://127.0.0.1:5000/api/stats")
print(f"   -> KPI Stats: Total={stats['stats']['total_docs']}, AutoAcceptRate={stats['stats']['auto_accept_rate']}%, PendingQueue={stats['stats']['pending_review']}")

records = check("http://127.0.0.1:5000/api/records")
print(f"   -> DB Record Count: {records['count']}")

print("\nALL BACKEND APIS & PIPELINE STEPS VERIFIED SUCCESSFULLY!")
