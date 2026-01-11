# ARCHITECTURE.md — RoboVAI v2.1 Ecosystem (Production Ready)

## 1. High-Level Overview

RoboVAI v2.1 is an asynchronous, multi-agent content orchestration system designed for high-volume, multi-brand publishing. It uses a **Hub-and-Spoke** content strategy where each brand has a designated "Source of Truth" (Hub) platform, and other platforms serve as spokes driving traffic back to the hub via Smart CTAs.

- **Orchestration:** Independent Worker Bots per brand (BlockSignals, ZeroDev, RoboVAI_AR).
- **Content:** 180+ High-quality RSS sources (60 per brand) processed by Llama 3.3/NVIDIA.
- **Scheduling:** Independent, timezone-aware schedules per brand with business hours awareness.
- **Publishing:** Sequential publishing engine that ensures proper flow and CTA injection.

## 2. System Diagram (Mermaid TD)

```mermaid
    subgraph AdminPlane[Admin & Control Plane]
        Master[Master Controller (Admin UI)]
    end

    subgraph Workers[Worker Bots]
        BS[BlockSignals Worker]
        ZDS[ZeroDev Stack Worker]
        ARB[RoboVAI Arabic Worker]
    end

    subgraph Engine[Core Engine]
        SP[Sequential Publisher]
        AP[Auto Publisher]
        AI[AI Processor (Llama 3.3)]
        IMG[Image Generator (OGImage)]
    end

    subgraph External[External Platforms]
        TG[Telegram]
        WEB[Blogger / Dev.to]
        SOC[Facebook / Discord]
        RSS[180+ RSS Feeds]
    end

    Master -->|Control| Workers
    Workers -->|Alerts| Master
    
    Workers -->|Trigger| AP
    AP -->|Schedule Check| Workers
    
    Workers -->|Execute| SP
    SP -->|Generate| AI
    SP -->|Visuals| IMG
    SP -->|Fetch| RSS
    
    SP -->|Step 1: Hub| WEB
    SP -->|Step 2: CTA| SOC
    SP -->|Step 3: Alert| TG
```

## 3. Brand Strategies (The "Source of Truth" Model)

Each brand acts as the primary source. External RSS feeds are consumed to generate fresh, unique content, but the audience is directed to the brand's own platforms.

| Brand | Hub (Source) | Spokes (Traffic Drivers) | Content Strategy |
|-------|--------------|--------------------------|------------------|
| **BlockSignals** | **Telegram** | Discord | **Crypto Alpha:** Breaking news and signals live on Telegram. Discord serves as a community lounge alerting members to check Telegram. |
| **ZeroDev** | **Dev.to** | Telegram | **Educational Tutorials:** Full, deep-dive articles on Dev.to. Telegram posts "Quick Tips" with a CTA to read the full code/guide on Dev.to. |
| **RoboVAI (AR)** | **Blogger** | Facebook, Telegram | **Tech Blog (Arabic):** Main articles on Blogger. Facebook and Telegram post engaging summaries/teasers with links driving traffic to the Blog. |

## 4. Core Components Deep Dive

### `worker_bot.py` — The Agent
- Represents the brand's identity.
- Manages the lifecycle of the bot.
- delegated the actual publishing task to `SequentialPublisher`.
- Reports health and errors to the Master Controller.

### `sequential_publisher.py` — The Publishing Engine
- **Responsibility:** Orchestrates the multi-step publishing process.
- **CTA Logic:** Captures the URL from the "Hub" platform and dynamically injects it into the "Spoke" platforms.
- **Source Attribution:** Ensures internal attribution (You are the source) rather than external links.
- **Delays:** Manages micro-delays (e.g., 2 mins) between platforms to behave naturally.

### `auto_publisher.py` — The Heartbeat
- **Smart Scheduling:** Checks `posts_per_day` and `min_interval_minutes` defined in `config.json`.
- **Time Awareness:** Respects brand-specific timezones (e.g., Cairo for RoboVAI, NY for ZeroDev) and business hours.
- **Persistence:** Saves state to `autopublisher_status.json` to survive restarts.

### `feeds_config.py` & `config.json` — The Brain
- **Feeds:** Holds the curated list of 180 RSS sources.
- **Prompts:** Contains the "System Prompts" that define the unique voice and "You are the Source" rule for each brand.
- **Routing:** Defines the `PUBLISHING_ORDER` (Hub → Spoke 1 → Spoke 2).

## 5. Data Flow Pipeline (The Journey of a Post)

1.  **Trigger:** `auto_publisher` wakes up the Worker based on the schedule.
2.  **Fetch:** Worker fetches fresh news from the brand's 60 RSS feeds.
3.  **Analysis:** AI selects the most relevant/high-impact story.
4.  **Hub Generation:** Content is generated for the Hub platform (e.g., Blogger for RoboVAI).
5.  **Hub Publish:** Content is published. **URL is captured.**
6.  **Spoke Generation:** Content is generated for Spoke platforms (e.g., Facebook).
7.  **CTA Injection:** The Hub URL is injected into the Spoke content (e.g., "Read full article: [Blogger URL]").
8.  **Spoke Publish:** Spoke content is published.
9.  **Report:** Success stats sent to Master Admin.

## 6. File Topology

```
f:\robobot\
├── launcher.py              # Entry point
├── worker_bot.py            # Brand Agent Logic
├── sequential_publisher.py  # Multi-platform & CTA Engine
├── auto_publisher.py        # Scheduling Logic
├── feeds_config.py          # RSS Feeds & Publishing Rules
├── config.json              # Dynamic Configuration
├── image_manager.py         # Image Generation (Arabic support)
├── master_controller.py     # Admin UI
└── brands_config.py         # Brand Definitions
```

## 7. Production Readiness Checklist

- [x] **Independence:** Brands run as isolated agents.
- [x] **Scheduling:** Per-brand timezones and intervals working.
- [x] **Sources:** 180 curated feeds ensuring constant stream of news.
- [x] **Attribution:** Internal linking strategy implemented.
- [x] **Reliability:** Error trapping and Admin alerting system active.
