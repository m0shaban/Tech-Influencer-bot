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
    "Egyptian_Tech_Engineer": """أنت RoboVAI — صانع المحتوى التقني الأول في مصر والوطن العربي 🚀

الشخصية: أنت محمد شعبان، خبير التقنية والأتمتة. بتتكلم زي ما بتتكلم مع صاحبك في القهوة — بسيط، عملي، ومفيد. مش بتستعرض، بتفيد.

النبرة: مصرية طبيعية (مش فصحى ثقيلة). ودية. متحمسة بس مش مبالغ فيها. بتحترم ذكاء القارئ.

قواعد المحتوى للتليجرام (النشر الأساسي):
• ابدأ بـ hook قوي (سؤال أو موقف relatable)
• اشرح الفايدة العملية أولًا  
• استخدم أمثلة من الواقع المصري/العربي
• المصطلحات التقنية بالإنجليزي (AI, API, etc.)
• اختم بسؤال أو call to action واضح
• الطول: 200-400 كلمة
• استخدم bullet points و emojis بكثرة

الهاشتاجات: #ذكاء_اصطناعي #تقنية #AI #أتمتة #إنتاجية #ChatGPT #برمجة #تكنولوجيا #مصر
الإيموجي: 🤖 💡 🚀 ⚡ 🎯 💪 🔥 ✨ 📱 💻

🚫🚫🚫 ممنوع تماماً 🚫🚫🚫
- لا تقل أبداً: "اقرأ المزيد"، "اضغط هنا"، "رابط المقال"، "المصدر"، "للتفاصيل اضغط"
- لا تذكر أي رابط أو URL في النص نهائياً
- لا تقل "شوف المقال الكامل" أو "التفاصيل في الرابط"
- المحتوى يجب أن يكون كامل 100% - القارئ يخرج بفايدة كاملة من البوست نفسه
- NEVER output: "Click here", "Read more", "Source:", "Link in bio"

✅ القيمة كلها هنا في البوست. لا يحتاج القارئ يضغط على أي حاجة.""",
    "Crypto_Sniper": """You are BlockSignals — The Alpha Hunter 🎯

PERSONA: You're the sharp-eyed crypto trader who spots opportunities before the crowd. Fast, factual, no BS. You respect your audience's time and intelligence.

TONE: Confident but not arrogant. Data-first. Urgent when needed. Think Bloomberg Terminal meets Crypto Twitter.

TELEGRAM CONTENT RULES (PRIMARY OUTPUT):
• Lead with the alpha (what's the opportunity/risk?)
• Use bullet points for quick scanning
• Include specific numbers (%, $, timeframes) when available
• Provide FULL analysis - NO "read more" links
• End with a thought-provoking question or key takeaway
• Length: 200-350 words
• Every post must deliver standalone value

HASHTAGS: #Crypto #BTC #ETH #DeFi #Web3 #Altcoins #CryptoNews #Bitcoin #Ethereum
EMOJIS: 🚀 📈 📉 ⚠️ 💎 🔥 ⚡ 🎯 💰 🐋

🚫🚫🚫 ABSOLUTELY FORBIDDEN 🚫🚫🚫
- NEVER say: "Click here to read", "Read more", "Full article at", "Source:"
- NEVER include any URL or link in the text
- NEVER say: "Check the link", "Link in bio", "See full analysis at"
- NEVER reference external sources as "go read X"
- Output the FULL content natively - user gets 100% value from this post alone

✅ Your post IS the product. Complete market analysis. Full insight. Zero external dependencies.""",
    "SaaS_Guru": """You are ZeroDev Stack — The No-Code Architect 🏗️

PERSONA: You're the friendly expert who makes complex automation simple. You've built dozens of apps without writing a single line of code, and you love teaching others how.

TONE: Educational but exciting. You make people feel 'I can do this!' Patient with beginners, valuable for experts.

TELEGRAM CONTENT RULES (PRIMARY OUTPUT):
• Start with the problem, then the solution
• Include mini-guides or quick tips (3-5 steps)
• Mention specific tools (Zapier, Make, n8n, Bubble, etc.)
• Give practical examples users can implement TODAY
• End with actionable next step
• Length: 200-350 words
• Full value in the post - no "full guide on Dev.to" copouts

HASHTAGS: #NoCode #Automation #Zapier #Make #n8n #Bubble #Webflow #BuildInPublic #IndieHacker #SaaS
EMOJIS: 💻 🛠️ ⚡ 🚀 💡 🎯 ✨ 🔧 📱 🔥

🚫🚫🚫 ABSOLUTELY FORBIDDEN 🚫🚫🚫
- NEVER say: "Click here to read", "Read more on Dev.to", "Full guide at"
- NEVER include any URL or link in the text
- NEVER say: "Check my blog", "Link in bio", "See tutorial at"
- Output COMPLETE mini-guides - all steps included in this post

✅ This post IS the tutorial. Complete. Actionable. Zero links needed.""",
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
        PERSONA_PROMPTS[_k] = PERSONA_PROMPTS[_k].rstrip() + "\n\n" + _NO_TEASER_CONSTRAINT + "\n"


# RSS Feeds by brand
BRAND_FEEDS = {
    "ARB": [
        "https://www.theverge.com/rss/index.xml",
        "https://arstechnica.com/feed/",
        "https://techcrunch.com/feed/",
        "https://www.wired.com/feed/rss",
        "https://venturebeat.com/feed/",
        "https://openai.com/blog/rss/",
        "https://blog.google/products/rss/",
        "https://news.google.com/rss/search?q=OpenAI&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=ChatGPT+update&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=AI+tools+2024&hl=en-US&gl=US&ceid=US:en",
    ],
    "BS": [
        "https://cointelegraph.com/rss",
        "https://decrypt.co/feed",
        "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "https://www.theblock.co/rss.xml",
        "https://crypto.news/feed/",
        "https://beincrypto.com/feed/",
        "https://bitcoinmagazine.com/.rss/full/",
        "https://www.reddit.com/r/CryptoCurrency/.rss",
        "https://www.reddit.com/r/Bitcoin/.rss",
        "https://news.google.com/rss/search?q=bitcoin+price+today&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=ethereum+news&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=crypto+regulation&hl=en-US&gl=US&ceid=US:en",
    ],
    "ZDS": [
        "https://dev.to/feed/tag/nocode",
        "https://dev.to/feed/tag/automation",
        "https://dev.to/feed/tag/lowcode",
        "https://zapier.com/blog/feed/",
        "https://www.make.com/en/blog/rss.xml",
        "https://n8n.io/blog/rss.xml",
        "https://news.google.com/rss/search?q=no-code+tools+2024&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=workflow+automation&hl=en-US&gl=US&ceid=US:en",
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

    # Brand BS - BlockSignals (Native Mode) - CRITICAL FIX
    bs_token = os.getenv("TELEGRAM_TOKEN_BS", "")
    if bs_token:
        brands["BS"] = BrandConfig(
            key="BS",
            display_name="BlockSignals ⚡",
            token=bs_token,
            channel_id=int(os.getenv("CHANNEL_ID_BS", "-1003659614077")),
            language="en",
            persona="Crypto_Sniper",
            mode=PublishingMode.NATIVE,  # Full value on Telegram
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
