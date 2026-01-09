# 🔗 دليل إعادة تشغيل LinkedIn - RoboVAI

## ✅ تم إصلاح المشاكل

تم تحديث نظام LinkedIn ليعمل مع أحدث API (UGC Posts):
- ✅ إصلاح صيغة Person URN
- ✅ تحديث linkedin_publisher.py
- ✅ إضافة Client ID للإعدادات
- ✅ أدوات جديدة للاختبار وتحديث التوكن

## 📋 الخطوات المطلوبة

### الخطوة 1: احصل على Client Secret

1. افتح: https://www.linkedin.com/developers/apps
2. اختر التطبيق: **robovai bot**
3. اذهب إلى تبويب **Auth**
4. اضغط **Show** بجانب **Primary Client Secret**
5. انسخ القيمة الكاملة

### الخطوة 2: أضف Client Secret إلى .env

افتح ملف `.env` وأضف السر:

```env
LINKEDIN_CLIENT_SECRET=القيمة_التي_نسختها
```

### الخطوة 3: حدّث Access Token (التوكن ينتهي كل 60 يوم)

قد يكون التوكن الحالي منتهي الصلاحية. قم بتحديثه:

```bash
# شغّل السكريبت التفاعلي
python get_linkedin_token.py
```

**ماذا سيحدث:**
1. سيفتح متصفح فيه صفحة LinkedIn للموافقة
2. اضغط **Allow** للموافقة
3. بعد الموافقة، ستُحوّل لصفحة redirect
4. انسخ الرابط الكامل من شريط العنوان
5. الصقه في Terminal عندما يُطلب منك
6. السكريبت سيجيب لك Token جديد و Person URN

**النتيجة:** ستحصل على قيم جديدة لإضافتها في `.env`:
```env
LINKEDIN_ACCESS_TOKEN=AQxxxxxxxxxxxx...
LINKEDIN_PERSON_URN=urn:li:person:569338843
```

### الخطوة 4: اختبر LinkedIn

```bash
python test_linkedin.py
```

**الاختبارات:**
1. ✅ فحص الإعدادات (Client ID, Secret, Token, URN)
2. ✅ فحص صيغة التوكن
3. ✅ نشر بوست تجريبي (⚠️ سينشر بوست حقيقي على بروفايلك)
4. ✅ مشاركة مقال (اختياري)

**إذا نجحت كل الاختبارات:**
```
🎉 All tests passed! LinkedIn is ready to use
```

### الخطوة 5: فعّل LinkedIn في النظام

افتح `platform_config.json` وعدّل:

```json
{
  "platforms": {
    "linkedin": {
      "enabled": true,  // غيّرها من false إلى true
      "publish_mode": "delayed",
      "delay_minutes": 20,
      ...
    }
  }
}
```

## 🔧 معلومات التطبيق (LinkedIn App)

**التطبيق:** robovai bot  
**Client ID:** `78llmg4hvagid4` ✅  
**Scopes المفعّلة:**
- ✅ `r_verify` - التحقق من البروفايل
- ✅ `w_member_social` - إنشاء البوستات
- ✅ `r_profile_basicinfo` - معلومات البروفايل الأساسية

**Redirect URL:**
```
https://www.linkedin.com/developers/tools/oauth/redirect
```

## 🔄 كيف يعمل النظام

### 1. نشر بوست نصي
```python
from linkedin_publisher import LinkedInPublisher

publisher = LinkedInPublisher()
result = publisher.publish_text_post(
    caption="محتوى البوست...",
    visibility="PUBLIC"  # أو "CONNECTIONS"
)

print(f"Post ID: {result['post_id']}")
```

### 2. مشاركة مقال
```python
result = publisher.publish_article(
    caption="تعليق على المقال...",
    article_url="https://example.com/article",
    visibility="PUBLIC"
)
```

### 3. نشر صورة
```python
result = publisher.publish_image_post(
    caption="وصف الصورة...",
    image_url="https://example.com/image.jpg",
    visibility="PUBLIC"
)
```

## 📊 API Endpoints المستخدمة

**LinkedIn UGC Posts API:**
```
POST https://api.linkedin.com/v2/ugcPosts
```

**هيدر مطلوب:**
```
X-Restli-Protocol-Version: 2.0.0
Authorization: Bearer {access_token}
Content-Type: application/json
```

**صيغة الطلب:**
```json
{
  "author": "urn:li:person:569338843",
  "lifecycleState": "PUBLISHED",
  "specificContent": {
    "com.linkedin.ugc.ShareContent": {
      "shareCommentary": {
        "text": "محتوى البوست..."
      },
      "shareMediaCategory": "NONE"
    }
  },
  "visibility": {
    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
  }
}
```

## ⚠️ معلومات مهمة

### صلاحية Access Token
- **المدة:** 60 يوم (~2 شهر)
- **عند الانتهاء:** شغّل `python get_linkedin_token.py`
- **الأعراض:** خطأ 401 Unauthorized

### حدود النشر (Rate Limits)
- **عضو واحد:** 150 طلب/يوم
- **التطبيق:** 100,000 طلب/يوم

### أنواع المحتوى
| النوع | shareMediaCategory | الوصف |
|-------|-------------------|-------|
| نص فقط | `NONE` | بوست نصي بدون وسائط |
| مقال | `ARTICLE` | رابط مع preview |
| صورة | `IMAGE` | بوست مع صورة |
| فيديو | `VIDEO` | بوست مع فيديو |

## 🐛 حل المشاكل الشائعة

### المشكلة: 401 Unauthorized
**السبب:** التوكن منتهي أو غير صحيح  
**الحل:**
```bash
python get_linkedin_token.py
```

### المشكلة: 403 Forbidden
**السبب:** الـ scopes غير مفعّلة  
**الحل:** تأكد من تفعيل `w_member_social` في LinkedIn App

### المشكلة: 400 Bad Request
**السبب:** صيغة Person URN خاطئة  
**الحل:** تأكد أن URN بالصيغة: `urn:li:person:569338843`

### المشكلة: Person URN غير موجود
**الحل اليدوي:**
1. افتح: https://www.linkedin.com/in/YOUR-PROFILE/
2. افتح Chrome DevTools (F12)
3. ابحث في Network عن طلبات تحتوي على `urn:li:person`
4. انسخ الـ URN وأضفه في `.env`

## 📁 الملفات الجديدة

### `get_linkedin_token.py`
**الوظيفة:** تحديث Access Token التلقائي  
**الاستخدام:**
```bash
python get_linkedin_token.py
```

**الخطوات:**
1. يفتح صفحة Authorization في المتصفح
2. تضغط Allow
3. تنسخ redirect URL
4. يجيب لك Token جديد + Person URN

### `test_linkedin.py`
**الوظيفة:** اختبار شامل للنشر على LinkedIn  
**الاستخدام:**
```bash
python test_linkedin.py
```

**الاختبارات:**
- ✅ فحص الإعدادات
- ✅ فحص التوكن
- ✅ نشر بوست تجريبي
- ✅ مشاركة مقال (اختياري)

### `linkedin_publisher.py`
**التحديثات:**
- إصلاح Person URN format
- دعم UGC Posts API
- تحسين معالجة الأخطاء

## 🎯 التكامل مع النظام الرئيسي

عند تفعيل LinkedIn في `platform_config.json`:

**الأولوية:** Priority 5 (بعد Telegram, Discord, Blogger, Facebook)  
**التأخير:** 20 دقيقة من بداية النشر  
**الـ AI المستخدم:** Groq Fast (Llama 3.3-70B)  
**نوع المحتوى:** Professional business-focused  

**Flow النشر:**
```
Blogger (0 min) → Dev.to (2 min) → Facebook (4 min) → Telegram (6 min)
    ↓
LinkedIn (20 min) ← استراتيجي، احترافي، ROI-focused
```

## ✅ Checklist النهائي

- [ ] حصلت على Client Secret من LinkedIn Portal
- [ ] أضفت `LINKEDIN_CLIENT_SECRET` في `.env`
- [ ] شغّلت `python get_linkedin_token.py` وحصلت على token جديد
- [ ] أضفت `LINKEDIN_ACCESS_TOKEN` في `.env`
- [ ] شغّلت `python test_linkedin.py` ونجحت الاختبارات
- [ ] فعّلت LinkedIn في `platform_config.json` (`enabled: true`)
- [ ] جرّبت Force Fetch من Dashboard أو Telegram Bot

## 🎉 النتيجة المتوقعة

عند Force Fetch:
```
🔄 Sequential publishing order: ['blogger', 'devto', 'facebook', 'telegram', 'linkedin']
...
⏳ Waiting 20 minutes before publishing to linkedin...
✅ Injected CTA for linkedin
📤 Publishing to linkedin...
✅ linkedin published: https://www.linkedin.com/feed/update/...
```

---

**الحالة:** ✅ جاهز للتجربة  
**التحديث:** 2026-01-09  
**Commit:** `58457f6` - Fix LinkedIn Integration with UGC Posts API
