from collections import Counter
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from backend.app.core.policies import can_contact_lead
from backend.app.models.domain import ActionApproval, ApprovalState, DraftRequest, LeadCreate, LeadView
from backend.app.services.auth_service import require_operator
from backend.app.services.sales_ai import draft_reply

router = APIRouter(prefix="/api/v1", tags=["sales-workspace"])
LEADS: dict[str, LeadView] = {}
AUDIT: list[dict] = []

@router.get("/health")
def health(): return {"status": "ok", "external_delivery": False}

@router.post("/leads", response_model=LeadView)
def create_lead(payload: LeadCreate, _: str = Depends(require_operator)):
    lead = LeadView(id=str(uuid4()), **payload.model_dump())
    LEADS[lead.id] = lead
    AUDIT.append({"event": "lead_created", "lead_id": lead.id})
    return lead

@router.get("/leads", response_model=list[LeadView])
def list_leads(_: str = Depends(require_operator)): return list(LEADS.values())

@router.post("/drafts")
def create_draft(payload: DraftRequest, _: str = Depends(require_operator)):
    if payload.lead_id not in LEADS: raise HTTPException(status_code=404, detail="Lead not found")
    draft = draft_reply(payload)
    AUDIT.append({"event": "draft_created", "lead_id": payload.lead_id, "intent": draft.intent})
    return draft

@router.post("/leads/{lead_id}/approve")
def approve_action(lead_id: str, payload: ActionApproval, _: str = Depends(require_operator)):
    lead = LEADS.get(lead_id)
    if not lead: raise HTTPException(status_code=404, detail="Lead not found")
    lead.approval = ApprovalState.APPROVED
    AUDIT.append({"event": "action_approved", "lead_id": lead_id, "action": payload.action_type, "by": payload.approved_by})
    return {"approved": True, "delivery_performed": False, "reason": "External delivery requires an explicit integration and a second execution gate."}

@router.get("/analytics")
def analytics(_: str = Depends(require_operator)):
    return {"lead_count": len(LEADS), "by_stage": Counter(item.stage.value for item in LEADS.values()), "consented_leads": sum(1 for item in LEADS.values() if item.consent_to_contact), "approved_contactable": sum(1 for item in LEADS.values() if can_contact_lead(item.consent_to_contact, item.approval)), "audit_events": len(AUDIT)}
