"""
RSS Feeds & Publishing Configuration per Brand

🎯 DESIGN PHILOSOPHY:
- Each brand = unique content creator personality
- Publishing order optimized for CTA flow (long-form first → social with links)
- Minimal delays for faster publishing cycles
- Global trendy sources for all brands (especially robovai_ar)
"""

from typing import List, Dict, Any
import random


# ═══════════════════════════════════════════════════════════════════════════════
# 📡 BRAND RSS FEEDS — Trendy, Global, High-Quality Sources
# ═══════════════════════════════════════════════════════════════════════════════

BRAND_FEEDS = {
    "blocksignals": [
        # 🏆 Tier 1: Breaking News
        "https://cointelegraph.com/rss",
        "https://decrypt.co/feed",
        "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "https://www.theblock.co/rss.xml",
        # 🥈 Tier 2: Analysis & Deep Dives
        "https://crypto.news/feed/",
        "https://beincrypto.com/feed/",
        "https://bitcoinmagazine.com/.rss/full/",
        "https://cryptoslate.com/feed/",
        # 🏢 Official Sources
        "https://blog.kraken.com/feed",
        "https://blog.coinbase.com/feed",
        "https://blog.chain.link/rss/",
        "https://blog.ethereum.org/feed.xml",
        # 🌐 Community & Trends
        "https://www.reddit.com/r/CryptoCurrency/.rss",
        "https://www.reddit.com/r/Bitcoin/.rss",
        "https://www.reddit.com/r/ethereum/.rss",
        # 📰 Google News (Trending)
        "https://news.google.com/rss/search?q=bitcoin+price&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=ethereum+news&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=crypto+regulation+SEC&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=defi+tvl&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=bitcoin+ETF+approval&hl=en-US&gl=US&ceid=US:en",
    ],
    "zerodev": [
        # 🛠️ No-Code/Low-Code
        "https://dev.to/feed/tag/nocode",
        "https://dev.to/feed/tag/automation",
        "https://dev.to/feed/tag/lowcode",
        "https://dev.to/feed/tag/zapier",
        # 🚀 Product Launches
        "https://www.producthunt.com/feed",
        # 📚 Tool Blogs
        "https://zapier.com/blog/feed/",
        "https://webflow.com/blog/rss",
        "https://www.notion.so/blog/rss",
        "https://ifttt.com/blog/feed",
        # 🔧 Automation Platforms
        "https://www.make.com/en/blog/rss.xml",
        "https://n8n.io/blog/rss.xml",
        # 📰 Trending Topics
        "https://news.google.com/rss/search?q=no-code+tools&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=zapier+make+automation&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=workflow+automation+AI&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=airtable+notion&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=bubble+webflow&hl=en-US&gl=US&ceid=US:en",
    ],
    "robovai_ar": [
        # ════════════════════════════════════════════════════════════════════
        # 🌍 GLOBAL TECH NEWS — Top English Sources (AI will translate to Arabic)
        # ════════════════════════════════════════════════════════════════════
        # 🏆 Tier 1: Major Tech Publications
        "https://www.theverge.com/rss/index.xml",
        "https://arstechnica.com/feed/",
        "https://www.wired.com/feed/rss",
        "https://techcrunch.com/feed/",
        "https://mashable.com/feeds/rss/all",
        "https://www.engadget.com/rss.xml",
        "https://thenextweb.com/feed/",
        "https://venturebeat.com/feed/",
        # 📱 Apple & Google Ecosystem
        "https://9to5mac.com/feed/",
        "https://9to5google.com/feed/",
        "https://www.androidauthority.com/feed/",
        # 🤖 AI & ML Specific
        "https://openai.com/blog/rss/",
        "https://blog.google/products/rss/",
        "https://www.anthropic.com/news/rss",
        "https://stability.ai/blog?format=rss",
        # 💻 Developer & Enterprise
        "https://www.zdnet.com/news/rss.xml",
        "https://www.cnet.com/rss/news/",
        "https://www.infoworld.com/index.rss",
        # 🌐 Reddit Communities (Trending Discussions)
        "https://www.reddit.com/r/artificial/.rss",
        "https://www.reddit.com/r/ChatGPT/.rss",
        "https://www.reddit.com/r/technology/.rss",
        "https://www.reddit.com/r/MachineLearning/.rss",
        "https://www.reddit.com/r/singularity/.rss",
        # 📰 Google News — HOT TRENDING TOPICS (English)
        "https://news.google.com/rss/search?q=OpenAI+GPT&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=ChatGPT+update&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=Google+Gemini+AI&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=Claude+AI+Anthropic&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=AI+tools+productivity&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=Apple+AI+features&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=Microsoft+Copilot&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=Midjourney+DALL-E&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=Sora+AI+video&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=tech+startup+funding&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=automation+business&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=no-code+low-code&hl=en-US&gl=US&ceid=US:en",
    ],
}


# ═══════════════════════════════════════════════════════════════════════════════
# 📤 PUBLISHING ORDER — Optimized for CTA Flow
# ═══════════════════════════════════════════════════════════════════════════════
#
# STRATEGY:
# 1. Long-form content FIRST (Blog/Dev.to) → Gets URL
# 2. Social platforms SECOND → Can include blog link as CTA
# 3. Minimal delays (2 min max) for fast publishing cycles
#

PUBLISHING_ORDER = {
    "blocksignals": [
        # Telegram first (fast alerts), Discord follows with discussion invite
        {"platform": "telegram", "delay_minutes": 0, "enable_cta": False},
        {"platform": "discord", "delay_minutes": 2, "enable_cta": True},
    ],
    "zerodev": [
        # Dev.to first (gets article URL), Telegram follows with link
        {"platform": "devto", "delay_minutes": 0, "enable_cta": False},
        {"platform": "telegram", "delay_minutes": 2, "enable_cta": True},
    ],
    "robovai_ar": [
        # Blogger first (gets article URL), then social with links
        {"platform": "blogger", "delay_minutes": 0, "enable_cta": False},
        {"platform": "facebook", "delay_minutes": 2, "enable_cta": True},
        {"platform": "telegram", "delay_minutes": 2, "enable_cta": True},
    ],
}


# ═══════════════════════════════════════════════════════════════════════════════
# 🔗 CTA TEMPLATES — Cross-Platform Promotion
# ═══════════════════════════════════════════════════════════════════════════════

CTA_TEMPLATES = {
    "blocksignals": {
        "telegram": "",  # First platform, no CTA needed
        "discord": "\n\n⚡ **Join our Telegram** for instant alerts: {telegram_url}\n\n#Crypto #BTC #ETH #DeFi #Web3",
    },
    "zerodev": {
        "devto": "",  # First platform, no CTA needed
        "telegram": "\n\n📖 **Full tutorial on Dev.to**: {devto_url}\n\n#NoCode #Automation #Zapier #Make",
    },
    "robovai_ar": {
        "blogger": "",  # First platform, no CTA needed
        "facebook": "\n\n📖 **اقرأ المقال كامل**: {blogger_url}\n\n#ذكاء_اصطناعي #تقنية #AI #ChatGPT",
        "telegram": "\n\n📖 **المقال الكامل**: {blogger_url}\n💬 **ناقش معانا**: {facebook_url}\n\n#AI #تقنية #أتمتة",
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# 🏷️ HASHTAG SETS — Platform-Specific
# ═══════════════════════════════════════════════════════════════════════════════

HASHTAG_SETS = {
    "blocksignals": {
        "default": ["#Crypto", "#BTC", "#ETH", "#DeFi", "#Web3", "#CryptoNews"],
        "bitcoin": ["#Bitcoin", "#BTC", "#HODL", "#Cryptocurrency", "#BTCPrice"],
        "ethereum": ["#Ethereum", "#ETH", "#DeFi", "#SmartContracts", "#Web3"],
        "altcoins": ["#Altcoins", "#CryptoGems", "#100x", "#NewListings"],
        "regulation": ["#CryptoRegulation", "#SEC", "#CryptoLaw", "#Compliance"],
    },
    "zerodev": {
        "default": [
            "#NoCode",
            "#Automation",
            "#LowCode",
            "#BuildInPublic",
            "#IndieHacker",
        ],
        "zapier": ["#Zapier", "#Automation", "#Workflow", "#Productivity"],
        "make": ["#Make", "#Integromat", "#Automation", "#NoCode"],
        "bubble": ["#Bubble", "#NoCode", "#WebApp", "#StartupTools"],
        "ai": ["#AITools", "#AIAutomation", "#NoCodeAI", "#FutureOfWork"],
    },
    "robovai_ar": {
        "default": ["#ذكاء_اصطناعي", "#تقنية", "#AI", "#أتمتة", "#مصر"],
        "chatgpt": ["#ChatGPT", "#OpenAI", "#ذكاء_اصطناعي", "#AIChat"],
        "tools": ["#أدوات_إنتاجية", "#تطبيقات", "#تقنية", "#Productivity"],
        "business": ["#ريادة_أعمال", "#شركات_ناشئة", "#تحول_رقمي", "#Startup"],
        "arabic": ["#تقنية_عربي", "#محتوى_عربي", "#مصر", "#السعودية", "#الإمارات"],
    },
}


def get_hashtags(brand_name: str, category: str = "default") -> List[str]:
    """Get hashtags for brand and category."""
    brand_tags = HASHTAG_SETS.get(brand_name, {})
    return brand_tags.get(category, brand_tags.get("default", []))


# ═══════════════════════════════════════════════════════════════════════════════
# 🔄 CROSS-POLLINATION — Brand Network Mentions
# ═══════════════════════════════════════════════════════════════════════════════

CROSS_POLLINATION = {
    "blocksignals": {
        "zerodev": "💡 Want to automate your crypto tracking? @ZeroDev builds no-code tools for traders",
        "robovai_ar": "🌍 Arabic content? @RoboVAI covers crypto in Arabic for MENA region",
    },
    "zerodev": {
        "blocksignals": "📊 Need crypto data for your automations? @BlockSignals has real-time feeds",
        "robovai_ar": "🇪🇬 Arabic automation content? @RoboVAI teaches no-code in Arabic",
    },
    "robovai_ar": {
        "all": "🌐 **شبكتنا الإنجليزية:**\n⚡ @BlockSignals — أخبار الكريبتو\n💻 @ZeroDev — أدوات الأتمتة\n\nتابعونا للمحتوى بالإنجليزي! 🚀",
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# 📊 HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════


def get_feeds_for_brand(brand_name: str) -> List[str]:
    """Get RSS feeds for specific brand."""
    return BRAND_FEEDS.get(brand_name, [])


def get_all_brands_with_feeds() -> List[str]:
    """Get list of all brands that have RSS feeds."""
    return [brand for brand, feeds in BRAND_FEEDS.items() if feeds]


def get_publishing_order(
    brand_name: str, enabled_platforms: List[str]
) -> List[Dict[str, Any]]:
    """Get publishing order filtered by enabled platforms."""
    brand_order = PUBLISHING_ORDER.get(brand_name, [])
    return [p for p in brand_order if p["platform"] in enabled_platforms]


def inject_ctas(
    content: str, platform: str, brand_name: str, published_urls: Dict[str, str]
) -> str:
    """Inject cross-platform CTAs at end of content."""
    brand_templates = CTA_TEMPLATES.get(brand_name, {})
    template = brand_templates.get(platform, "")

    if not template:
        return content

    try:
        url_dict = {f"{p}_url": url for p, url in published_urls.items()}
        cta = template.format(**url_dict)
        return content + cta
    except KeyError as e:
        print(f"⚠️ Missing URL for CTA placeholder: {e}")
        return content


def should_cross_pollinate(post_count: int) -> bool:
    """Determine if post should include cross-brand reference (every 10th post)."""
    return post_count % 10 == 0


def get_cross_pollination_snippet(brand_name: str) -> str:
    """Get cross-brand mention snippet."""
    snippets = CROSS_POLLINATION.get(brand_name, {})

    if not snippets:
        return ""

    if brand_name == "robovai_ar":
        return snippets.get("all", "")

    return random.choice(list(snippets.values()))


# Legacy compatibility
RSS_FEEDS = []
for brand_feeds in BRAND_FEEDS.values():
    RSS_FEEDS.extend(brand_feeds)
RSS_FEEDS = list(set(RSS_FEEDS))
