# 🚀 Deployment Cheat Sheet

## 1. Render Start Command
**Command:** `python launcher.py --async`
- This runs the Master Controller, All Worker Bots, and the Auto-Scheduler in a single process.
- It also starts a minimal HTTP server for Render Health Checks.

## 2. Environment Variables
Ensure these are set in Render/Heroku Dashboard:
- `TELEGRAM_TOKEN`: (Master Bot Token)
- `ADMIN_USER_ID`: (Your Telegram ID)
- `GROQ_API_KEY`: (For AI Generation)
- Brand Tokens (e.g., `BS_BOT_TOKEN`, `ARB_BOT_TOKEN`)

## 3. Worker Configuration
- Workers automatically register themselves.
- If a brand has no token in `.env`, it will be skipped (safe failure).

## 4. Organizing Files
Run the included script to clean up the folder:
```bash
python organize_workspace.py
```
*Note: This moves documentation and helper scripts. Core bot files are kept in root to ensure stability.*
