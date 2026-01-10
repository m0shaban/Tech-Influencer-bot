# ARCHITECTURE.md — RoboVAI v2.0 Ecosystem

## 1. High-Level Overview (The Big Picture)

RoboVAI v2.0 is an asynchronous, multi-agent content orchestration system using a **Hub-and-Spoke** topology. Responsibilities are strictly separated:

- **Master Controller (Orchestrator):** Admin UI, health monitoring, control commands, alert fan-out. It never posts content.
- **Brand Workers (Execution Agents):** One per brand (BlockSignals, RoboVAI Arabic, ZeroDev Stack). Each runs its own bot token, persona prompt, feeds, schedule, and publishing mode.

## 2. System Diagram (Mermaid TD)

```mermaid

    subgraph AdminPlane[Admin & Control Plane]
        Master[Master Controller (Admin UI)]
    end

    subgraph Workers[Worker Bots]
        BS[BlockSignals Worker]
        ARB[RoboVAI Arabic Worker]
        ZDS[ZeroDev Stack Worker]
    end

    subgraph External[External Services]
        TG[Telegram API]
        AI[AI Models (Groq / NVIDIA)]
        FEEDS[Data Sources / RSS / Scrapers]
    end

    Master -->|Commands / Force / Status| BS
    Master -->|Commands / Force / Status| ARB
    Master -->|Commands / Force / Status| ZDS

    BS -->|Alerts / Logs| Master
    ARB -->|Alerts / Logs| Master
    ZDS -->|Alerts / Logs| Master

    BS -->|Publish| TG
    ARB -->|Publish| TG
    ZDS -->|Publish| TG

    BS -->|Fetch| FEEDS
    ARB -->|Fetch| FEEDS
    ZDS -->|Fetch| FEEDS

    BS -->|LLM Calls| AI
    ARB -->|LLM Calls| AI
    ZDS -->|LLM Calls| AI
```

## 3. Core Components Deep Dive

### `launcher.py` — Entry Point & Event Loop

- Boots the ecosystem using `asyncio.gather` to run Master + all Workers concurrently.
- Loads environment (`dotenv`) before env checks.
- Offers dual modes: async (preferred) and threading fallback.
- Guards against multi-instance token conflicts by ensuring single orchestrated startup.

### `master_controller.py` — Admin's Cockpit

- Exposes admin commands (`/start`, `/brands`, `/force`, `/status`) without blocking worker execution.
- Renders inline dashboards for per-brand control (force fetch, stats, feeds, pause/resume).
- Acts as observer: receives crash alerts from workers and surfaces them to ADMIN_USER_ID.

### `worker_bot.py` — Generic Worker Class (instantiated per brand)

- **Scheduling:** Runs periodic/scheduled fetch-and-publish cycles (and on-demand force fetch).
- **Content Generation:** Calls AI with brand-specific persona prompt; enforces native-value delivery (no outbound links unless funnel mode demands external platforms).
- **Publishing Logic:**
  - **Native Mode:** Full value on Telegram.
  - **Funnel Mode:** TG teaser + external platforms (e.g., Blogger/Facebook).
  - **Dual Mode:** Native TG plus long-form on another platform (e.g., Dev.to).
- **Resilience:** Catches exceptions, reports alerts to Master (DM to admin), and logs locally with brand prefix.

### `brands_config.py` — Configuration Singleton

- Central source of truth for:
  - Tokens, channel IDs, schedules, feeds, platforms per brand.
  - Persona prompts (strict “no external links” for native value delivery).
  - Publishing mode enum (NATIVE/FUNNEL/DUAL).
- Acts like a factory input: workers are created from this config mapping.

## 4. Data Flow Pipeline (The Journey of a Post)

1. **Trigger:** Scheduler or force command wakes the Worker.
2. **Sourcing:** Worker pulls a fresh item from RSS/feeds (`feed_manager`).
3. **Processing:** Worker injects the brand persona prompt from `brands_config.py`.
4. **Generation:** LLM (Groq/NVIDIA) produces platform-specific content (native TG or long-form for funnel/dual).
5. **Publishing:** Worker posts to the Telegram channel (and optional external platforms per mode).
6. **Reporting:** Success/failure logged; on errors, the Worker alerts the Master (admin DM) with traceback.

## 5. Tech Stack & Design Patterns

- **Tech Stack:** Python 3.11+, asyncio, Telegram client (python-telegram-bot; aiogram 3.x compatible design), Groq/NVIDIA LLM APIs, optional SQLite for persistence.
- **Design Patterns:**
  - **Factory Pattern:** `launcher.py` instantiates workers from `brands_config` mappings.
  - **Observer Pattern:** Workers notify Master of crashes/errors; Master monitors and commands workers.
  - **Singleton:** `brands_config.py` acts as the singular configuration source for all agents.

## File Topology (Key Files)

```
launcher.py          # Async entrypoint, orchestrates master + workers
master_controller.py # Admin UI, dashboards, commands, observer
worker_bot.py        # Generic worker implementation per brand
brands_config.py     # Brand registry: tokens, prompts, feeds, modes
feed_manager.py      # RSS/HTML fetch and dedup
ai_processor.py      # LLM invocation, parsing, prompt enforcement
```

## Operating Modes (per Brand)

- **NATIVE:** Full value inside Telegram (BlockSignals).
- **FUNNEL:** TG teaser driving to external platforms (RoboVAI Arabic).
- **DUAL:** Native TG plus long-form external (ZeroDev Stack).

## Concurrency Model

- Preferred: `python launcher.py --async` → `asyncio.gather` runs Master + all Workers.
- Fallback: threading mode for environments where async polling is constrained.

## Reliability & Alerts

- Workers wrap critical paths with exception handling; on failure, they DM admin via Master token.
- Strict single-instance per bot token to avoid `getUpdates` conflicts.
  FACEBOOK_PAGE_ACCESS_TOKEN_ARB=...
