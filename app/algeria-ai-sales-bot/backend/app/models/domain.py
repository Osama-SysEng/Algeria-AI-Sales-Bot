from enum import Enum
from pydantic import BaseModel, Field

class LeadStage(str, Enum):
    NEW = "new"
    QUALIFIED = "qualified"
    HUMAN_REVIEW = "human_review"
    WON = "won"
    LOST = "lost"

class ApprovalState(str, Enum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class LeadCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=120)
    contact_reference: str = Field(min_length=3, max_length=160)
    source: str = Field(default="manual", max_length=64)
    consent_to_contact: bool = False

class LeadView(LeadCreate):
    id: str
    stage: LeadStage = LeadStage.NEW
    approval: ApprovalState = ApprovalState.NOT_REQUIRED

class DraftRequest(BaseModel):
    lead_id: str
    customer_message: str = Field(min_length=1, max_length=8000)
    catalog_context: str = Field(default="", max_length=8000)

class ReplyDraft(BaseModel):
    lead_id: str
    intent: str
    reply_darija: str
    facts_used: list[str]
    confidence: str
    requires_human_approval: bool = True

class ActionApproval(BaseModel):
    action_type: str = Field(pattern="^(send_message|create_quote|mark_won)$")
    approved_by: str = Field(min_length=2, max_length=120)
    note: str = Field(default="", max_length=1000)
