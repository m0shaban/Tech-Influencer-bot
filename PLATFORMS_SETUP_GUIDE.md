# 🌐 دليل إعداد المنصات للنشر

هذا الدليل يشرح كيف تحصل على API keys لكل منصة وتضيفها للبوت.

---

## ✅ المنصات المفعّلة حالياً:

### 1️⃣ Telegram ✅

- **الحالة**: مفعّل
- **المطلوب**: `TELEGRAM_TOKEN`, `CHANNEL_ID`
- **الاستخدام**: قناة النشر الرئيسية

### 2️⃣ Discord ✅

- **الحالة**: مفعّل
- **المطلوب**: `DISCORD_WEBHOOK_URL`
- **الاستخدام**: مجتمع التقنية

### 3️⃣ Blogger ✅

- **الحالة**: مفعّل
- **المطلوب**: OAuth 2.0 tokens
- **الاستخدام**: مدونة تفصيلية

### 4️⃣ Facebook ✅

- **الحالة**: مفعّل
- **المطلوب**: `FACEBOOK_PAGE_ACCESS_TOKEN`, `FACEBOOK_PAGE_ID`
- **الاستخدام**: صفحة الفيسبوك

---

## 🆕 المنصات المتاحة (تحتاج إعداد):

### 5️⃣ Dev.to 🆕

**الوصف**: منصة للمطورين لنشر المقالات التقنية والشروحات

**لماذا مفيدة؟**

- ✅ مجتمع كبير من المطورين (1M+ مستخدم)
- ✅ SEO قوي جداً
- ✅ Free forever
- ✅ Markdown support
- ✅ تفاعل عالي على المحتوى التقني

**خطوات التفعيل:**

1. اذهب لـ https://dev.to
2. سجل دخول أو أنشئ حساب جديد
3. اذهب لـ Settings → Extensions: https://dev.to/settings/extensions
4. اضغط "Generate API Key"
5. انسخ الـ API Key
6. أضفه للـ `.env`:
   ```env
   DEVTO_API_KEY=your_api_key_here
   ```
7. غيّر في `platform_config.json`:
   ```json
   "devto": {
     "enabled": true,
     "publish_mode": "delayed",
     "delay_minutes": 40
   }
   ```

**اختبار:**

```bash
python devto_publisher.py
```

---

### 6️⃣ LinkedIn 💼

**الوصف**: شبكة احترافية لنشر محتوى مهني

**لماذا مفيدة؟**

- ✅ جمهور احترافي (B2B)
- ✅ مناسبة للمحتوى التقني والريادي
- ✅ Reach عالي للمحتوى الجيد

**خطوات التفعيل:**

1. اذهب لـ https://www.linkedin.com/developers/
2. أنشئ تطبيق جديد
3. احصل على Access Token
4. أضف للـ `.env`:
   ```env
   LINKEDIN_ACCESS_TOKEN=your_token
   LINKEDIN_PERSON_URN=urn:li:person:YOUR_ID
   ```

**موجود بالفعل في .env ✅** - جاهز للتفعيل!

---

### 7️⃣ Twitter / X 🐦

**الوصف**: منصة micro-blogging للأخبار السريعة

**لماذا مفيدة؟**

- ✅ انتشار سريع جداً
- ✅ مناسبة للأخبار العاجلة
- ✅ Viral potential عالي

**خطوات التفعيل:**

1. اذهب لـ https://developer.twitter.com/
2. أنشئ Project & App
3. احصل على API credentials
4. أضف للـ `.env`:
   ```env
   TWITTER_API_KEY=your_key
   TWITTER_API_SECRET=your_secret
   TWITTER_ACCESS_TOKEN=your_token
   TWITTER_ACCESS_SECRET=your_secret
   ```

---

### 8️⃣ Reddit 🤖

**الوصف**: مجتمعات متخصصة (subreddits)

**لماذا مفيدة؟**

- ✅ مجتمعات تقنية كبيرة (r/programming, r/technology)
- ✅ تفاعل عميق ومناقشات طويلة
- ✅ مصداقية عالية

**خطوات التفعيل:**

1. اذهب لـ https://www.reddit.com/prefs/apps
2. أنشئ تطبيق من نوع "script"
3. احصل على Client ID & Secret
4. أضف للـ `.env`:
   ```env
   REDDIT_CLIENT_ID=your_id
   REDDIT_CLIENT_SECRET=your_secret
   REDDIT_USERNAME=your_username
   REDDIT_PASSWORD=your_password
   REDDIT_SUBREDDIT=technology
   ```

---

### 9️⃣ Medium 📝

**الوصف**: منصة نشر مقالات طويلة وتحليلية

**لماذا مفيدة؟**

- ✅ قراء يبحثون عن محتوى عميق
- ✅ SEO ممتاز
- ✅ Monetization options

**خطوات التفعيل:**

1. اذهب لـ https://medium.com/me/settings/security
2. احصل على Integration Token
3. أضف للـ `.env`:
   ```env
   MEDIUM_ACCESS_TOKEN=your_token
   MEDIUM_AUTHOR_ID=your_id
   ```

**ملاحظة:** Medium API محدودة - يفضل استخدام RSS-to-Medium services

---

## 🚀 منصات إضافية مقترحة:

### 🔟 Hashnode

**الوصف**: منصة blogging للمطورين (منافس Dev.to)

**المميزات:**

- ✅ Custom domain مجاني
- ✅ Newsletter مدمج
- ✅ SEO قوي
- ✅ مجتمع مطورين نشط

**كيف تضيفه:**
سيحتاج إنشاء `hashnode_publisher.py` مشابه لـ `devto_publisher.py`

---

### 1️⃣1️⃣ Substack

**الوصف**: منصة newsletters احترافية

**المميزات:**

- ✅ بناء قائمة بريدية
- ✅ Monetization (subscriptions)
- ✅ Analytics قوية

**الاستخدام المقترح:**
Newsletter أسبوعي يلخص أهم الأخبار

---

### 1️⃣2️⃣ Instagram

**الوصف**: منصة visual content

**المميزات:**

- ✅ Reach كبير جداً
- ✅ Stories & Reels
- ✅ Young audience

**الاستخدام المقترح:**

- تحويل الأخبار لـ Infographics
- Stories يومية
- Carousel posts

**التحدي:** يحتاج إنشاء صور/فيديو من النص

---

### 1️⃣3️⃣ TikTok

**الوصف**: short-form video

**المميزات:**

- ✅ أعلى reach organic
- ✅ Algorithm قوي جداً
- ✅ Viral potential

**الاستخدام المقترح:**

- فيديوهات قصيرة (60 ثانية)
- شروحات سريعة
- Tech tips

**التحدي:** يحتاج video generation من النص

---

### 1️⃣4️⃣ YouTube Community

**الوصف**: Community posts على يوتيوب

**المميزات:**

- ✅ Reach من subscribers
- ✅ يدعم Text + Images + Polls
- ✅ مكمل لقناة يوتيوب

---

### 1️⃣5️⃣ WhatsApp Channel

**الوصف**: قنوات البث على واتساب

**المميزات:**

- ✅ أعلى engagement rate
- ✅ مستخدمين كثير في الوطن العربي
- ✅ Notifications قوية

---

### 1️⃣6️⃣ Telegram Stories

**الوصف**: Stories على تليجرام (feature جديد)

**المميزات:**

- ✅ مدمج مع قناتنا الحالية
- ✅ 24 hours visibility
- ✅ Interactive

---

## 📊 الترشيحات حسب الأولوية:

### 🥇 أولوية عالية (افعلهم الآن):

1. **Dev.to** ← أسهل + أكبر فائدة للمحتوى التقني ✅ **تم إضافته!**
2. **LinkedIn** ← موجود في .env، فقط فعّله
3. **Twitter** ← مهم جداً للانتشار السريع

### 🥈 أولوية متوسطة:

4. **Hashnode** ← بديل Dev.to
5. **WhatsApp Channel** ← engagement عالي
6. **Instagram** ← يحتاج تصميم صور

### 🥉 أولوية منخفضة (مستقبلاً):

7. **YouTube Community** ← إذا عملت قناة يوتيوب
8. **TikTok** ← يحتاج video production
9. **Substack** ← للـ premium content

---

## ⚙️ كيف تفعّل أي منصة:

### الخطوة 1: أضف API Key للـ .env

```env
PLATFORM_API_KEY=your_key_here
```

### الخطوة 2: فعّل في platform_config.json

```json
"platform_name": {
  "enabled": true,
  "publish_mode": "delayed",
  "delay_minutes": 45,
  "custom_prompt": "اكتب بأسلوب مناسب للمنصة...",
  "max_length": 5000,
  "priority": 10
}
```

### الخطوة 3: اختبر

```bash
python platform_name_publisher.py
```

---

## 💡 نصائح:

1. **لا تفعّل كل المنصات مرة واحدة**

   - ابدأ بـ 3-4 منصات
   - راقب الأداء
   - ثم أضف تدريجياً

2. **خصص المحتوى لكل منصة**

   - استخدم `custom_prompt` في platform_config.json
   - كل منصة لها أسلوب مختلف

3. **راقب Analytics**

   - شوف أي منصة تعطي engagement أحسن
   - ركز على الأفضل

4. **استخدم Staggered Publishing**

   - لا تنشر في نفس الوقت على كل منصة
   - وزع كل 5-10 دقائق

5. **A/B Testing**
   - جرب أوقات نشر مختلفة
   - جرب أنواع محتوى مختلفة

---

## ❓ محتاج مساعدة؟

إذا واجهت مشكلة في إعداد أي منصة:

1. شوف الـ error message
2. تأكد من الـ API keys صحيحة
3. اختبر بـ `test_connection()` function
4. شوف الـ logs في `bot.log`

---

**تم التحديث:** 7 يناير 2026
**آخر إضافة:** Dev.to Publisher ✅
