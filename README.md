# RoboVAI — Egyptian Chic AI Publishing Engine

RoboVAI is a Telegram publishing bot that curates multi-source tech/AI/automation content, rewrites it in a friendly "Egyptian Youth Chic" style, and posts with visuals and optional polls. It includes a Streamlit Command Center for control, plus a health checker for pre-deploy diagnostics.

## Highlights

- Multi-source RSS: Rotates across 40+ feeds with shuffle to avoid bias.
- Smart fetching: Stops at the first unseen post and persists to `data/seen_posts.json`.
- Visuals: Extracts images from RSS (media/enclosure/HTML) and posts as photo when available.
- AI rewrites (Groq): Fast JSON-mode captions + polls via `llama3-70b-8192`.
- Engagement: Optional polls right after publishing.
- Jittered scheduler: Random 1–15 min delay per cycle, Cairo time window (9:00–23:00).
- Command Center: Streamlit dashboard for status, prompt edits, feeds, moderation, and broadcasts.
- Health check: One-shot system diagnostician with colored PASS/FAIL.

## Architecture

- Core
  - [main.py](main.py): Bot app, jittered scheduler, Cairo time window, publish flow.
  - [feed_manager.py](feed_manager.py): Fetch latest post across feeds; dedupe; image extraction.
  - [feeds_config.py](feeds_config.py): List of RSS sources (edit as needed).
  - [ai_processor.py](ai_processor.py): Groq/OpenAI client; JSON captions + poll data.
  - [data/seen_posts.json](data/seen_posts.json): Local persistence of seen links.
- Ops & Control
  - [dashboard.py](dashboard.py): Streamlit Command Center with config locking.
  - [config.json](config.json): Settings edited by dashboard.
  - [health_check.py](health_check.py): Environment, files, Telegram, Groq, RSS diagnostics.
- Setup
  - [requirements.txt](requirements.txt): Python dependencies.
  - [.env.example](.env.example): Environment variable template.

## Requirements

- Python 3.10+
- Telegram Bot token and channel/group IDs
- Groq Cloud API key (for OpenAI client using Groq)

## Quick Start

```bash
# Optional: create and activate a virtualenv
python -m venv .venv
. .venv/Scripts/Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env
# Edit .env and set: TELEGRAM_TOKEN, GROQ_API_KEY, CHANNEL_ID, GROUP_ID, DASHBOARD_PASSWORD (optional)

# Run health check
python health_check.py

# Start the bot
python main.py

# Launch the Command Center (new terminal)
streamlit run dashboard.py
```

## Configuration

- `.env`
  - `TELEGRAM_TOKEN`: Bot token
  - `CHANNEL_ID`: Target channel (e.g., @yourchannel or numeric ID)
  - `GROUP_ID`: Target group ID (optional)
  - `GROQ_API_KEY`: Groq API key
  - `DASHBOARD_PASSWORD`: Protects the dashboard (optional)
- `config.json` (edited by the dashboard)
  - `status`: `active` or `paused`
  - `force_fetch`: Boolean flag to signal an immediate cycle
  - `system_prompt`: Persona text (dashboard-managed)
  - `feeds`: Custom feeds list (add/remove in dashboard)
  - `welcome_message`, `banned_words`, `broadcast_target`

## Publishing Flow

1. Scheduler sleeps randomly (1–15 minutes), then checks Cairo time window.
2. Fetches across shuffled feeds and stops at the first unseen post.
3. AI (Groq) returns JSON: `caption`, `has_poll`, `poll_question`, `poll_options`.
4. If an image is present, posts as photo with caption; otherwise text.
5. If `has_poll` is true, sends a poll immediately after.

## Dashboard Features

- Status toggle, force fetch flag, live log tail.
- Edit persona prompt, one-click Magic Post for a URL.
- View/add/remove feeds.
- Welcome message & blacklist management; direct broadcasts to channel/group.

## Troubleshooting

- Health check: run [health_check.py](health_check.py) and fix any FAIL items.
- Telegram: ensure `TELEGRAM_TOKEN` and target IDs are correct and bot has posting rights.
- Groq: confirm `GROQ_API_KEY` and model availability; the health check prints response time.
- Images: some feeds won’t provide media; bot falls back to text posting.
- Time window: posts only between 09:00–23:00 Africa/Cairo.

## Notes

- Dashboard writes to `config.json`. Wire your bot logic to consume flags like `status`/`force_fetch` as needed.
- Keep `feeds_config.py` updated with sources relevant to your audience.

—
Product name: RoboVAI
