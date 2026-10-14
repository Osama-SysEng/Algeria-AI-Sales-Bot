# Algeria AI Sales Bot — مساعد مبيعات ذكي للسوق الجزائري

منصة تجريبية لتمكين فرق المبيعات: إدارة العملاء المحتملين (Leads)، مسودات ردود بالعربية والفرنسية والدارجة الجزائرية، ومراحل بيع محكومة — مع بوابة موافقة بشرية قبل أي إجراء خارجي.

## الحالة

- **النطاق:** نموذج تشغيلي (FastAPI + تخزين في الذاكرة). لا قاعدة بيانات دائمة بعد — تُفقد البيانات عند إعادة التشغيل.
- **الذكاء:** كشف نوايا محلي (عربي/فرنسي/دارجة) + LLM خارجي اختياري عبر `LLM_BASE_URL`/`LLM_API_KEY` مع fallback آمن. أي فشل ينحدر لمسودة محلية بدل الخطأ 500.
- **الأمان:** حد معدل 120/دقيقة لكل IP+مسار، منع تكرار `contact_reference` (409)، رفض القفز بين المراحل (422)، حارس موافقة يرفض التسليم الخارجي غير المنفذ (503).

## البنية

```
Algeria-AI-Sales-Bot/app/algeria-ai-sales-bot/
├── backend/app/
│   ├── main.py            # الدخول: backend.app.main:app
│   ├── api/router.py      # Leads + drafts + stages + analytics
│   ├── core/              # الإعداد والسياسات (21 متغيرا موثقا في .env.example)
│   ├── models/domain.py   # النماذج والتحقق
│   └── services/sales_ai.py  # كشف النية + fallback الدارجة
├── backend/dashboard/index.html
├── Dockerfile
└── requirements.txt
```

## البدء السريع

```bash
cd Algeria-AI-Sales-Bot/app/algeria-ai-sales-bot
cp .env.example .env
pip install -r requirements.txt
uvicorn backend.app.main:app --reload
# الصحة: http://localhost:8000/api/v1/health
# اللوحة: http://localhost:8000/dashboard/
```

## الاختبارات

```bash
cd Algeria-AI-Sales-Bot/app/algeria-ai-sales-bot
python -m pytest backend/tests -q   # 3 passed
```

## الحدود الصادقة

- لا إرسال خارجي فعلي (Telegram/CRM): موصلاتها قرار تشغيلي مستقبلي (webhook موقّع + outbox).
- لا استمرارية بيانات: للانتقال للإنتاج يلزم PostgreSQL.
- الدارجة: قواعد نوايا خفيفة، ليست نموذج لغه مدربا.

- تسجيل منظم JSON مع request_id وحجب الأسرار (راجع docs/LOGGING.md).
