# MAINTENANCE.md — RoboVAI v2.0 Operator Manual

## Overview

RoboVAI v2.0 runs a Hub-and-Spoke architecture: one Master Controller (admin-only) plus multiple Worker Bots (one per brand). The Master handles dashboards and alerts; Workers handle content generation and publishing.

```mermaid
flowchart LR
    Admin[[Admin User]] -->|Commands| Master((Master Controller))
    Master -->|Status/Alerts| Admin
    Master -->|Start/Stop| Workers{{Workers (ARB/BS/ZDS)}}
    Workers -->|Native Posts| TelegramChannels
    Workers -->|Alerts| Master
```

## System Health Check

- Use the Master Bot dashboard (`/start`) to view:
  - Workers online count.
  - Per-brand panels (mode, feeds, platforms, schedule).
  - Force fetch, pause/resume actions.
- If a worker is down, Master shows it as offline (button state) and you will see an alert in DM if it crashed.

## Troubleshooting Guide

### Scenario A: BlockSignals bot is silent

- Check Master alerts in your admin DM for crashes/tracebacks.
- Check console logs for `[BS]` lines.
- Verify API keys/quotas: GROQ_API_KEY\*, DISCORD webhook, TELEGRAM_TOKEN_BS.
- Run a manual force fetch from the BS worker chat (`⚡ Force Fetch`).
- If scraping is empty, inspect feeds in `brands_config.py` and network connectivity.

### Scenario B: Master Bot not responding

- Ensure no other processes are polling the same MASTER token.
- Restart the service: stop any `python` process running the bots, then `python launcher.py --async` (or the service unit if deployed).
- Check console for startup errors; Master will also alert on startup failure when possible.

### Scenario C: Content Quality is low

- Edit the brand persona prompt in `brands_config.py` (see `PERSONA_PROMPTS`).
- Keep the strict “NO links / full native content” lines intact.
- After changes, restart the system to reload prompts.

## Logs & Alerts

- Console/stdout: each worker prefixes logs with `[BRAND_KEY]`; Master with `[MASTER]` or `[LAUNCHER]`.
- Master Alerts (DM to ADMIN_USER_ID): triggered on worker crash/timeouts with traceback snippet.
- Tracebacks: read from bottom-up; first lines show the failing call; network errors often come from `telegram.error.*`.

## Backup Strategy

- Must-backup files:
  - `.env` (all tokens/keys/channel IDs).
  - `database.sqlite` (if present for persistence/jobs).
  - `brands_config.py` (persona prompts, feeds, schedules, modes).
  - Any generated images/cache you care about.
- Optional: `ARCHITECTURE.md`, `MAINTENANCE.md`, `SCALING_GUIDE.md` for ops knowledge.
- Schedule: daily off-box copy or versioned cloud secret manager for `.env`.

## Operational Checklist (daily/weekly)

- Daily: glance at Master dashboard; ensure workers show online; skim alerts.
- Weekly: review content quality; tweak prompts if needed; rotate GROQ/NVIDIA keys if nearing quota.
- Monthly: backup `.env` and config; update feeds for freshness.

## Restart Procedures

- Soft restart (dev): `Ctrl+C` then `python launcher.py --async`.
- Kill stray processes on Windows PowerShell:
  - List: `Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" | Select ProcessId,CommandLine`
  - Kill: `Stop-Process -Id <PID> -Force`
- Ensure only one instance per bot token is polling to avoid `Conflict: terminated by other getUpdates request`.
