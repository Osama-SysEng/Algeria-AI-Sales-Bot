import json
from openai import OpenAI
from backend.app.core.config import settings
from backend.app.models.domain import DraftRequest, ReplyDraft

SCHEMA = {"name": "sales_reply_draft", "strict": True, "schema": {"type": "object", "properties": {"intent": {"type": "string", "enum": ["inquiry", "order_request", "complaint", "follow_up", "other"]}, "reply_darija": {"type": "string"}, "facts_used": {"type": "array", "items": {"type": "string"}}, "confidence": {"type": "string", "enum": ["high", "medium", "low"]}}, "required": ["intent", "reply_darija", "facts_used", "confidence"], "additionalProperties": False}}

def draft_reply(request: DraftRequest) -> ReplyDraft:
    if not settings.llm_api_key or not settings.llm_base_url:
        return ReplyDraft(lead_id=request.lead_id, intent="other", reply_darija="مسودة الذكاء الاصطناعي غير مهيأة. راجع رسالة العميل وأعد الرد يدويًا.", facts_used=[], confidence="low")
    client = OpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)
    response = client.chat.completions.create(model=settings.llm_model, messages=[
        {"role": "system", "content": "Draft a concise Algerian Darija sales reply. Use only supplied facts. Do not invent stock, delivery dates, discounts, prices, guarantees, or policy. Do not send messages or execute orders. Return JSON only."},
        {"role": "user", "content": f"Catalog context:\n{request.catalog_context}\n\nCustomer message:\n{request.customer_message}"},
    ], response_format={"type": "json_schema", "json_schema": SCHEMA})
    raw = response.choices[0].message.content
    if not raw: raise RuntimeError("LLM returned no draft")
    return ReplyDraft(lead_id=request.lead_id, **json.loads(raw))
