import json
from openai import OpenAI
from backend.app.core.config import settings
from backend.app.models.domain import DraftRequest, ReplyDraft

SCHEMA = {"name": "sales_reply_draft", "strict": True, "schema": {"type": "object", "properties": {"intent": {"type": "string", "enum": ["inquiry", "order_request", "complaint", "follow_up", "other"]}, "reply_darija": {"type": "string"}, "facts_used": {"type": "array", "items": {"type": "string"}}, "confidence": {"type": "string", "enum": ["high", "medium", "low"]}}, "required": ["intent", "reply_darija", "facts_used", "confidence"], "additionalProperties": False}}

# Lightweight local intent heuristic (Arabic / French / Algerian Darija keywords).
# Used to label the safe manual fallback when no LLM is configured, and as a
# last-resort draft if the LLM call fails. Never invents prices or stock.
_INTENT_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("order_request", ("طلب", "اطلب", "نطلب", "أطلب", "commande", "commander", "order", "نشري", "حجز", "livraison", "توصيل")),
    ("complaint", ("شكوى", "مشكل", "مشكلة", "خسارة", "عطل", "problème", "probleme", "plainte", "retour", "مرتجع", "غلط")),
    ("inquiry", ("سعر", "شحال", "بشحال", "prix", "combien", "tarif", "السعر", "استفسار", "معلومات", "info", "disponible", "متوفر", "كاين")),
    ("follow_up", ("متابعة", "وين", "أين وصل", "suivi", "suivre", "follow", "relance", "تذكير")),
)

_FALLBACK_TEMPLATE = (
    "سلام عليكم، شكراً على رسالتك. هذي مسودة رد سريعة باش يراجعها فريق المبيعات قبل الإرسال: "
    "فهمنا بلي راك مهتم، وراح نرجعولك بالتأكيد بعد ما نتأكدو من المعلومات من الكتالوج. "
    "ما نرسلو حتى رد نهائي بلا مراجعة بشرية."
)

def detect_intent_local(message: str) -> str:
    lowered = message.lower()
    for intent, keywords in _INTENT_KEYWORDS:
        if any(kw in lowered for kw in keywords):
            return intent
    return "other"

def manual_fallback(request: DraftRequest) -> ReplyDraft:
    facts = [request.catalog_context.strip()] if request.catalog_context.strip() else []
    return ReplyDraft(
        lead_id=request.lead_id,
        intent=detect_intent_local(request.customer_message),
        reply_darija=_FALLBACK_TEMPLATE,
        facts_used=facts,
        confidence="low",
    )

def draft_reply(request: DraftRequest) -> ReplyDraft:
    if not settings.llm_api_key or not settings.llm_base_url:
        return manual_fallback(request)
    try:
        client = OpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url, timeout=20.0, max_retries=1)
        response = client.chat.completions.create(model=settings.llm_model, messages=[
            {"role": "system", "content": "Draft a concise Algerian Darija sales reply. Use only supplied facts. Do not invent stock, delivery dates, discounts, prices, guarantees, or policy. Do not send messages or execute orders. Return JSON only."},
            {"role": "user", "content": f"Catalog context:\n{request.catalog_context}\n\nCustomer message:\n{request.customer_message}"},
        ], response_format={"type": "json_schema", "json_schema": SCHEMA})
        raw = response.choices[0].message.content
        if not raw:
            return manual_fallback(request)
        data = json.loads(raw)
        return ReplyDraft(lead_id=request.lead_id, **data)
    except Exception:
        # Any LLM/transport/schema failure degrades to the safe manual draft
        # instead of surfacing a 500 with no usable reply.
        return manual_fallback(request)
