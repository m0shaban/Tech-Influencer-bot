# 🌐 Keep Render Web Service Alive (24/7 Free)

## Problem
Render free tier **Web Services** sleep after 15 minutes of inactivity.

## Solution
Use **UptimeRobot** (free) to ping your service every 5 minutes.

---

## Setup Steps

### 1. Deploy to Render

Your bot now runs as a **web service** with a health endpoint at `/health`.

After deployment, you'll get a URL like:
```
https://robovai-bot.onrender.com
```

### 2. Sign Up for UptimeRobot

1. Go to: https://uptimerobot.com
2. Click **"Sign Up"** (free forever)
3. Confirm your email

### 3. Add Monitor

1. Click **"+ Add New Monitor"**
2. Fill in:
   - **Monitor Type**: HTTP(s)
   - **Friendly Name**: RoboVAI Bot Keep-Alive
   - **URL**: `https://robovai-bot.onrender.com/health`
   - **Monitoring Interval**: 5 minutes (minimum for free)
3. Click **"Create Monitor"**

### 4. Done! ✅

Your bot will now stay awake 24/7 (free).

---

## How It Works

```
UptimeRobot (every 5 min)
    ↓
    → GET https://robovai-bot.onrender.com/health
    ↓
Render stays awake (no sleep) 🎯
```

---

## Alternative: Cron-job.org

If you prefer, use https://cron-job.org instead:
1. Sign up (free)
2. Add cron job:
   - URL: `https://robovai-bot.onrender.com/health`
   - Schedule: `*/5 * * * *` (every 5 minutes)

---

## Monitoring

Check bot status anytime:
- **Health**: https://robovai-bot.onrender.com/health
- **Status**: https://robovai-bot.onrender.com/

Both return JSON:
```json
{"status": "alive", "bot": "running"}
```
