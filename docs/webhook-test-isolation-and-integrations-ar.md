# عزل اختبارات Webhook وربط Telegram وCRM بأمان

هذا الملحق يصف **التصميم المطلوب قبل تفعيل موصل Telegram أو CRM**. النسخة الحالية من Algeria AI Sales Bot لا تحوي موصل إرسال خارجي نشط، و`ENABLE_EXTERNAL_DELIVERY=false` هو الوضع الصحيح في التطوير وstaging. لا تحول وجود اختبار ناجح إلى تصريح لإرسال رسائل فعلية.

## 1. كيف تؤتمت الاختبار من دون تسريب إلى الإنتاج

اعتمد أربعة حدود مستقلة، لا حدًا واحدًا. إذا فشل حد واحد، يجب أن يظل الحد التالي مانعًا للإرسال. هذا هو معنى **الدفاع المتعدد الطبقات** في هذا المسار.

| الحد | قاعدة الإعداد | اختبار آلي مطلوب | شرط الفشل الآمن |
|---|---|---|---|
| الهوية | Bot token وCRM credentials منفصلة 100% بين staging والإنتاج. | يفشل الـCI إذا تطابق fingerprint سر staging مع fingerprint إنتاج معروف. | لا يبدأ الموصل عند تطابق أو غياب `ENVIRONMENT=staging`. |
| الوجهة | `TELEGRAM_WEBHOOK_URL` و`CRM_BASE_URL` على نطاقات staging فقط. | اختبار سياسة يرفض نطاقات الإنتاج وقوائم المستلمين الإنتاجية. | يرفض الطلب قبل أي استدعاء شبكي. |
| التنفيذ | `OUTBOUND_DELIVERY_MODE=dry_run` في staging. | اختبار يثبت أن كل محاولة تنتج audit/outbox فقط ولا تستدعي HTTP client الخارجي. | أي mode غير معروف يعامل كـ`disabled`. |
| القرار البشري | `REQUIRE_HUMAN_APPROVAL=true`. | اختبار يثبت أن المسودة أو webhook الوارد لا ينشئ job إرسال. | لا يدخل outbox إلا request معتمد وصالح وغير opted-out. |

> **قاعدة قاطعة:** لا تستخدم token أو bot أو CRM sandbox مشتركًا مع الإنتاج. بيئة الاختبار تحتاج حسابات، مفاتيح، نطاقات، وسجلات منفصلة.

### مسار CI المقترح

في كل Pull Request، شغّل اختبارات وحدة بلا شبكة حقيقية. تستخدم الاختبارات server stub أو transport مزيفًا، وتتحقق من أن `send_message` لم يستدعَ. بعد الدمج إلى فرع staging فقط، شغّل اختبار تكامل محدود ضد Telegram staging وCRM sandbox، مع متلقٍ واحد مخصص للاختبار ومثبت في allow-list.

| طبقة الاختبار | مدخلات الاختبار | ما الذي يثبت؟ | ما الذي لا يفعله؟ |
|---|---|---|---|
| وحدة | update JSON محفوظ وموقّع تجريبيًا. | التحقق من السر، المخطط، `update_id`، opt-out، وقرار الرفض. | لا يفتح اتصال Telegram أو CRM. |
| عقد/تكامل | endpoint staging وtest bot وCRM sandbox. | نجاح webhook واستجابة 2xx ومعالجة event مرة واحدة. | لا يرسل إلى عملاء حقيقيين أو CRM إنتاجي. |
| قبول | test chat واحد وtest lead واحد بعد موافقة بشرية. | سلسلة audit → outbox → mock/dry-run. | لا يحول `dry_run` إلى إرسال حي. |
| نشر | فحص إعدادات وقت النشر. | البيئة، النطاق، الـmode، الأسرار، allow-list. | لا ينشر إذا وجدت قيمة إنتاج في staging. |

### اختبارات سلبية يجب أن تكون إلزامية

اختبر سر webhook خاطئًا أو مفقودًا، ثم `update_id` مكررًا، ثم webhook صحيحًا لعميل opted-out، ثم أمر اعتماد بلا consent. في الحالات الأربع يجب ألا يوجد استدعاء مزود خارجي وألا ينشأ أكثر من audit event صحيح. يمكن أن يعيد endpoint خطأ منضبطًا أو قبولًا idempotent حسب عقدك، لكن **لا يكرر العمل**.

تسمح Telegram بتعيين `secret_token` في `setWebhook` ويرسل في رأس `X-Telegram-Bot-Api-Secret-Token`. كما تعيد محاولة التسليم إن لم تتلقَّ استجابة 2xx، ولذلك فإن تخزين `update_id` كمفتاح فريد ضروري لاختبار إعادة المحاولة بأمان. [1]

## 2. مخطط التنفيذ الآمن

```text
Telegram staging webhook
        │  (secret header + schema + rate limit)
        ▼
Inbound event store ──► idempotency check ──► opt-out/consent gate
                                                    │
                              ┌─────────────────────┴────────────────────┐
                              ▼                                          ▼
                         rejected audit                            draft / review
                                                                         │
                                                         human approval + policy gate
                                                                         │
                                            dry-run outbox ──► mock transport only
```

في الإنتاج المستقبلي فقط، استبدل `mock transport only` بعامل outbox منفصل يقرأ صفًا مستوفيًا للشروط. يجب أن يمر العامل بفحوص إضافية: environment صريح، عدم opt-out، approval صالح، idempotency key غير منفذ، ومفتاح إرسال تشغيلي منفصل. لا تجعل معالج webhook نفسه يرسل الرسالة؛ فهو مسار وارد قد يعاد أو يتأخر أو يتلقى ضغطًا.

## 3. متغيرات البيئة الأساسية

لا تكتب القيم الفعلية داخل `.env.example` أو Git أو أرشيف التسليم. استخدم مدير أسرار بيئة الاستضافة، وأنشئ القيم الطويلة عشوائيًا، وفصل secret لكل بيئة.

### متغيرات أساسية مشتركة

| المتغير | مثال شكل القيمة فقط | الغرض | staging | production |
|---|---|---|---|---|
| `ENVIRONMENT` | `staging` | اختيار سياسة البيئة. | مطلوب. | `production` فقط بعد البوابات. |
| `ALLOWED_ORIGINS` | `https://sales-staging.example.com` | CORS للوحة الداخلية. | نطاق staging دقيق. | نطاق الإنتاج الدقيق. |
| `OPERATOR_TOKENS` | token عشوائي طويل | حماية API الداخلي. | مفتاح staging فقط. | مفتاح منفصل وتدوير دوري. |
| `REQUIRE_HUMAN_APPROVAL` | `true` | منع الإرسال دون إنسان. | `true`. | `true`. |
| `OUTBOUND_DELIVERY_MODE` | `disabled`/`dry_run` | وضع عامل الإرسال. | `dry_run`. | يبدأ `disabled` ثم `approval_only`. |
| `ENABLE_EXTERNAL_DELIVERY` | `false` | قاطع عام للإرسال. | `false`. | لا يتحول إلى `true` قبل قبول كامل. |
| `OUTBOX_ENCRYPTION_KEY` | سر عشوائي | حماية حمولة outbox إذا حفظت رسائل. | مفتاح منفصل. | مفتاح منفصل في KMS/secret manager. |

### Telegram

| المتغير | الغرض | قاعدة الأمان |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | اعتماد bot. | Bot staging مختلف عن production؛ لا يظهر في المتصفح أو logs. |
| `TELEGRAM_WEBHOOK_URL` | عنوان استقبال updates. | HTTPS على نطاق staging؛ لا تستخدم URL الإنتاج. Telegram تشترط HTTPS للـwebhook وتوثق المنافذ المدعومة. [1] [2] |
| `TELEGRAM_WEBHOOK_SECRET` | مطابقة رأس secret token. | 1–256 حرفًا مسموحًا به حسب Telegram؛ قارن بطريقة ثابتة الزمن ولا تضعه في URL. [1] |
| `TELEGRAM_ALLOWED_UPDATES` | allow-list لأنواع update. | ابدأ بـ`message` فقط؛ لا تقبل أنواعًا لا تختبرها. |
| `TELEGRAM_TEST_CHAT_IDS` | allow-list لمستلمي الاختبار. | تستخدم فقط في staging مع `dry_run`; لا تتضمن عملاء. |
| `TELEGRAM_API_BASE_URL` | endpoint المزود. | لا تغيّره إلى proxy مجهول؛ استخدم endpoint رسمي أو gateway معتمد. |

### CRM بشكل مستقل عن المزود

CRM غير محدد في المشروع، لذلك لا تفترض اسم متغير خاص بمزود بعينه. طبقة الموصل يجب أن تقرأ مجموعة عامة كهذه ثم تحولها داخل adapter للمزود المحدد.

| المتغير | الغرض | قاعدة الأمان |
|---|---|---|
| `CRM_PROVIDER` | مثل `hubspot` أو `salesforce` أو `custom`. | allow-list؛ لا تقبل اسمًا حرًا من طلب مستخدم. |
| `CRM_BASE_URL` | أصل API أو sandbox. | نطاق sandbox في staging، وتحقيق scheme=`https`. |
| `CRM_CLIENT_ID` | OAuth client identifier. | client staging منفصل. |
| `CRM_CLIENT_SECRET` | OAuth server secret. | secret manager فقط؛ لا يظهر في سجل خطأ. |
| `CRM_REFRESH_TOKEN` | تجديد token عند الحاجة. | حساب خدمة محدود scope وبيئة واحدة. |
| `CRM_API_TOKEN` | بديل machine-to-machine. | استخدمه بدل OAuth فقط إذا أوصى المزود؛ least privilege. |
| `CRM_PIPELINE_ID` | pipeline المسموح به. | pipeline sandbox منفصل؛ validate server-side. |
| `CRM_ALLOWED_OWNER_IDS` | ملاك يمكن الإسناد إليهم. | allow-list؛ لا يقبل owner من webhook. |
| `CRM_WEBHOOK_SIGNING_SECRET` | إذا كان CRM يرسل webhooks أيضًا. | يختلف عن Telegram secret ويتحقق منه endpoint منفصل. |

## 4. ملف `.env` نموذجي لـstaging

النموذج التالي يوضح الأسماء والاتجاه فقط. بدّل كل قيمة بديل بسر من مدير أسرار ولا تنسخه لإنتاج.

```dotenv
ENVIRONMENT=staging
ALLOWED_ORIGINS=https://sales-staging.example.com
OPERATOR_TOKENS=replace-with-long-staging-operator-token
REQUIRE_HUMAN_APPROVAL=true
OUTBOUND_DELIVERY_MODE=dry_run
ENABLE_EXTERNAL_DELIVERY=false
OUTBOX_ENCRYPTION_KEY=replace-with-staging-outbox-key

TELEGRAM_BOT_TOKEN=replace-with-staging-bot-token
TELEGRAM_WEBHOOK_URL=https://api-staging.example.com/integrations/telegram/webhook
TELEGRAM_WEBHOOK_SECRET=replace-with-telegram-staging-secret
TELEGRAM_ALLOWED_UPDATES=message
TELEGRAM_TEST_CHAT_IDS=replace-with-dedicated-test-chat-id
TELEGRAM_API_BASE_URL=https://api.telegram.org

CRM_PROVIDER=replace-with-approved-provider
CRM_BASE_URL=https://sandbox.crm-provider.example.com
CRM_CLIENT_ID=replace-with-staging-client-id
CRM_CLIENT_SECRET=replace-with-staging-client-secret
CRM_REFRESH_TOKEN=replace-with-staging-refresh-token
CRM_PIPELINE_ID=replace-with-sandbox-pipeline-id
CRM_ALLOWED_OWNER_IDS=replace-with-sandbox-owner-id
```

## 5. شرط التفعيل الحي

لا يكفي تغيير `ENABLE_EXTERNAL_DELIVERY=true`. قبل ذلك، يجب أن تنجح اختبارات العزل، وإعادة الإرسال، opt-out، approval، ومراقبة التسليم في staging. ويجب أن يوافق مسؤول مخول على تغيير تشغيل مستقل. عند إطلاق محدود، استخدم allow-list ضيقة، وسقفًا يوميًا، وkill switch، وتنبيهات على أي خطأ تسليم أو ازدياد في opt-out.

## المراجع

[1]: https://core.telegram.org/bots/api "Telegram Bot API — setWebhook، secret token، retries وgetWebhookInfo"
[2]: https://core.telegram.org/bots/webhooks "Telegram Webhooks — HTTPS وTLS ومتطلبات الاستقبال"
