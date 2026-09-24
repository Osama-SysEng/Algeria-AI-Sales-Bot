# دليل نواة API والتشغيل المرحلي

**المشروع:** Algeria AI Sales Bot  
**المؤلف:** Manus AI  
**النطاق:** شرح النسخة التشغيلية الحالية وخطة تفعيل القنوات الخارجية تدريجيًا. لا يفترض هذا الدليل أن أي رسالة مبيعات قد أُرسلت أو أن Telegram أو CRM تم ربطهما.

## 1. الفكرة الأمنية الأساسية

تعمل النواة الحالية كـ**مساحة عمل داخلية للمبيعات**. يمكن للمشغل إنشاء عميل محتمل، وطلب مسودة رد بالدارجة من نموذج لغوي خادمي، واعتماد إجراء. لكن الاعتماد لا يستدعي أي API خارجية ولا يرسل رسالة؛ قيمة `delivery_performed` تعود صراحةً بـ`false`. هذا الفصل يمنع أن تتحول صياغة نموذج أو webhook وارد إلى رسالة أو وعد أو طلب غير مراجع.

> **قاعدة التشغيل:** المسودة ليست أمر إرسال، والموافقة ليست تنفيذًا. التنفيذ الخارجي يجب أن يكون خدمة مستقلة ذات طابور وسجل تسليم ومفتاح إيقاف طارئ.

| طبقة القرار | ما تنفذه الآن | ما لا تنفذه | الحاجز المطلوب قبل المرحلة التالية |
|---|---|---|---|
| العميل المحتمل | حفظ الاسم المرجعي والمصدر وحالة consent. | لا يتحقق من رقم هاتف حقيقي ولا يتصل بجهة خارجية. | سياسة موافقة موثقة وربط هوية/جهة اتصال محمي. |
| مسودة الذكاء الاصطناعي | تصنيف intent وإنتاج نص Darija منظم عند تهيئة LLM. | لا يخترع سعرًا أو مخزونًا أو موعد تسليم أو ضمانًا، ولا يرسل شيئًا. | كتالوج موثق، مراجعة بشرية، واختبارات جودة لهجة. |
| اعتماد الإجراء | يسجل `action_type` واسم المعتمد في audit. | لا ينشئ عرضًا ولا يحرك مرحلة البيع ولا يرسل رسالة. | RBAC، معرف طلب idempotency، ومدير/مشغل منفصلان. |
| التحليلات | تعرض أعداد العملاء والموافقات والسجل دون محتوى المحادثة. | لا تعرض نص العميل في endpoint التحليلي. | قاعدة بيانات مدارة وصلاحيات صفوف وسياسة احتفاظ. |

## 2. استعراض نواة الـAPI

نقطة الدخول هي `backend/app/main.py`. تنشئ تطبيق FastAPI، وتقيّد CORS إلى `ALLOWED_ORIGINS` بدل السماح العام، وتعرض لوحة RTL عند `/dashboard`. المسارات الآتية تقع تحت `/api/v1` وتطلب `X-Operator-Token`. أثناء التطوير فقط، تسمح النواة بالوضع المحلي إذا لم تُضبط الرموز؛ أمّا في الإنتاج فإن غياب `OPERATOR_TOKENS` يعيد `503` بدل فتح الوصول.

| المسار | الوظيفة | المدخلات المهمة | مخرج آمن |
|---|---|---|---|
| `GET /api/v1/health` | فحص الخدمة. | لا شيء. | يصرح بأن التسليم الخارجي متوقف. |
| `POST /api/v1/leads` | إنشاء عميل محتمل. | `display_name`، `contact_reference`، `source`، `consent_to_contact`. | كائن Lead دون استدعاء CRM. |
| `GET /api/v1/leads` | قراءة العملاء في الذاكرة. | رمز مشغل. | قائمة داخلية؛ ليست مخزن إنتاج دائمًا. |
| `POST /api/v1/drafts` | إنشاء مسودة LLM. | `lead_id`، رسالة العميل، سياق الكتالوج. | `ReplyDraft` مع `requires_human_approval=true`. |
| `POST /api/v1/leads/{id}/approve` | تسجيل اعتماد إجراء. | نوع الإجراء واسم المعتمد وملاحظة. | `delivery_performed=false` دائمًا. |
| `GET /api/v1/analytics` | مؤشرات تشغيلية مختصرة. | رمز مشغل. | أعداد ومراحل فقط، دون نصوص المحادثات. |

### عقد الذكاء الاصطناعي

تستخدم `services/sales_ai.py` مخرج JSON مقيدًا: `intent` و`reply_darija` و`facts_used` و`confidence`. لا يوجد مفتاح في الشيفرة؛ يقرأ الخادم `LLM_API_KEY` و`LLM_BASE_URL` و`LLM_MODEL` من البيئة. إذا لم تتهيأ هذه القيم، تعود مسودة منخفضة الثقة تطلب المراجعة اليدوية بدل فشل خفي أو استدعاء مزود غير معروف.

> أضف فقط سياق الكتالوج الموثق إلى الطلب. لا تمرر للـLLM أرقام بطاقات أو كلمات مرور أو رموز وصول أو سجلات محادثات كاملة بلا حاجة تشغيلية.

## 3. هيكل ملفات النسخة التشغيلية

```text
Algeria-AI-Sales-Bot/
├── todo.md
└── app/algeria-ai-sales-bot/
    ├── .env.example                 # عقد المتغيرات فقط؛ لا يحوي أسرارًا فعلية
    ├── requirements.txt             # تبعيات Python
    ├── Dockerfile                   # صورة التطبيق الأصلية
    ├── docker-compose.yml           # إعداد محلي؛ غيّر كلمات المرور قبل استعماله
    ├── backend/
    │   ├── app/
    │   │   ├── main.py              # FastAPI وCORS واللوحة
    │   │   ├── api/router.py        # endpoints ومسارات التدقيق
    │   │   ├── core/config.py       # قراءة متغيرات البيئة
    │   │   ├── core/policies.py     # consent والمراحل المسموحة
    │   │   ├── models/domain.py     # Lead وDraft وApproval contracts
    │   │   └── services/            # auth_service وsales_ai
    │   ├── dashboard/index.html     # واجهة RTL الداخلية
    │   └── tests/test_sales_workspace.py
    └── docs/sales-bot-operation-ar.md
```

الـ`LEADS` و`AUDIT` في `api/router.py` مخازن في الذاكرة لتوضيح العقود واختبارها؛ تختفي عند إعادة التشغيل، ولذلك لا تستخدمها كبديل لقاعدة بيانات مدارة أو سجل تدقيق قانوني.

## 4. إعداد ملف البيئة

أنشئ `.env` محليًا فقط، وأضفه إلى مدير الأسرار في بيئة الاستضافة. لا تضعه داخل ZIP أو Git أو لقطة شاشة. المثال التالي يتعمد استخدام قيم بديلة:

```dotenv
# بيئة وتشغيل
ENVIRONMENT=staging
ALLOWED_ORIGINS=https://sales-staging.example.com
OPERATOR_TOKENS=replace-with-a-long-random-operator-token

# LLM: تبقى القيم خادمية ولا يقرأها dashboard
LLM_BASE_URL=https://your-approved-llm-gateway.example.com/v1
LLM_API_KEY=replace-with-server-side-secret
LLM_MODEL=gpt-5-mini

# قاطع أمان: يبقى false إلى أن يكتمل الربط واختبارات الاعتماد
ENABLE_EXTERNAL_DELIVERY=false

# لا تضف هذه القيم إلا عند بناء موصل Telegram منفصل وموقع
TELEGRAM_BOT_TOKEN=replace-with-staging-token
TELEGRAM_WEBHOOK_SECRET=replace-with-1-to-256-char-secret
```

| متغير | الغرض | قاعدة staging |
|---|---|---|
| `ENVIRONMENT` | يفعّل الفشل المغلق عند غياب رموز المشغل في الإنتاج. | `staging`، لا `production`. |
| `ALLOWED_ORIGINS` | يسمح لمصدر لوحة محدد فقط. | استخدم نطاق staging الدقيق، لا `*`. |
| `OPERATOR_TOKENS` | وصول API الداخلي. | عشوائي وطويل، مخزن في secret manager، ويدوّر عند الاشتباه. |
| `LLM_*` | اتصال النموذج من الخادم فقط. | استخدم مشروع/مفتاح staging منفصل وحدود إنفاق. |
| `ENABLE_EXTERNAL_DELIVERY` | مفتاح حظر صريح للإرسال. | يبقى `false` خلال كل اختبارات webhook وopt-out. |
| `TELEGRAM_*` | اعتماد موصل Telegram المستقبلي. | token مختلف عن الإنتاج وsecret منفصل. |

## 5. اختبار webhook في staging

لا يحتوي الإصدار الحالي على endpoint Telegram مفعّل؛ وهذا متعمد. عند بناء الموصل، لا تعِد استخدام endpoint القديم غير المؤمَّن. أنشئ endpoint جديدًا مثل `POST /integrations/telegram/webhook` مع تحقق الرأس والـidempotency، ثم اختبره بمفتاح Telegram خاص ببيئة staging.

Telegram يدعم `setWebhook` ويرسل POST لعنوان HTTPS. كما يتيح `secret_token` يمر في رأس `X-Telegram-Bot-Api-Secret-Token`، وينصح بتقييده لحروف محددة وبطول من 1 إلى 256. واجهة Telegram تعيد محاولة التسليم إذا لم تحصل على استجابة 2xx، لذلك لابد من معالجة التكرار وعدم اعتبار محاولة واحدة وعدًا بالإرسال. [1]

| خطوة الاختبار | الإعداد | النتيجة المقبولة | نتيجة يجب أن تمنع الإطلاق |
|---|---|---|---|
| 1. نشر endpoint | نطاق staging عام عبر HTTPS وTLS 1.2+، وحساب Telegram staging. | endpoint يستقبل POST ويعيد 200 بسرعة بعد تسجيل حدث وارد. | HTTP عادي، شهادة لا تطابق الاسم، أو endpoint خاص غير قابل للوصول. [2] |
| 2. سر الرأس | عيّن `secret_token` أثناء `setWebhook` واحفظه في secret manager. | الطلب الصحيح فقط يتجاوز مقارنة ثابتة الزمن. | قبول رأس مفقود أو secret في URL أو logs. [1] |
| 3. التحقق من المخطط | اقبل أنواع update في allow-list، وحدد حجم body وtimeout. | رسالة text تجريبية مسجلة كـinbound event. | تنفيذ إرسال أو CRM من معالج webhook نفسه. |
| 4. منع الإعادة | خزّن `update_id` بمعرف فريد ورفض/تجاهل النسخة الثانية. | إرسال نفس update مرتين ينتج audit واحدًا فقط. | إنشاء مسودتين أو تنفيذين لنفس الحدث. |
| 5. فشل محكوم | أعد 5xx مؤقتًا في اختبار اصطناعي ثم أعد الطلب نفسه. | طابور واحد/سجل واحد بعد الاسترداد، ولا رسالة خارجية. | duplication أو تسريب stack trace أو توقف الخدمة. |
| 6. مراجعة الحالة | افحص `getWebhookInfo`. | `url` و`allowed_updates` و`pending_update_count` كما هو متوقع. | أخطاء تسليم متكررة أو URL غير متوقع. [1] |

بما أن `getUpdates` وwebhook طريقتان متبادلتان لاستقبال التحديثات، لا تختبر long polling في نفس وقت webhook المعيّن. تدعم Telegram webhook فقط على HTTPS والمنافذ العامة الموثقة؛ راجع التوثيق الرسمي عند تغيير البنية أو الجدار الناري. [1] [2]

### صيغة اختبار endpoint محليًا

استخدم request اصطناعيًا **دون أي token إنتاجي** للتحقق من رفض السر الخاطئ، ثم استخدم حساب Telegram staging فقط للتحقق من السر الصحيح. لا تتضمن سجلات الاختبار كامل نص العميل أو رقم هاتفه؛ احتفظ بمعرف حدث، نوعه، النتيجة وسبب الرفض.

```text
حالة A: header مفقود أو خاطئ → 401/403، لا audit business action، لا LLM.
حالة B: header صحيح وupdate_id جديد → 202/200 بعد enqueue، audit inbound واحد.
حالة C: header صحيح وupdate_id مكرر → 200/409 حسب العقد، دون معالجة جديدة.
حالة D: تحديث صالح بعد opt-out → يسجل event فقط؛ لا draft follow-up ولا queue تسليم.
```

## 6. اختبار opt-out والموافقة البشرية

تعني `consent_to_contact` في النواة الحالية أن العميل أعطى موافقة مبدئية فقط، لكنها ليست بديلًا عن سجل موافقة مفصل. أضف في قاعدة البيانات القادمة: `consent_version` و`consented_at` و`source` و`proof_reference` و`opted_out_at` و`opt_out_reason`. يجب أن يفوز opt-out على كل campaigns أو مسودات أو approvals سابقة.

| حالة اختبار | تجهيز | السلوك المتوقع | دليل التدقيق |
|---|---|---|---|
| عميل بلا consent | أنشئ lead بـ`false`. | لا يعد صالحًا للتواصل حتى لو كُتبت مسودة. | `approved_contactable=0`. |
| عميل مع consent بلا اعتماد | consent صحيح، approval معلّق. | يمكن التحرير والمراجعة، لكن لا يوجد تنفيذ. | سجل draft فقط. |
| اعتماد بشري | مشرف يوافق على `send_message`. | يسجل الاعتماد؛ هذه النسخة تبقي التسليم `false`. | المعتمد، الوقت، action والنote. |
| opt-out وارد | رسالة/زر موثق مثل “إيقاف” أو “unsubscribe”. | يغيّر الحالة إلى opted-out بصورة ذرية ويلغي الأعمال المعلقة. | event، المصدر، وقت الإلغاء، معرف الطلب. |
| إعادة webhook | أرسل حدث opt-out نفسه مرتين. | تبقى الحالة opted-out؛ لا حدث أعمال متكرر. | event idempotency key واحد. |
| محاولة بعد opt-out | حاول إنشاء مسودة متابعة أو أمر إرسال. | رفض منطقي واضح؛ لا LLM إذا أمكن ولا enqueue. | سبب الرفض: `contact_opted_out`. |

بعد نجاح هذه الحالات، أضف اختبار قبول مستقل لمسار التنفيذ الخارجي: يلتقط فقط صفًا معتمدًا وغير opted-out، يؤكد أن `idempotency_key` لم ينفذ سابقًا، ويرسل عبر موصل واحد، ثم يسجل نتيجة المزود. وجود اعتماد لا يلغي حق العميل في الإلغاء، ولا يجب أن تعمل retries بعد opt-out.

## 7. بوابة الانتقال من staging إلى الإنتاج

| البوابة | شرط القبول |
|---|---|
| الهوية والصلاحيات | RBAC فعلي، تدوير أسرار، ورفض مغلق عند غيابها. |
| البيانات | قاعدة بيانات مدارة، تشفير أثناء النقل والتخزين، retention وطلبات حذف. |
| webhook | secret header، idempotency، allow-list، rate limit، وحالة `getWebhookInfo` سليمة. |
| opt-out | حالات القبول الست أعلاه ناجحة، وإلغاء الأعمال المعلقة مؤكد. |
| الذكاء الاصطناعي | مخرجات JSON valid، لا حقائق غير موثقة، مراجعة عيّنية للدارجة والمنتج. |
| الإرسال الخارجي | outbox، retry محدود، dead-letter، تنبيه فشل، وkill switch. |
| الملاحظة | metrics لزمن الاستجابة، 4xx/5xx، retries، approvals، opt-outs، ومراجعة logs. |

## المراجع

[1]: https://core.telegram.org/bots/api "Telegram Bot API — setWebhook وgetWebhookInfo"
[2]: https://core.telegram.org/bots/webhooks "Telegram — Webhooks: HTTPS وTLS ومتطلبات الوصول"
