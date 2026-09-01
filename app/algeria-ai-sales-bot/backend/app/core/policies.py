from backend.app.models.domain import ApprovalState, LeadStage

def can_contact_lead(consent_to_contact: bool, approval: ApprovalState) -> bool:
    return consent_to_contact and approval is ApprovalState.APPROVED

def can_transition(current: LeadStage, target: LeadStage) -> bool:
    allowed = {
        LeadStage.NEW: {LeadStage.QUALIFIED, LeadStage.HUMAN_REVIEW, LeadStage.LOST},
        LeadStage.QUALIFIED: {LeadStage.HUMAN_REVIEW, LeadStage.WON, LeadStage.LOST},
        LeadStage.HUMAN_REVIEW: {LeadStage.QUALIFIED, LeadStage.WON, LeadStage.LOST},
        LeadStage.WON: set(), LeadStage.LOST: set(),
    }
    return target in allowed[current]
