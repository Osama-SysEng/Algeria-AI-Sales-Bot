from collections import Counter
from time import monotonic
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, Request
from backend.app.core.config import settings
from backend.app.core.policies import can_contact_lead, can_transition
from backend.app.models.domain import ActionApproval, ApprovalState, DraftRequest, LeadCreate, LeadView, StageTransition
from backend.app.services.auth_service import require_operator
from backend.app.services.sales_ai import draft_reply

router = APIRouter(prefix="/api/v1", tags=["sales-workspace"])
LEADS: dict[str, LeadView] = {}
AUDIT: list[dict] = []

# Basic in-memory rate limiter: (client_ip, path) -> list of request timestamps.
# Generous default (120/min) so normal dashboard use and tests never trip it,
# while naive abuse loops get a 429 instead of unbounded memory growth.
_RATE_LIMIT_MAX = 120
_RATE_LIMIT_WINDOW_S = 60.0
_RATE_BUCKETS: dict[tuple[str, str], list[float]] = {}

def _check_rate_limit(request: Request) -> None:
    client = request.client.host if request.client else "unknown"
    key = (client, request.url.path)
    now = monotonic()
    hits = [t for t in _RATE_BUCKETS.get(key, []) if now - t < _RATE_LIMIT_WINDOW_S]
    if len(hits) >= _RATE_LIMIT_MAX:
        raise HTTPException(status_code=429, detail="Rate limit exceeded, retry later")
    hits.append(now)
    # Bound memory: keep only the current window, drop idle buckets.
    if len(hits) >= _RATE_LIMIT_MAX:
        _RATE_BUCKETS[key] = hits[-_RATE_LIMIT_MAX:]
    else:
        _RATE_BUCKETS[key] = hits
    if len(_RATE_BUCKETS) > 5000:
        oldest = min(_RATE_BUCKETS, key=lambda k: _RATE_BUCKETS[k][0] if _RATE_BUCKETS[k] else now)
        del _RATE_BUCKETS[oldest]

@router.get("/health")
def health(): return {"status": "ok", "external_delivery": False}

@router.post("/leads", response_model=LeadView)
def create_lead(payload: LeadCreate, request: Request, _: str = Depends(require_operator)):
    _check_rate_limit(request)
    duplicate = next((item for item in LEADS.values() if item.contact_reference.lower() == payload.contact_reference.lower()), None)
    if duplicate:
        raise HTTPException(status_code=409, detail="Lead with this contact_reference already exists")
    lead = LeadView(id=str(uuid4()), **payload.model_dump())
    LEADS[lead.id] = lead
    AUDIT.append({"event": "lead_created", "lead_id": lead.id})
    return lead

@router.get("/leads", response_model=list[LeadView])
def list_leads(request: Request, _: str = Depends(require_operator)):
    _check_rate_limit(request)
    return list(LEADS.values())

@router.post("/leads/{lead_id}/stage", response_model=LeadView)
def transition_stage(lead_id: str, payload: StageTransition, request: Request, _: str = Depends(require_operator)):
    _check_rate_limit(request)
    lead = LEADS.get(lead_id)
    if not lead: raise HTTPException(status_code=404, detail="Lead not found")
    if not can_transition(lead.stage, payload.target_stage):
        raise HTTPException(status_code=422, detail=f"Transition from {lead.stage.value} to {payload.target_stage.value} is not allowed")
    lead.stage = payload.target_stage
    AUDIT.append({"event": "stage_transition", "lead_id": lead_id, "stage": payload.target_stage.value})
    return lead

@router.post("/drafts")
def create_draft(payload: DraftRequest, request: Request, _: str = Depends(require_operator)):
    _check_rate_limit(request)
    if payload.lead_id not in LEADS: raise HTTPException(status_code=404, detail="Lead not found")
    try:
        draft = draft_reply(payload)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=502, detail="Draft service temporarily unavailable, retry later")
    AUDIT.append({"event": "draft_created", "lead_id": payload.lead_id, "intent": draft.intent})
    return draft

@router.post("/leads/{lead_id}/approve")
def approve_action(lead_id: str, payload: ActionApproval, request: Request, _: str = Depends(require_operator)):
    _check_rate_limit(request)
    lead = LEADS.get(lead_id)
    if not lead: raise HTTPException(status_code=404, detail="Lead not found")
    if not lead.consent_to_contact:
        raise HTTPException(status_code=422, detail="Cannot approve contact without lead consent_to_contact")
    if settings.enable_external_delivery:
        raise HTTPException(status_code=503, detail="External delivery is not implemented in this version")
    lead.approval = ApprovalState.APPROVED
    AUDIT.append({"event": "action_approved", "lead_id": lead_id, "action": payload.action_type, "by": payload.approved_by})
    return {"approved": True, "delivery_performed": False, "reason": "External delivery requires an explicit integration and a second execution gate."}

@router.get("/analytics")
def analytics(request: Request, _: str = Depends(require_operator)):
    _check_rate_limit(request)
    return {"lead_count": len(LEADS), "by_stage": Counter(item.stage.value for item in LEADS.values()), "consented_leads": sum(1 for item in LEADS.values() if item.consent_to_contact), "approved_contactable": sum(1 for item in LEADS.values() if can_contact_lead(item.consent_to_contact, item.approval)), "audit_events": len(AUDIT)}
