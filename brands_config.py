"""
Brands Configuration Module - Hub-and-Spoke Architecture
=========================================================

This module defines the configuration for the Multi-Agent System:
- Master Controller (Admin Bot) - Management only, no content posting
- Brand Workers (Content Bots) - Independent content generation and posting

Each brand is a self-contained agent with its own:
- Telegram Token
- Channel ID
- Persona/System Prompt
- Publishing Mode (Native, Funnel, Dual)
- RSS Feeds
"""

import os
from typing import Dict, Any, Optional, Literal
from dataclasses import dataclass, field
from enum import Enum

from dotenv import load_dotenv

load_dotenv()


class PublishingMode(Enum):
    """
    Publishing modes for brand content:
    - NATIVE: Full value in Telegram, no external links needed
    - FUNNEL: Telegram acts as teaser to drive traffic to external platforms
    - DUAL: Both native content AND external platform publishing
    """

    NATIVE = "native"  # Full content on Telegram (BlockSignals style)
    FUNNEL = "funnel"  # Drive traffic to Blogger/Facebook
    DUAL = "dual"  # Both native TG content + external publishing


@dataclass
class BrandConfig:
    """Configuration for a single brand agent."""

    key: str
    display_name: str
    token: str
    channel_id: int
    language: str
    persona: str
    mode: PublishingMode
    system_prompt: str
    feeds: list[str] = field(default_factory=list)
    platforms: dict[str, dict] = field(default_factory=dict)
    schedule: dict = field(default_factory=dict)
    cta_url: str = ""  # New: custom CTA link (Blog, Landing Page, etc.)

    # Platform-specific credentials (suffix-based)
    account_suffix: str = ""

    def get_env(self, key: str, default: str = "") -> str:
        """Get environment variable with brand suffix."""
        # Try brand-specific first
        val = os.getenv(f"{key}_{self.account_suffix}", "")
        if val:
            return val
        # Fallback to generic
        return os.getenv(key, default)


# ============================================================
# MASTER CONTROLLER CONFIGURATION
# ============================================================

MASTER_BOT_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0") or "0")


# ============================================================
# BRAND WORKER CONFIGURATIONS
# ============================================================

# System prompts for each persona
PERSONA_PROMPTS = {
    "Egyptian_Tech_Engineer": """أنت محمد شعبان (RoboVAI) — رائد أعمال تقني وصانع محتوى مؤثر في الشرق الأوسط 🇪🇬🚀

🔵 **الشخصية**:
أنت لست مجرد بوت، أنت "المهندس الشاطر" اللي بيفهم في الكواليس. خبير في الذكاء الاصطناعي والأتمتة (Automation) والبيزنس. أسلوبك "حريف" بس "ابن بلد". بتشرح التكنولوجيا المعقدة بطريقة تخلي أي حد يفهم ويتحمس ينفذ.

🔵 **النبرة (Tone)**:
• مصرية حديثة (Modern Egyptian): "يا جماعة"، "ده جيم سينجر"، "تخيل بقى".
• حماسية وذكية: صوتك فيه طاقة الإنجاز.
• عملية جداً: "خلاصة الكلام"، "من الآخر".

🔵 **الهيكل المطلوب للبوست (Telegram Native)**:
1. **The Hook (الخاطفة)**: ابدأ بجملة قوية أو سؤال صادم يخص الـ AI أو التكنولوجيا.
2. **The Meat (الزتونة)**: اشرح الخبر أو الأداة بوضوح. ركز على "إزاي ده هيفيدني كقارئ؟" وتجاهل تفاصيل الشركات المملة.
3. **The Twist (اللمسة الشخصية)**: ضيف رأيك كخبير. هل دي فرصة؟ هل ده تهديد؟
4. **The CTA (الإجراء)**: شجعهم يتابعوا القناة أو يجربوا الأداة.

🚫 **ممنوعات قاتلة**:
• لا تستخدم لغة البوتات ("في عالم التكنولوجيا المتسارع...").
• لا تضع مقدمات مملة. ادخل في الموضوع فوراً.
• لا تضع روابط خارجية في النص. (الروابط مكانها في الأزرار فقط).

✅ **هدف البوست**: بناء الثقة. القارئ لازم يحس إن "محمد شعبان" هو مصدره الأول للمعلومة التقنية.""",
    "Crypto_Sniper": """You are BlockSignals — The Apex Predator of Crypto Trading 🎯🐋

🔵 **PERSONA**:
You are a veteran trader who has seen regular folks get wrecked and whales get rich. You are here to level the playing field. You don't report news; you interpret **signals**. You are sharp, direct, and focused on ROI.

🔵 **TONE**:
• High Energy & Urgency: "Wake up," "Huge move," "Alert."
• Analytical but Plain English: Explain *why* price is moving, not just that it moved.
• Alpha-First: Lead with the opportunity or the risk.

🔵 **POST STRUCTURE (Telegram Native)**:
1. **The Signal (Headline)**: E.g., "BTC just broke $70k resistance!" or "SOL Ecosystem Alert 🚨"
2. **The Analysis (The Why)**: Quick bullet points on on-chain data, sentiment, or macro news.
3. **The Play (Actionable)**: What should a smart trader watch? (Resistance levels, support zones).
4. **The Verdict**: Bullish 🐂 or Bearish 🐻?

🚫 **DANGER ZONE**:
• NO financial advice disclaimers that sound robotic.
• NO links in the body text.
• NO "Read more on Coindesk". You ARE the source.

✅ **GOAL**: The user feels they have an "unfair advantage" by following you.""",
    "SaaS_Guru": """You are ZeroDev Stack — The No-Code/SaaS Architect 🏗️💡

🔵 **PERSONA**:
You are the builder who launches startups in a weekend. You believe code is optional, but logic is mandatory. You love tools like Bubble, Make, Supabase, and AI agents. You are a teacher and a builder.

🔵 **TONE**:
• Empowering & Educational: "You can build this too."
• Step-by-Step Logic: Clear, structured thinking.
• Indie Hacker Vibes: Focused on shipping, MVP, and revenue.

🔵 **POST STRUCTURE (Telegram Native)**:
1. **The Problem**: "Struggling to manage leads?" or "Want to clone Instagram?"
2. **The Solution (The Stack)**: Introduce the tool/workflow.
3. **The 'How-To' (Mini-Guide)**: 3-5 bullet points explaining the setup.
4. **The Result**: "Saved 10 hours/week" or "Launched in 24 hours".

🚫 **FORBIDDEN**:
• Do NOT act like a news reporter. Be a **User/Reviewer**.
• NO generic "This tool is great". Say EXACTLY what it solves.
• NO links in body.

✅ **GOAL**: Users save your post to their "Saved Messages" because it's a valuable tutorial/resource.""",
}


# Global negative constraint (must be present in all personas)
_NO_TEASER_CONSTRAINT = (
    "CRITICAL INSTRUCTION: You are FORBIDDEN from writing 'Click the link to read more' "
    "or 'Read the full article here'. You MUST write the FULL content/tutorial/news summary "
    "directly in the response. The output must be valuable on its own. Do not act as a gateway."
)

# Inject the constraint into each persona prompt (safely, without changing tone)
for _k in list(PERSONA_PROMPTS.keys()):
    if _NO_TEASER_CONSTRAINT not in PERSONA_PROMPTS[_k]:
        PERSONA_PROMPTS[_k] = (
            PERSONA_PROMPTS[_k].rstrip() + "\n\n" + _NO_TEASER_CONSTRAINT + "\n"
        )


# RSS Feeds by brand
BRAND_FEEDS = {
    "ARB": [
        "https://www.theverge.com/rss/index.xml",
        "https://arstechnica.com/feed/",
        "https://techcrunch.com/feed/",
        "https://www.wired.com/feed/rss",
        "https://venturebeat.com/feed/",
        "https://openai.com/blog/rss/",
        # Removed generic Google Search feeds (low quality images)
    ],
    "BS": [
        "https://cointelegraph.com/rss",
        "https://decrypt.co/feed",
        "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "https://www.theblock.co/rss.xml",
        # Removed generic Reddit and Search feeds
    ],
    "ZDS": [
        "https://zapier.com/blog/feed/",
        "https://www.make.com/en/blog/rss.xml",
        "https://n8n.io/blog/rss.xml",
        # Kept Dev.to as it is relevant for this niche
        "https://dev.to/feed/tag/nocode",
        "https://dev.to/feed/tag/automation",
    ],
}


def get_brand_configs() -> Dict[str, BrandConfig]:
    """
    Load all brand configurations from environment variables.
    Returns a dictionary of brand_key -> BrandConfig.
    """
    brands = {}

    # Brand ARB - RoboVAI Arabic (Funnel Mode)
    arb_token = os.getenv("TELEGRAM_TOKEN_ARB", "")
    if arb_token:
        brands["ARB"] = BrandConfig(
            key="ARB",
            display_name="RoboVAI 🤖 العربي",
            token=arb_token,
            channel_id=int(os.getenv("CHANNEL_ID_ARB", "-1003547538277")),
            language="ar",
            persona="Egyptian_Tech_Engineer",
            mode=PublishingMode.FUNNEL,
            system_prompt=PERSONA_PROMPTS["Egyptian_Tech_Engineer"],
            feeds=BRAND_FEEDS["ARB"],
            account_suffix="ARB",
            cta_url="https://robovai.blogspot.com",  # Default CTA to Blog
            platforms={
                "blogger": {"enabled": True, "priority": 1},
                "facebook": {"enabled": True, "priority": 2},
                "telegram": {"enabled": True, "priority": 3},
            },
            schedule={
                "timezone": "Africa/Cairo",
                "wake_hour": 9,
                "sleep_hour": 23,
                "posts_per_day": 10,
            },
        )

    # Brand BS - BlockSignals (Native Mode)
    bs_token = os.getenv("TELEGRAM_TOKEN_BS", "")
    if bs_token:
        brands["BS"] = BrandConfig(
            key="BS",
            display_name="BlockSignals ⚡",
            token=bs_token,
            channel_id=int(os.getenv("CHANNEL_ID_BS", "-1003659614077")),
            language="en",
            persona="Crypto_Sniper",
            mode=PublishingMode.NATIVE,
            system_prompt=PERSONA_PROMPTS["Crypto_Sniper"],
            feeds=BRAND_FEEDS["BS"],
            account_suffix="BS",
            platforms={
                "telegram": {"enabled": True, "priority": 1},
                "discord": {"enabled": True, "priority": 2},
            },
            schedule={
                "timezone": "America/New_York",
                "wake_hour": 8,
                "sleep_hour": 23,
                "posts_per_day": 8,
            },
        )

    # Brand ZDS - ZeroDev Stack (Dual Mode)
    zds_token = os.getenv("TELEGRAM_TOKEN_ZDS", "")
    if zds_token:
        brands["ZDS"] = BrandConfig(
            key="ZDS",
            display_name="ZeroDev Stack 💻",
            token=zds_token,
            channel_id=int(os.getenv("CHANNEL_ID_ZDS", "-1003629994158")),
            language="en",
            persona="SaaS_Guru",
            mode=PublishingMode.DUAL,  # Both native TG + Dev.to
            system_prompt=PERSONA_PROMPTS["SaaS_Guru"],
            feeds=BRAND_FEEDS["ZDS"],
            account_suffix="ZDS",
            platforms={
                "devto": {"enabled": True, "priority": 1},
                "telegram": {"enabled": True, "priority": 2},
            },
            schedule={
                "timezone": "America/New_York",
                "wake_hour": 9,
                "sleep_hour": 22,
                "posts_per_day": 6,
            },
        )

    return brands


def get_brand_by_key(key: str) -> Optional[BrandConfig]:
    """Get a specific brand configuration by its key."""
    brands = get_brand_configs()
    return brands.get(key.upper())


def get_all_brand_keys() -> list[str]:
    """Get list of all configured brand keys."""
    return list(get_brand_configs().keys())


# Legacy compatibility - map old config.json brand names to new keys
LEGACY_BRAND_MAP = {
    "robovai_ar": "ARB",
    "blocksignals": "BS",
    "zerodev": "ZDS",
}


def legacy_to_new_key(legacy_key: str) -> str:
    """Convert legacy brand key to new format."""
    return LEGACY_BRAND_MAP.get(legacy_key.lower(), legacy_key.upper())


def new_to_legacy_key(new_key: str) -> str:
    """Convert new brand key to legacy format."""
    reverse_map = {v: k for k, v in LEGACY_BRAND_MAP.items()}
    return reverse_map.get(new_key.upper(), new_key.lower())
