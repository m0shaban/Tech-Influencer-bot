# 🚀 دليل نشر RoboVAI Bot - مجاناً

## الخيار الأول: Railway.app (الأسهل - مُوصى به)

### المتطلبات
- حساب GitHub
- حساب Railway.app
- المتغيرات البيئية (.env values)

### الخطوات

#### 1. إعداد GitHub Repository

```bash
# Initialize git (إذا لم يكن موجود)
cd F:\robobot
git init
git add .
git commit -m "Initial commit - RoboVAI Bot"

# Create repository على GitHub ثم:
git remote add origin https://github.com/YOUR_USERNAME/robobot.git
git branch -M main
git push -u origin main
```

#### 2. Deploy على Railway

1. اذهب إلى: https://railway.app
2. اضغط **"Start a New Project"**
3. اختر **"Deploy from GitHub repo"**
4. اختر الـ repository: `robobot`
5. Railway هيعمل auto-detect للـ Python project

#### 3. إضافة Environment Variables

في Railway Dashboard:
- اضغط على الـ **Variables** tab
- أضف كل المتغيرات من `.env`:

```
TELEGRAM_TOKEN=your_bot_token_here
ADMIN_USER_ID=your_telegram_user_id
CHANNEL_ID=@your_channel_username
GROUP_ID=your_group_id
GROQ_API_KEY=your_groq_api_key
DASHBOARD_PASSWORD=your_secure_password
```

#### 4. Configure Start Command

في Railway Settings:
- **Start Command:** 
```bash
python main.py & streamlit run dashboard.py --server.port=$PORT --server.address=0.0.0.0
```

#### 5. Deploy!

- اضغط **Deploy**
- استنى 2-3 دقائق
- Railway هيديك URL للـ dashboard

### 🎉 تم! البوت شغال دلوقتي

**Dashboard URL:** `https://your-project.railway.app`

---

## الخيار الثاني: Render.com (أكثر استقرار)

### المميزات
- ✅ 750 hours/month مجاناً
- ✅ Auto-sleep بعد 15 دقيقة inactivity
- ✅ Web Service + Background Worker منفصلين

### الخطوات

#### 1. إعداد GitHub (نفس الخطوة أعلاه)

#### 2. Create render.yaml

الملف موجود بالفعل في المشروع!

#### 3. Deploy على Render

1. اذهب إلى: https://render.com
2. اضغط **"New +"** → **"Blueprint"**
3. اختر الـ GitHub repo
4. Render هيقرأ `render.yaml` تلقائياً
5. أضف الـ Environment Variables
6. اضغط **Apply**

#### 4. Configure Services

Render هينشئ:
- **Web Service:** Streamlit Dashboard (ينام بعد 15 دقيقة)
- **Background Worker:** Telegram Bot (يشتغل 24/7)

### Keep Dashboard Awake (اختياري)

استخدم **UptimeRobot** أو **Cron-job.org** للـ ping:
```
https://your-app.onrender.com
```

---

## الخيار الثالث: Google Cloud Run (للمحترفين)

### المميزات
- ✅ 2 million requests مجاناً
- ✅ Serverless - مش محتاج تدير servers
- ✅ Auto-scaling

### المتطلبات
- حساب Google Cloud
- Docker knowledge (basic)

### الخطوات

#### 1. إنشاء Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["sh", "-c", "python main.py & streamlit run dashboard.py --server.port=8080 --server.address=0.0.0.0"]
```

#### 2. Deploy

```bash
# Install gcloud CLI
# ثم:
gcloud init
gcloud run deploy robobot --source . --region us-central1 --allow-unauthenticated
```

---

## الخيار الرابع: Oracle Cloud (Always Free - الأقوى)

### المميزات
- ✅ مجاني **للأبد** (Always Free Tier)
- ✅ 2 VMs مجانية (ARM-based)
- ✅ 200GB storage
- ✅ أفضل من كل الخيارات الأخرى!

### العيوب
- ⚠️ Setup أصعب شوية
- ⚠️ محتاج تدير Linux server

### الخطوات (مختصرة)

1. إنشاء حساب: https://cloud.oracle.com
2. Create VM Instance (Always Free - ARM)
3. SSH للـ server:
```bash
ssh ubuntu@your-vm-ip
```
4. Install dependencies:
```bash
sudo apt update
sudo apt install python3-pip git
```
5. Clone repo & setup:
```bash
git clone https://github.com/YOUR_USERNAME/robobot.git
cd robobot
pip3 install -r requirements.txt
```
6. Create systemd services (للـ auto-restart):
```bash
sudo nano /etc/systemd/system/robobot.service
```
7. Enable & start:
```bash
sudo systemctl enable robobot
sudo systemctl start robobot
```

---

## 📊 مقارنة سريعة

| الخيار | السهولة | الاستقرار | المدة المجانية | مناسب لـ |
|--------|---------|-----------|----------------|----------|
| **Railway** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | $5/شهر (~500hrs) | المبتدئين |
| **Render** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 750 hrs/month | الجميع |
| **GCP Run** | ⭐⭐⭐ | ⭐⭐⭐⭐ | 2M requests | المحترفين |
| **Oracle** | ⭐⭐ | ⭐⭐⭐⭐⭐ | للأبد! | Technical users |

---

## 🎯 التوصية النهائية

### للمبتدئين:
**ابدأ بـ Railway.app** - أسهل وأسرع حل

### للاستقرار الطويل:
**استخدم Render.com** - أفضل free tier

### إذا كنت technical:
**Oracle Cloud Always Free** - مجاني للأبد مع إمكانيات ممتازة

---

## 🔧 ملاحظات مهمة

### 1. الـ Dashboard Password
في كل الحالات، ضيف:
```
DASHBOARD_PASSWORD=your_secure_password_here
```

### 2. Groq API Limits
- Free tier: 30 requests/minute
- لو قربت من الحد، زود الـ fetch interval

### 3. Keep Alive
Railway و Render بينام الـ services بعد inactivity. الحلول:
- استخدم UptimeRobot للـ ping كل 5 دقائق
- أو استخدم GitHub Actions workflow (موجود في `.github/workflows/`)

### 4. Logs Monitoring
كل المنصات بتوفر logs viewer. تابع الـ logs في البداية.

---

## 🆘 المشاكل الشائعة

### البوت مش بيرد في Telegram
- تأكد إن `TELEGRAM_TOKEN` صحيح
- تأكد إن الـ webhook مش مفعّل (الكود بيحذفه تلقائياً)

### الـ Dashboard مش بيفتح
- تأكد إن الـ PORT environment variable موجودة
- Railway/Render بتحطها تلقائياً

### "Out of memory" error
- Render free tier: 512MB RAM
- قلل الـ `DEFAULT_MAX_TOKENS` لو محتاج

---

## 📞 الدعم

إذا واجهت مشكلة:
1. افحص الـ logs
2. تأكد من الـ environment variables
3. اعمل health check: `python health_check.py`

---

**🎉 بالتوفيق في الـ deployment!**
