"""
RSS Feeds & Publishing Configuration per Brand

🎯 DESIGN:
- 60 high-quality sources per brand (180 total)
- Publishing order optimized for CTA flow
- Source attribution in all content
- Cross-platform promotion
"""

from typing import List, Dict, Any
import random


# ═══════════════════════════════════════════════════════════════════════════════
# 📡 BRAND RSS FEEDS — 60 Sources Each (180 Total)
# ═══════════════════════════════════════════════════════════════════════════════

BRAND_FEEDS = {
    "blocksignals": [
        # Tier 1: Major Crypto News
        "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "https://cointelegraph.com/rss",
        "https://www.theblock.co/rss.xml",
        "https://blockworks.co/feed",
        "https://decrypt.co/feed",
        # Official Protocol Blogs
        "https://blog.ethereum.org/feed.xml",
        "https://www.nansen.ai/research/rss.xml",
        "https://insights.glassnode.com/rss/",
        "https://messari.io/rss",
        "https://www.bankless.com/rss",
        # News Aggregators
        "https://cryptopanic.com/news/rss/",
        "https://www.newsbtc.com/feed/",
        "https://bitcoinmagazine.com/.rss/full/",
        "https://consensys.io/blog/rss.xml",
        "https://101blockchains.com/feed",
        # Market News
        "https://blockchain.news/rss",
        "https://insidebitcoins.com/feed",
        "https://www.bitdegree.org/crypto/news/rss",
        "https://blog.coinfund.io/feed",
        "https://www.blockchain.com/blog/rss",
        # Analysis & Trading
        "https://cryptoslate.com/feed/",
        "https://beincrypto.com/feed/",
        "https://ambcrypto.com/feed/",
        "https://www.cryptoglobe.com/latest/feed/",
        "https://bitcoinist.com/feed/",
        # DeFi Focused
        "https://thedefiant.io/api/feed",
        "https://cryptobriefing.com/feed/",
        "https://www.blocktempo.com/feed/",
        "https://www.altcoinbuzz.io/feed/",
        "https://chainwire.org/feed/",
        # Protocol Blogs
        "https://ripplecoinnews.com/feed/",
        "https://nulltx.com/feed/",
        "https://dappradar.com/blog/feed",
        "https://blog.0xproject.com/feed",
        "https://blog.polygon.technology/rss.xml",
        "https://solana.com/blog/rss.xml",
        "https://cardanofoundation.org/en/news/rss/",
        "https://blog.chain.link/rss.xml",
        "https://aave.com/blog/rss.xml",
        "https://blog.uniswap.org/rss.xml",
        # NFT & Gaming
        "https://opensea.io/blog/feed/",
        "https://rarible.com/blog/feed/",
        "https://editorial.superrare.com/feed/",
        # Security & Wallets
        "https://www.ledger.com/blog/feed",
        "https://blog.trezor.io/feed",
        # Exchange Blogs
        "https://blog.kraken.com/feed/",
        "https://www.binance.com/en/blog/rss",
        "https://www.coinbase.com/blog/rss",
        "https://www.gemini.com/blog/rss",
        "https://blog.bitmex.com/feed/",
        "https://insights.deribit.com/feed/",
        # Stablecoins & DeFi Protocols
        "https://www.circle.com/blog/rss.xml",
        "https://tether.to/en/rss/",
        "https://blog.makerdao.com/feed/",
        "https://compound.finance/blog/rss.xml",
        "https://blog.yearn.finance/feed",
        "https://news.curve.fi/rss/",
        "https://www.sushi.com/blog/rss.xml",
        "https://blog.pancakeswap.finance/feed",
    ],
    "zerodev": [
        # No-Code Platforms
        "https://bubble.io/blog/rss",
        "https://webflow.com/blog/rss.xml",
        "https://www.softr.io/blog/rss.xml",
        "https://www.indiehackers.com/feed.xml",
        "https://www.producthunt.com/feed?category=software",
        # SaaS & Growth
        "https://www.saastr.com/feed/",
        "https://tomtunguz.com/index.xml",
        "https://www.cursor.com/blog/rss.xml",
        "https://blog.replit.com/feed.xml",
        "https://www.makerpad.co/blog-rss.xml",
        # Automation Tools
        "https://zapier.com/blog/feeds/latest/",
        "https://blog.airtable.com/rss/",
        "https://www.nocode.tech/stories/blog/rss.xml",
        "https://getlatka.com/blog/feed",
        "https://www.saasmag.com/feed/",
        # Design & Dev
        "https://hackingui.com/feed/",
        "https://nocodedev.com/feed",
        "https://codeornocode.com/feed",
        "https://nocodesundays.com/feed",
        # Mobile No-Code
        "https://www.adalo.com/posts/rss.xml",
        "https://www.glideapps.com/blog/rss.xml",
        "https://blog.flutterflow.io/rss/",
        "https://retool.com/blog/rss.xml",
        "https://blog.google/products/appsheet/rss/",
        # Enterprise Low-Code
        "https://www.outsystems.com/blog/rss.xml",
        "https://www.mendix.com/blog/feed/",
        "https://www.bettyblocks.com/blog/rss.xml",
        "https://blog.caspio.com/feed/",
        "https://www.knack.com/blog/feed/",
        # Builders & Portals
        "https://www.stackerhq.com/blog/rss.xml",
        "https://www.bravostudio.app/blog/rss.xml",
        "https://dorik.com/blog/feed",
        "https://carrd.co/blog/feed",
        "https://blog.tally.so/rss/",
        "https://www.typeform.com/blog/feed/",
        # Productivity & Docs
        "https://www.notion.so/blog/rss.xml",
        "https://coda.io/blog/rss.xml",
        "https://miro.com/blog/feed/",
        "https://www.figma.com/blog/feed/",
        "https://www.canva.com/learn/feed/",
        # SaaS Marketing
        "https://buffer.com/resources/rss/",
        "https://blog.hubspot.com/rss.xml",
        "https://www.intercom.com/blog/feed/",
        "https://blog.close.com/feed/",
        "https://www.profitwell.com/recur/rss.xml",
        # VC & Growth
        "https://openviewpartners.com/blog/feed/",
        "https://review.firstround.com/feed.xml",
        "https://blog.ycombinator.com/feed/",
        "https://www.techstars.com/blog/rss.xml",
        # Analytics & Metrics
        "https://baremetrics.com/blog/feed",
        "https://blog.chartmogul.com/feed/",
        "https://userguiding.com/blog/feed/",
        "https://www.appcues.com/blog/rss.xml",
        "https://www.trychameleon.com/blog/rss.xml",
        # Product Management
        "https://www.pendo.io/blog/feed/",
        "https://www.productplan.com/feed/",
        "https://www.aha.io/blog/feed",
    ],
    "robovai_ar": [
        # Major AI Companies
        "https://openai.com/news/rss.xml",
        "https://research.google/blog/rss",
        "https://news.microsoft.com/source/topics/ai/feed/",
        "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml",
        "https://techcrunch.com/category/artificial-intelligence/feed/",
        "https://www.wired.com/feed/category/science/latest/rss",
        "https://news.mit.edu/rss/topic/artificial-intelligence",
        "https://blogs.nvidia.com/feed/",
        "https://huggingface.co/blog/feed.xml",
        "https://venturebeat.com/category/ai/feed/",
        # Tech News
        "https://www.zdnet.com/topic/artificial-intelligence/rss.xml",
        "https://lifehacker.com/rss",
        "https://www.makeuseof.com/feed/",
        "https://www.fastcompany.com/technology/rss",
        "https://www.aitrends.com/feed/",
        # MENA Tech
        "https://www.wamda.com/rss",
        "https://www.menabytes.com/feed/",
        "https://www.tech-wd.com/wd/feed/",
        "https://aitnews.com/feed/",
        "https://www.arabnet.me/english/rss",
        # AI Research Labs
        "https://deepmind.google/blog/rss.xml",
        "https://ai.meta.com/blog/rss.xml",
        "https://www.anthropic.com/news/rss.xml",
        "https://aws.amazon.com/blogs/machine-learning/feed/",
        "https://www.ibm.com/blog/category/research/feed/",
        # Academic AI
        "https://bair.berkeley.edu/blog/feed.xml",
        "https://ai.stanford.edu/blog/feed.xml",
        "https://machinelearningmastery.com/feed/",
        "https://towardsdatascience.com/feed",
        "https://www.analyticsvidhya.com/feed/",
        # AI News Sites
        "https://www.kdnuggets.com/feed",
        "https://www.marktechpost.com/feed/",
        "https://www.unite.ai/feed/",
        "https://www.artificialintelligence-news.com/feed/",
        "https://thegradient.pub/rss/",
        "https://www.skynettoday.com/rss.xml",
        # Productivity
        "https://productivityland.com/feed/",
        "https://www.asianefficiency.com/feed/",
        "https://zenhabits.net/feed/",
        "https://blog.rescuetime.com/feed/",
        "https://todoist.com/help/articles/feed",
        # Project Management
        "https://blog.trello.com/rss.xml",
        "https://blog.asana.com/feed/",
        "https://monday.com/blog/feed/",
        "https://clickup.com/blog/feed/",
        # Career & Business
        "https://www.workitdaily.com/blog/rss.xml",
        "https://www.careercontessa.com/blog/rss.xml",
        "https://www.themuse.com/advice/feed",
        "https://www.glassdoor.com/blog/feed/",
        "https://hbr.org/rss/topic/technology",
        "https://sloanreview.mit.edu/feed/",
        # Arabic Regional
        "https://www.almasryalyoum.com/rss/section/13",
        "https://www.youm7.com/rss/Section/328",
        "https://gate.ahram.org.eg/rss/14.aspx",
        "https://www.skynewsarabia.com/rss/technology.xml",
        "https://www.alarabiya.net/tools/mrss/technology.xml",
        "https://asharq.com/rss/technology/",
        "https://www.arabnews.com/cat/11/rss.xml",
        "https://www.entrepreneur.com/me/rss",
        "https://www.forbesmiddleeast.com/rss/technology",
    ],
}


# ═══════════════════════════════════════════════════════════════════════════════
# 📤 PUBLISHING ORDER — Blog First, Then Social (for CTAs)
# ═══════════════════════════════════════════════════════════════════════════════

PUBLISHING_ORDER = {
    "blocksignals": [
        {"platform": "telegram", "delay_minutes": 0, "enable_cta": False},
        {"platform": "discord", "delay_minutes": 2, "enable_cta": True},
    ],
    "zerodev": [
        {"platform": "devto", "delay_minutes": 0, "enable_cta": False},
        {"platform": "telegram", "delay_minutes": 2, "enable_cta": True},
    ],
    "robovai_ar": [
        {"platform": "blogger", "delay_minutes": 0, "enable_cta": False},
        {"platform": "facebook", "delay_minutes": 2, "enable_cta": True},
        {"platform": "telegram", "delay_minutes": 2, "enable_cta": True},
    ],
}


# ═══════════════════════════════════════════════════════════════════════════════
# 🔗 CTA TEMPLATES — Point to YOUR OWN Platforms (You are the source!)
# ═══════════════════════════════════════════════════════════════════════════════
#
# STRATEGY:
# - BlockSignals: Telegram is the HUB → Discord points to Telegram
# - ZeroDev: Dev.to is the HUB (full articles) → Telegram points to Dev.to
# - RoboVAI_AR: Blogger is the HUB (المدونة الرئيسية) → Facebook & Telegram point to Blogger
#
# The first platform in order gets NO CTA (it's the source)
# Later platforms get CTAs pointing BACK to the source
# ═══════════════════════════════════════════════════════════════════════════════

CTA_TEMPLATES = {
    # BlockSignals: Telegram → Discord
    "blocksignals": {
        "telegram": "",  # Source - no CTA needed
        "discord": "\n\n━━━━━━━━━━━━━━━━\n⚡ **Join our Telegram for instant signals**: {telegram_url}\n🔔 Never miss a move!\n\n#Crypto #BTC #ETH #DeFi #Web3",
    },
    # ZeroDev: Dev.to (full tutorials) → Telegram (alerts)
    "zerodev": {
        "devto": "",  # Source - full article lives here
        "telegram": "\n\n━━━━━━━━━━━━━━━━\n📖 **Full Tutorial on Dev.to**: {devto_url}\n\n👆 Step-by-step guide with code snippets!\n\n#NoCode #Automation #BuildInPublic #IndieHacker",
    },
    # RoboVAI_AR: Blogger (المدونة) → Facebook → Telegram
    "robovai_ar": {
        "blogger": "",  # المصدر الرئيسي - المقال الكامل هنا
        "facebook": "\n\n━━━━━━━━━━━━━━━━\n📖 **اقرأ المقال الكامل على المدونة**:\n{blogger_url}\n\n👆 شرح تفصيلي مع صور وأمثلة عملية!\n\n#ذكاء_اصطناعي #تقنية #AI #أتمتة",
        "telegram": "\n\n━━━━━━━━━━━━━━━━\n📖 **المقال الكامل**: {blogger_url}\n💬 **ناقشنا على فيسبوك**: {facebook_url}\n\n👆 تفاصيل أكتر وشرح عملي!\n\n#AI #تقنية #ذكاء_اصطناعي",
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# 🏷️ HASHTAG SETS
# ═══════════════════════════════════════════════════════════════════════════════

HASHTAG_SETS = {
    "blocksignals": {
        "default": [
            "#Crypto",
            "#BTC",
            "#ETH",
            "#DeFi",
            "#Web3",
            "#CryptoNews",
            "#Trading",
        ],
        "bitcoin": [
            "#Bitcoin",
            "#BTC",
            "#HODL",
            "#Cryptocurrency",
            "#BTCPrice",
            "#Halving",
        ],
        "ethereum": [
            "#Ethereum",
            "#ETH",
            "#DeFi",
            "#SmartContracts",
            "#Web3",
            "#Layer2",
        ],
        "defi": ["#DeFi", "#Yield", "#TVL", "#DEX", "#Lending", "#Staking"],
        "nft": ["#NFT", "#NFTs", "#DigitalArt", "#Web3", "#OpenSea"],
    },
    "zerodev": {
        "default": [
            "#NoCode",
            "#Automation",
            "#LowCode",
            "#BuildInPublic",
            "#IndieHacker",
            "#SaaS",
        ],
        "zapier": ["#Zapier", "#Automation", "#Workflow", "#Productivity", "#NoCode"],
        "bubble": ["#Bubble", "#NoCode", "#WebApp", "#StartupTools", "#BuildInPublic"],
        "ai": [
            "#AITools",
            "#AIAutomation",
            "#NoCodeAI",
            "#FutureOfWork",
            "#Productivity",
        ],
    },
    "robovai_ar": {
        "default": ["#ذكاء_اصطناعي", "#تقنية", "#AI", "#أتمتة", "#مصر", "#تكنولوجيا"],
        "chatgpt": ["#ChatGPT", "#OpenAI", "#ذكاء_اصطناعي", "#AIChat", "#GPT"],
        "tools": ["#أدوات_إنتاجية", "#تطبيقات", "#تقنية", "#Productivity"],
        "business": ["#ريادة_أعمال", "#شركات_ناشئة", "#تحول_رقمي", "#Startup"],
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


def get_hashtags(brand_name: str, category: str = "default") -> List[str]:
    """Get hashtags for brand and category."""
    brand_tags = HASHTAG_SETS.get(brand_name, {})
    return brand_tags.get(category, brand_tags.get("default", []))


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
    except KeyError:
        return content


def should_cross_pollinate(post_count: int) -> bool:
    """Cross-pollinate every 10th post."""
    return post_count % 10 == 0


def get_cross_pollination_snippet(brand_name: str) -> str:
    """Get cross-brand mention snippet."""
    snippets = {
        "blocksignals": "💡 @ZeroDev teaches no-code automation | 🇪🇬 @RoboVAI for Arabic tech",
        "zerodev": "📊 @BlockSignals for crypto signals | 🇪🇬 @RoboVAI for Arabic content",
        "robovai_ar": "🌐 تابعونا بالإنجليزي:\n⚡ @BlockSignals — كريبتو\n💻 @ZeroDev — أتمتة",
    }
    return snippets.get(brand_name, "")


# Legacy compatibility
RSS_FEEDS = []
for brand_feeds in BRAND_FEEDS.values():
    RSS_FEEDS.extend(brand_feeds)
RSS_FEEDS = list(set(RSS_FEEDS))
