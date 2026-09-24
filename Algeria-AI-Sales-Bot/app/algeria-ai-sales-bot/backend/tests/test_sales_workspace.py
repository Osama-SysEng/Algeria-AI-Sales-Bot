from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def headers(): return {"X-Operator-Token": ""}

def test_create_lead_and_draft_without_external_delivery():
    lead = client.post("/api/v1/leads", headers=headers(), json={"display_name": "عميل اختبار", "contact_reference": "contact-001", "source": "manual", "consent_to_contact": True})
    assert lead.status_code == 200
    payload = lead.json()
    draft = client.post("/api/v1/drafts", headers=headers(), json={"lead_id": payload["id"], "customer_message": "حاب نعرف السعر", "catalog_context": "لا يوجد سعر مؤكد"})
    assert draft.status_code == 200
    assert draft.json()["requires_human_approval"] is True
    assert "مسودة" in draft.json()["reply_darija"]

def test_approval_records_audit_but_does_not_send():
    lead = client.post("/api/v1/leads", headers=headers(), json={"display_name": "عميل موافق", "contact_reference": "contact-002", "consent_to_contact": True}).json()
    approved = client.post(f"/api/v1/leads/{lead['id']}/approve", headers=headers(), json={"action_type": "send_message", "approved_by": "sales-manager"})
    assert approved.status_code == 200
    assert approved.json()["delivery_performed"] is False

def test_analytics_does_not_expose_message_content():
    analytics = client.get("/api/v1/analytics", headers=headers())
    assert analytics.status_code == 200
    assert "lead_count" in analytics.json()
    assert "customer_message" not in analytics.json()
