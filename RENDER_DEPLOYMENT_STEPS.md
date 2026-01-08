# 🚀 Render.com Deployment - Step by Step

## ✅ Pre-Deployment Checklist

### Files Ready:

- ✅ `render.yaml` - Service configuration
- ✅ `requirements.txt` - Python dependencies
- ✅ `.gitignore` - Security (excludes .env)
- ✅ All source code committed to Git

---

## 📋 Step 1: Upload to GitHub

### 1.1 Create GitHub Repository

1. Go to: https://github.com/new
2. Fill in:
   - **Repository name:** `robobot`
   - **Description:** `RoboVAI - AI-powered Telegram RSS Bot`
   - **Visibility:** Public or Private (your choice)
   - ⚠️ **DO NOT** check "Initialize with README"
3. Click **"Create repository"**

### 1.2 Push Local Code

After creating the repository, GitHub will show you commands. Run:

```powershell
cd F:\robobot
git remote add origin https://github.com/YOUR_USERNAME/robobot.git
git branch -M main
git push -u origin main
```

**Replace `YOUR_USERNAME` with your actual GitHub username!**

---

## 🎯 Step 2: Deploy to Render.com

### 2.1 Sign Up / Login

1. Go to: https://render.com
2. Click **"Get Started"** or **"Sign In"**
3. Choose **"Sign in with GitHub"** (recommended)
4. Authorize Render to access your repositories

### 2.2 Create New Blueprint

1. Click the **"New +"** button (top right)
2. Select **"Blueprint"**
3. Connect your GitHub repository:
   - If not connected: Click **"Connect GitHub"**
   - Select the **`robobot`** repository
4. Click **"Connect"**

### 2.3 Render Reads `render.yaml`

Render will automatically detect `render.yaml` and show you:

**Services to be created:**

- ✅ **robovai-worker** (Background Worker) - Telegram Bot (Polling)

### 2.4 Add Environment Variables

⚠️ **CRITICAL STEP!** Add these for the **worker** service:

Click on **"Add Environment Variable"** and add:

```
TELEGRAM_TOKEN=your_bot_token_here
ADMIN_USER_ID=your_telegram_user_id
CHANNEL_ID=@your_channel_username
GROUP_ID=your_group_id_or_username
GROQ_API_KEY=your_groq_api_key_here

# Storj public image URLs (required for Facebook/Discord/Dev.to/etc)
STORJ_ACCESS_KEY_ID=...
STORJ_SECRET_ACCESS_KEY=...
STORJ_ENDPOINT_URL=https://gateway.storjshare.io
STORJ_BUCKET=your_bucket
STORJ_PUBLIC_BASE_URL=https://link.storjshare.io/raw/<share-token>/<bucket>
```

**How to get these values:**

| Variable                | Where to Find                                 |
| ----------------------- | --------------------------------------------- |
| `TELEGRAM_TOKEN`        | @BotFather on Telegram                        |
| `ADMIN_USER_ID`         | @userinfobot on Telegram (send /start)        |
| `CHANNEL_ID`            | Your channel username (e.g., @nextlevelegypt) |
| `GROUP_ID`              | Group chat ID (use @userinfobot in the group) |
| `GROQ_API_KEY`          | https://console.groq.com/keys                 |
| `STORJ_PUBLIC_BASE_URL` | Public base URL (anonymous GET must work)     |

### 2.5 Review & Deploy

1. Review the configuration
2. Click **"Apply"**
3. ⏳ Wait 3-5 minutes for deployment

---

## 🎉 Step 3: Verify Deployment

### 3.1 Check Services Status

In Render Dashboard, you should see:

**robovai-worker** (Background Worker)

- Status: ✅ **Live**
- Logs: Should show "Bot started" message

### 3.2 Test the Bot

1. Open Telegram
2. Send `/start` to your bot
3. Admin should see: "أهلاً يا هندسة! 🚀 غرفة التحكم جاهزة."
4. Click **"⚡ Force Fetch"** to test publishing

### 3.3 Test the Dashboard

Dashboard is intended to run on **Streamlit Cloud** (separate from Render).
Deploy the same repo there and run:

`streamlit run dashboard.py`

---

## 🔧 Step 4: Post-Deployment Configuration

### 4.1 Telegram Conflict (مهم جداً)

لو ظهر خطأ `telegram.error.Conflict` يبقى فيه **نسختين** من البوت شغالين.
اقفل/احذف أي Deploy تاني (Railway/Local/Service قديم على Render) بنفس `TELEGRAM_TOKEN`.

### 4.2 Monitor Logs

**For Worker (Telegram Bot):**

1. Go to Render Dashboard
2. Click **robobot-worker**
3. Click **"Logs"** tab
4. Watch for successful posts: `Published: https://...`

**For Dashboard:**

1. Click **robobot-dashboard**
2. Click **"Logs"** tab
3. Look for: `You can now view your Streamlit app`

---

## ⚠️ Troubleshooting

### Problem: "Worker keeps crashing"

**Solution:**

1. Check Logs for error messages
2. Common issues:
   - Missing environment variables
   - Invalid TELEGRAM_TOKEN
   - GROQ_API_KEY quota exceeded

### Problem: "Dashboard shows 404"

**Solution:**

1. Wait 2-3 minutes after first deploy
2. Check if build completed successfully
3. Verify `startCommand` in render.yaml

### Problem: "Bot not responding in Telegram"

**Solution:**

1. Check Worker logs
2. Verify TELEGRAM_TOKEN is correct
3. Make sure webhook is not enabled elsewhere
4. Restart the worker service

### Problem: "Out of memory (free tier limit)"

**Solution:**

1. Free tier has 512MB RAM limit
2. If needed, reduce `DEFAULT_MAX_TOKENS` in `ai_processor.py`:
   ```python
   DEFAULT_MAX_TOKENS = 1200  # Instead of 1800
   ```

---

## 📊 Free Tier Limits

### Render.com Free Tier:

- ✅ **750 hours/month** for Web Services
- ✅ **Unlimited hours** for Background Workers (like your bot!)
- ✅ **512MB RAM** per service
- ⚠️ Web Services sleep after **15 minutes** of inactivity
- ✅ **Auto-deploys** on every Git push

### Pro Tips:

1. خلي Render فيه **Worker واحد فقط** للبوت ✅
2. خلي الصور تطلع Public عبر Storj عشان باقي المنصات ✅

---

## 🔄 Updating Your Bot

### To deploy updates:

1. Make changes to your code
2. Commit and push:
   ```powershell
   git add .
   git commit -m "Update: description of changes"
   git push
   ```
3. Render auto-deploys! ✅

---

## 🆘 Getting Help

### Check Logs First:

- Render Dashboard → Your Service → Logs tab

### Common Log Messages:

**✅ Success:**

```
Bot started
Published: https://...
System Ready to Launch
```

**❌ Errors:**

```
Missing GROQ_API_KEY → Add in environment variables
Telegram error 401 → Check TELEGRAM_TOKEN
json_validate_failed → Groq API issue, will retry
```

### Health Check:

After deployment, you can run health check from Render Shell:

1. Go to Service → Shell
2. Run: `python health_check.py`

---

## 🎯 Next Steps After Deployment

### 1. Monitor Performance

- Check logs daily for the first week
- Verify posts are publishing correctly
- Watch for any errors

### 2. Customize Content

- Use Dashboard to adjust system prompt
- Add/remove RSS feeds
- Change posting frequency (in code)

### 3. Scale (Optional)

- Upgrade to paid tier for more RAM/hours
- Add more channels
- Implement analytics

---

## 📞 Support Resources

- **Render Docs:** https://render.com/docs
- **Telegram Bot API:** https://core.telegram.org/bots/api
- **Groq API Docs:** https://console.groq.com/docs
- **Streamlit Docs:** https://docs.streamlit.io

---

## ✅ Final Checklist

Before going live, verify:

- [ ] GitHub repository created and pushed
- [ ] Render Blueprint deployed successfully
- [ ] All 6 environment variables added
- [ ] Worker status shows "Live"
- [ ] Dashboard accessible via URL
- [ ] Bot responds to /start in Telegram
- [ ] Force Fetch publishes successfully
- [ ] Dashboard login works with password
- [ ] UptimeRobot monitor set up (optional)

---

**🎉 Congratulations! Your RoboVAI Bot is now live on Render.com!**

Enjoy your 24/7 AI-powered content bot! 🚀
