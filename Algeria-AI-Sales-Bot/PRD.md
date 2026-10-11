# PRD — Algeria-AI-Sales-Bot (مساعد مبيعات جزائري)
## 1. نظرة عامة
- مساحة مبيعات بمساعدة AI مع بوابات موافقة بشرية إلزامية.
- التدفق: leads ← مسودات رد بالدارجة ← اعتماد إجراء. بدون إرسال خارجي.
- Backend: FastAPI (`backend/app/api/router.py`) ببادئة `/api/v1`.
- اللوحة: ملفات static على `/dashboard`.
## 2. المستخدمون
1. مشغّل (operator) عبر ترويسة `X-Operator-Token` (`require_operator`).
2. مراجع مبيعات يعتمد الإجراءات (`approved_by`).
3. مدقق يقرأ `/analytics` وaudit events.
## 3. الميزات الأساسية (قابلة للاختبار)
1. فحص صحة يعيد `external_delivery:false`.
2. إنشاء lead مع منع تكرار `contact_reference` (409).
3. قائمة leads بترقيم (`limit` 1–500 و`offset`).
4. نقل مرحلة حسب سياسة `can_transition` (وإلا 422).
5. المراحل: `new|qualified|human_review|won|lost`.
6. إنشاء مسودة رد (LLM عند ضبطه أو fallback محلي آمن).
7. المسودة لا تخترع أسعارًا/مخزونًا وتطلب موافقة بشرية دائمًا.
8. اعتماد إجراء محروس بالموافقة: `consent_to_contact` وإلا 422.
9. `action_type` محصور في `send_message|create_quote|mark_won`.
10. تحليلات: عدد، حسب المرحلة، موافَقون قابلون للتواصل، أحداث audit.
## 4. الـAPI endpoints الحقيقية (من الكود فقط)
- `GET /api/v1/health`
- `POST /api/v1/leads` — 409 عند تكرار `contact_reference`.
- `GET /api/v1/leads?limit=&offset=`
- `POST /api/v1/leads/{lead_id}/stage` — 422 عند انتقال ممنوع.
- `POST /api/v1/drafts` — 404 إن غاب lead.
- `POST /api/v1/leads/{lead_id}/approve` — يعيد `delivery_performed:false`.
- `GET /api/v1/analytics`
- `GET /dashboard` (ملفات static).
## 5. بيانات الدخول/الإعداد للاختبار
- عيّن `OPERATOR_TOKENS=tok-test-1` ومرّره `X-Operator-Token: tok-test-1`.
- بدون `LLM_BASE_URL/LLM_API_KEY` يعمل fallback محلي (`confidence:low`).
- النموذج الافتراضي `gpt-5-mini` عند ضبط LLM.
- مثال lead: `{display_name, contact_reference, source, consent_to_contact}`.
- مثال draft: `{lead_id, customer_message, catalog_context}`.
- مثال approve: `{action_type:"send_message", approved_by:"op-1"}`.
- الاختبار: `pytest backend/tests/test_sales_workspace.py`.
- حد معدل داخلي 120/دقيقة لكل (IP, path).
## 6. خارج النطاق (mocked/simulated — صراحة)
- لا إرسال خارجي: `delivery_performed:false` دائمًا.
- تفعيل `ENABLE_EXTERNAL_DELIVERY` يرد 503 (غير منفذ).
- لا موصل Telegram ولا CRM (مجموعات env محجوزة فقط).
- `requires_human_approval=true` دائمًا.
- التخزين in-memory (`LEADS`/`AUDIT`) — يُفقد عند إعادة التشغيل.
