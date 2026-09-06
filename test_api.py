import json
import unittest
import os
import sys

# Ensure services directory is accessible
sys.path.append(os.path.dirname(__file__))

from app import app
from services.db_storage import init_db

class BhumiNetraBackendTestCase(unittest.TestCase):

    def setUp(self):
        init_db()
        self.client = app.test_client()
        self.client.testing = True

    def test_01_presets_endpoint(self):
        res = self.client.get('/api/presets')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data["status"], "success")
        self.assertTrue(len(data["presets"]) > 0)

    def test_02_process_high_confidence(self):
        res = self.client.post('/api/process', json={"preset_id": "maharashtra_712"})
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        rec = data["record"]
        self.assertEqual(rec["status"], "AUTO_ACCEPTED")
        self.assertIn("validation", rec)
        self.assertIn("rules_evaluated", rec["validation"])
        self.assertGreater(rec["overall_confidence"], 80.0)

    def test_03_process_low_confidence_pending_review(self):
        res = self.client.post('/api/process', json={"preset_id": "karnataka_rtc"})
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        rec = data["record"]
        self.assertEqual(rec["status"], "PENDING_HUMAN_REVIEW")

        # Verify record appears in pending reviews queue
        pending_res = self.client.get('/api/reviews/pending')
        self.assertEqual(pending_res.status_code, 200)
        pending_data = json.loads(pending_res.data)
        pending_ids = [r["id"] for r in pending_data["records"]]
        self.assertIn(rec["id"], pending_ids)

    def test_04_record_crud_operations(self):
        # 1. CREATE Record (POST /api/records)
        new_payload = {
            "id": "BH-TEST-9999",
            "doc_type": "Title Deed",
            "state": "Maharashtra",
            "district": "Pune",
            "taluka": "Haveli",
            "village": "Wagholi",
            "survey_no": "999/1",
            "khata_no": "1234",
            "status": "PENDING_HUMAN_REVIEW"
        }
        res_create = self.client.post('/api/records', json=new_payload)
        self.assertEqual(res_create.status_code, 201)
        created_rec = json.loads(res_create.data)["record"]
        self.assertEqual(created_rec["id"], "BH-TEST-9999")

        # 2. READ Single Record (GET /api/records/<id>)
        res_get = self.client.get('/api/records/BH-TEST-9999')
        self.assertEqual(res_get.status_code, 200)
        rec = json.loads(res_get.data)["record"]
        self.assertEqual(rec["survey_no"], "999/1")

        # 3. READ All Records (GET /api/records)
        res_all = self.client.get('/api/records')
        self.assertEqual(res_all.status_code, 200)
        records_list = json.loads(res_all.data)["records"]
        self.assertTrue(any(r["id"] == "BH-TEST-9999" for r in records_list))

        # 4. UPDATE Record (PUT /api/records/<id>)
        res_put = self.client.put('/api/records/BH-TEST-9999', json={"survey_no": "999/1-MODIFIED", "village": "New Village"})
        self.assertEqual(res_put.status_code, 200)
        rec_updated = json.loads(res_put.data)["record"]
        self.assertEqual(rec_updated["survey_no"], "999/1-MODIFIED")

        # 5. DELETE Record (DELETE /api/records/<id>)
        res_del = self.client.delete('/api/records/BH-TEST-9999')
        self.assertEqual(res_del.status_code, 200)
        
        # Verify 404 after deletion
        res_get_del = self.client.get('/api/records/BH-TEST-9999')
        self.assertEqual(res_get_del.status_code, 404)

    def test_05_approve_review_and_field_corrections(self):
        # Process a record needing review
        res_proc = self.client.post('/api/process', json={"preset_id": "karnataka_rtc"})
        rec_id = json.loads(res_proc.data)["record"]["id"]

        # Approve record with field correction
        res_approve = self.client.post(f'/api/reviews/{rec_id}/approve', json={
            "comments": "Corrected primary owner name and approved.",
            "reviewer": "Inspector_Sharma",
            "updated_fields": {
                "owners": [{"name": "Venkatachalapathy Gowda Corrected", "share_fraction": 1.0}]
            }
        })
        self.assertEqual(res_approve.status_code, 200)
        approved_rec = json.loads(res_approve.data)["record"]
        self.assertEqual(approved_rec["status"], "MANUALLY_APPROVED")

        # Verify Audit Log
        res_audit = self.client.get(f'/api/records/{rec_id}/audit')
        self.assertEqual(res_audit.status_code, 200)
        audit_data = json.loads(res_audit.data)
        actions = [log["action"] for log in audit_data["audit_logs"]]
        self.assertIn("DOCUMENT_UPLOADED", actions)
        self.assertIn("PROCESSING_COMPLETED", actions)
        self.assertIn("FIELD_CORRECTED", actions)
        self.assertIn("RECORD_APPROVED", actions)

    def test_06_reject_review(self):
        res_proc = self.client.post('/api/process', json={"preset_id": "karnataka_rtc"})
        rec_id = json.loads(res_proc.data)["record"]["id"]

        res_reject = self.client.post(f'/api/reviews/{rec_id}/reject', json={
            "comments": "Invalid seal and unreadable signature",
            "reviewer": "Inspector_Verma"
        })
        self.assertEqual(res_reject.status_code, 200)
        rejected_rec = json.loads(res_reject.data)["record"]
        self.assertEqual(rejected_rec["status"], "REJECTED")

    def test_07_dashboard_stats(self):
        res_stats = self.client.get('/api/dashboard/stats')
        self.assertEqual(res_stats.status_code, 200)
        stats = json.loads(res_stats.data)["stats"]
        self.assertIn("total_records", stats)
        self.assertIn("auto_accepted", stats)
        self.assertIn("pending_review", stats)
        self.assertIn("manually_approved", stats)
        self.assertIn("rejected", stats)
        self.assertIn("high_risk_records", stats)
        self.assertIn("average_confidence", stats)

    def test_08_error_handling(self):
        # 404 for non-existent record
        res = self.client.get('/api/records/BH-NONEXISTENT')
        self.assertEqual(res.status_code, 404)
        
        # 404 for invalid endpoint
        res_404 = self.client.get('/api/invalid_route')
        self.assertEqual(res_404.status_code, 404)
        
        # 400 for bad POST /api/records payload
        res_bad = self.client.post('/api/records', data="Not JSON", content_type="application/json")
        self.assertEqual(res_bad.status_code, 400)

if __name__ == "__main__":
    unittest.main()

