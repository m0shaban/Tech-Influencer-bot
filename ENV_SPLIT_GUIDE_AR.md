# دليل فصل المتغيرات (Render vs Dashboard)

الهدف: تمنع اللخبطة بين الأسرار (Secrets) وبين إعدادات البراند (Brand Config).

## 1) متغيرات Render (Secrets) — تتظبط في Render Environment
هذه متغيرات حساسة أو خاصة بالحسابات/API Tokens. لا تضعها داخل الداشبورد.

### أساسية
- `TELEGRAM_TOKEN`
- `ADMIN_USER_ID`
- `DASHBOARD_PASSWORD`

### AI Keys (عندك 7 مفاتيح)
- `GROQ_API_KEY` (أساسي)
- `GROQ_API_KEY_2` … `GROQ_API_KEY_7` (اختياري للتوزيع/الـ load balancing)
- `NVIDIA_API_KEY` (اختياري)
- `NVIDIA_API_KEY_DEEPSEEK` (اختياري)

### نشر المنصات (حسب اللي هتشغله)
- Blogger:
  - `BLOGGER_BLOG_ID`
  - `BLOGGER_API_KEY` أو `BLOGGER_ACCESS_TOKEN`
- Facebook Page:
  - `FACEBOOK_PAGE_ACCESS_TOKEN`
  - `FACEBOOK_PAGE_ID`
- Dev.to:
  - `DEVTO_API_KEY`
- Discord:
  - `DISCORD_WEBHOOK_URL`

### الصور / ImgBB
- `IMGBB_API_KEY`

> ملاحظة: لينكدإن متعطل حالياً في `platform_config.json` بسبب 403.

## 2) متغيرات Dashboard (غير أسرار) — تتظبط من داخل الداشبورد
تتخزن داخل `config.json` (ملف داخلي).

### إعدادات عامة
- `status`: active/paused
- `force_fetch`: True/False

### Brands (الأهم)
الداشبورد يوفر Brand Manager لإضافة أكثر من براند. لكل براند:
- `system_prompt`
- `feeds` (قائمة RSS)
- `channel_id` (وجهة تيليجرام)
- `group_id` (اختياري)
- `platforms` (تفعيل/تعطيل منصات لكل براند)
- `facebook_page_url` (اختياري لو البراند له صفحة مختلفة)
- `accounts` (اختياري لتعدد الحسابات لكل منصة)

## 2.1) تعدد الحسابات لكل منصة (Multi-Accounts per platform)
الفكرة: كل Brand يختار suffix للحساب لكل منصة من الداشبورد.

مثال: لو في Brand حاطط `accounts.facebook = RBV` يبقى البوت هيبحث أولاً عن:
- `FACEBOOK_PAGE_ID_RBV`
- `FACEBOOK_PAGE_ACCESS_TOKEN_RBV`
ولو مش موجودين، هيرجع للـ defaults بدون suffix.

### Naming Convention (Render env)
- Telegram (اختياري لو عايز Bot مختلف لكل Brand): `TELEGRAM_TOKEN_<SUFFIX>`
- Facebook: `FACEBOOK_PAGE_ID_<SUFFIX>` و `FACEBOOK_PAGE_ACCESS_TOKEN_<SUFFIX>`
- Dev.to: `DEVTO_API_KEY_<SUFFIX>`
- Blogger: `BLOGGER_BLOG_ID_<SUFFIX>` + (`BLOGGER_API_KEY_<SUFFIX>` أو `BLOGGER_ACCESS_TOKEN_<SUFFIX>`) + (اختياري) `BLOGGER_REFRESH_TOKEN_<SUFFIX>`, `BLOGGER_CLIENT_ID_<SUFFIX>`, `BLOGGER_CLIENT_SECRET_<SUFFIX>`
- Discord: `DISCORD_WEBHOOK_URL_<SUFFIX>` (+ اختياري `DISCORD_USERNAME_<SUFFIX>`, `DISCORD_AVATAR_URL_<SUFFIX>`)

### Active Brand
- `active_brand`: المفتاح الحالي (مثال: `robovai_ar`)

## 3) مين “مصدر الحقيقة” لكل شيء؟
- الأسرار والتوكنز: Render فقط.
- تخصيص البراند (feeds/prompt/وجهة تيليجرام/المنصات): Dashboard فقط.
- إعدادات المنصات العامة (تأخير/أولوية/قوالب CTA): `platform_config.json` في الريبو.

## 4) Workflow مقترح (سلس)
1) اعمل Deploy جديد على Render وحط كل Secrets.
2) افتح Dashboard:
   - أضف Brand 1 (RoboVAI Arabic): feeds + prompt + channel_id + platforms.
   - اضغط "Set as Active".
3) أضف Brand 2 (Next Step English): نفس الفكرة.
4) كل مرة تحب تغيّر البراند النشط: Set as Active.

