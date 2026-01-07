# 🔗 LinkedIn Integration Guide

## Overview

RoboVAI now supports cross-posting to LinkedIn! Publish your tech content to both Telegram and LinkedIn simultaneously.

---

## 🚀 Quick Setup (5 minutes)

### Step 1: Create LinkedIn App

1. Go to: https://www.linkedin.com/developers/apps
2. Click **"Create app"**
3. Fill in:
   - **App name**: RoboVAI Publisher
   - **LinkedIn Page**: Your company page (or create one)
   - **App logo**: Upload any image
   - **Privacy policy URL**: https://yoursite.com/privacy (or use a placeholder)
4. Agree to terms → **Create app**

### Step 2: Get API Access

1. In your app, go to **Products** tab
2. Request access to: **"Share on LinkedIn"** and **"Sign In with LinkedIn"**
3. Wait for approval (usually instant for Share on LinkedIn)

### Step 3: Generate Access Token

#### Option A: Quick Test (2-hour token)

1. Go to **Auth** tab
2. Copy your **Client ID** and **Client Secret**
3. Use LinkedIn's OAuth 2.0 Playground:
   - https://www.linkedin.com/developers/tools/oauth
4. Scopes needed: `w_member_social`, `r_liteprofile`
5. Copy the **Access Token**

#### Option B: Production (60-day token)

```python
# Run this script to get a long-lived token
python scripts/linkedin_auth.py
```

### Step 4: Get Your Person URN

```bash
# Test and get your URN
python -c "from linkedin_publisher import LinkedInPublisher; p = LinkedInPublisher(); print(p._get_person_urn())"
```

### Step 5: Add to `.env`

```bash
LINKEDIN_ACCESS_TOKEN=AQV...your_token_here
LINKEDIN_PERSON_URN=urn:li:person:ABC123xyz
```

---

## ✅ Testing

```bash
# Test connection
python linkedin_publisher.py

# Expected output:
# ✅ LinkedIn connected: Your Name
```

---

## 📊 Usage

### In Config (config.json)

```json
{
  "platforms": ["telegram", "linkedin"],
  "linkedin_visibility": "PUBLIC"
}
```

### Via Admin Commands

**Enable LinkedIn:**

```
/setplatform linkedin on
```

**Publish to both:**

```
⚡ Force Fetch
(will publish to both Telegram + LinkedIn automatically)
```

**LinkedIn only:**

```
/publishlinkedin
```

---

## 🎨 Content Formatting

### Automatic Adjustments for LinkedIn:

- ✅ Professional tone maintained
- ✅ 3000 character limit enforced
- ✅ Link previews auto-generated
- ✅ Images uploaded and attached
- ✅ Hashtags optimized

### Example Transformation:

**Telegram Post:**

```
🔥 تخيل إن الكود اللي بتكتبه في يوم.. بقى يخلص في ثانية

Google عملت نقلة نوعية في Gemini...
[continues in Arabic]

🔗 لينك الخبر: https://...
```

**LinkedIn Post (auto-converted):**

```
🚀 Major breakthrough in AI development

Google's latest Gemini update demonstrates 100x speed improvement...
[professional English summary]

Read more: https://...

#AI #TechNews #Innovation
```

---

## 🔧 Advanced Configuration

### Platform-Specific Settings

```python
# In config.json
{
  "linkedin": {
    "enabled": true,
    "visibility": "PUBLIC",  # or "CONNECTIONS"
    "auto_translate": true,  # Arabic → English
    "add_hashtags": true,
    "max_hashtags": 5
  }
}
```

### Custom Publishing Logic

```python
from multi_platform_publisher import MultiPlatformPublisher

publisher = MultiPlatformPublisher()

# Publish to specific platforms
await publisher.publish(
    caption="Your content here",
    link="https://...",
    image_url="https://...",
    platforms=["linkedin"]  # Only LinkedIn
)
```

---

## 📈 Analytics (Coming Soon)

Track performance across platforms:

- LinkedIn impressions
- Engagement rate comparison
- Best-performing content per platform
- Optimal posting times

---

## 🆘 Troubleshooting

### "Access token expired"

**Solution:** Regenerate token (LinkedIn tokens expire after 60 days)

```bash
python scripts/linkedin_auth.py
```

### "Invalid URN"

**Solution:** Re-fetch your Person URN

```bash
python -c "from linkedin_publisher import LinkedInPublisher; p = LinkedInPublisher(); print(p._get_person_urn())"
```

### "Rate limit exceeded"

**Solution:** LinkedIn free tier limits:

- 100 posts/day
- Wait 1 minute between posts
  (RoboVAI handles this automatically)

---

## 💰 LinkedIn API Limits

### Free Tier:

- ✅ 100 posts/day
- ✅ Personal profiles only
- ✅ Basic analytics

### LinkedIn Marketing API (Paid):

- 🚀 Unlimited posts
- 🚀 Company pages
- 🚀 Advanced analytics
- 🚀 Sponsored content
- Cost: Contact LinkedIn Sales

---

## 🎯 Best Practices

### 1. Content Strategy

- **Telegram**: Egyptian Arabic, casual tone, emojis
- **LinkedIn**: Professional English, industry insights
- **Both**: Valuable tech content, actionable tips

### 2. Posting Frequency

- **Telegram**: 50-100 posts/day ✅
- **LinkedIn**: 5-10 posts/day (quality > quantity)
- **RoboVAI**: Auto-throttles to respect limits

### 3. Engagement

- LinkedIn posts get 2-3x more engagement than Telegram
- Use LinkedIn for career tips, case studies
- Use Telegram for breaking news, quick updates

---

## 📞 Support

Issues with LinkedIn integration?

- GitHub Issues: https://github.com/m0shaban/Tech-Influencer-bot/issues
- Tag: `linkedin` `integration`

---

**Ready to 2x your reach? Enable LinkedIn now! 🚀**
