# Streamlit Cloud Secrets Configuration

Copy this to Streamlit Cloud → App Settings → Secrets:

```toml
# Copy these values from your .env file
DASHBOARD_PASSWORD = "your_password"
TELEGRAM_TOKEN = "your_telegram_bot_token"
CHANNEL_ID = "@your_channel"
GROUP_ID = "your_group_id"
GROQ_API_KEY = "your_groq_api_key"
GROQ_MODELS = "llama-3.3-70b-versatile,llama-3.1-70b-versatile,llama-3.1-8b-instant"
ADMIN_USER_ID = "your_telegram_user_id"

# Optional: Platform credentials (if you want to manage them from dashboard)
DISCORD_WEBHOOK_URL = "your_discord_webhook"
FACEBOOK_PAGE_ACCESS_TOKEN = "your_facebook_token"
FACEBOOK_PAGE_ID = "your_facebook_page_id"
DEVTO_API_KEY = "your_devto_key"
BLOGGER_BLOG_ID = "your_blogger_blog_id"
```

## How to Add:
1. Go to https://share.streamlit.io/
2. Click on your app (tech-influencer-bot)
3. Settings → Secrets
4. Paste the content above
5. Click "Save"
