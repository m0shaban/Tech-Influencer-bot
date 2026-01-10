"""
RSS Feeds Configuration per Brand

Each brand has curated RSS feeds targeting specific niches.
RoboVAI Arabic curates content from other brands (no direct feeds).
"""

from typing import List, Dict, Any


# Brand-specific RSS feeds
BRAND_FEEDS = {
    "blocksignals": [
        "https://cointelegraph.com/rss",
        "https://decrypt.co/feed",
        "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "https://cryptopotato.com/feed/",
        "https://beincrypto.com/feed/",
        "https://www.theblock.co/rss.xml",
        "https://crypto.news/feed/",
    ],
    
    "zerodev": [
        "https://www.nocode.tech/feed",
        "https://dev.to/feed/tag/nocode",
        "https://www.producthunt.com/feed",
        "https://zapier.com/blog/feed/",
        "https://bubble.io/blog/rss.xml",
        "https://webflow.com/blog/rss",
        "https://www.makerpad.co/feed",
    ],
    
    "flowpilot": [
        "https://zapier.com/blog/feed/",
        "https://www.notion.so/blog/rss",
        "https://lifehacker.com/rss",
        "https://www.makeuseof.com/feed/",
        "https://www.fastcompany.com/technology/rss",
    ],
    
    "growthbyte": [
        "https://moz.com/blog/feed",
        "https://neilpatel.com/feed/",
        "https://www.searchenginejournal.com/feed/",
        "https://contentmarketinginstitute.com/feed/",
        "https://blog.hubspot.com/marketing/rss.xml",
    ],
    
    "robovai_ar": [
        # No direct feeds - curates from other brands
    ],
}


def get_feeds_for_brand(brand_name: str) -> List[str]:
    """
    Get RSS feeds for specific brand
    
    Args:
        brand_name: Brand identifier (blocksignals, zerodev, etc.)
    
    Returns:
        List of RSS feed URLs
    """
    return BRAND_FEEDS.get(brand_name, [])


def get_all_brands_with_feeds() -> List[str]:
    """Get list of all brands that have RSS feeds (excludes robovai_ar)"""
    return [brand for brand, feeds in BRAND_FEEDS.items() if feeds]


def curate_for_robovai_ar(all_posts: List[Dict[str, Any]], max_items: int = 5) -> List[Dict[str, Any]]:
    """
    Curate content from other brands for RoboVAI Arabic
    
    Strategy:
    - Fetch last 24h posts from BlockSignals, ZeroDev, FlowPilot
    - Filter high-engagement posts (this is placeholder - needs analytics)
    - Return for translation/adaptation to Egyptian Arabic
    
    Args:
        all_posts: List of posts from all brands (last 24h)
        max_items: Maximum number of posts to curate
    
    Returns:
        List of curated posts for RoboVAI Arabic
    """
    # TODO: Implement curation logic
    # For now, return empty list - will be implemented when we have engagement data
    
    # Future logic:
    # 1. Filter posts from last 24 hours
    # 2. Score by engagement (likes, comments, shares)
    # 3. Diversity: pick from different brands
    # 4. Relevance: match RoboVAI AR audience interests
    # 5. Return top N posts
    
    return []


# Platform publishing order per brand
PUBLISHING_ORDER = {
    "blocksignals": [
        {"platform": "telegram", "delay_minutes": 0, "enable_cta": True},
        {"platform": "discord", "delay_minutes": 3, "enable_cta": True},
    ],
    
    "zerodev": [
        {"platform": "devto", "delay_minutes": 0, "enable_cta": True},
        {"platform": "telegram", "delay_minutes": 3, "enable_cta": True},
    ],
    
    "flowpilot": [
        {"platform": "telegram", "delay_minutes": 0, "enable_cta": False},
    ],
    
    "growthbyte": [
        {"platform": "linkedin", "delay_minutes": 0, "enable_cta": False},
        {"platform": "telegram", "delay_minutes": 3, "enable_cta": True},
    ],
    
    "robovai_ar": [
        {"platform": "blogger", "delay_minutes": 0, "enable_cta": True},
        {"platform": "facebook", "delay_minutes": 5, "enable_cta": True},
        {"platform": "telegram", "delay_minutes": 10, "enable_cta": True},
    ],
}


def get_publishing_order(brand_name: str, enabled_platforms: List[str]) -> List[Dict[str, Any]]:
    """
    Get publishing order for specific brand
    
    Args:
        brand_name: Brand identifier
        enabled_platforms: List of enabled platforms from config
    
    Returns:
        List of platform configs with delays and CTA settings
    """
    brand_order = PUBLISHING_ORDER.get(brand_name, [])
    
    # Filter only enabled platforms
    return [p for p in brand_order if p["platform"] in enabled_platforms]


# CTA templates per brand/platform
CTA_TEMPLATES = {
    "blocksignals": {
        "telegram": "\n\n💬 **Join the discussion on Discord**: {discord_url}",
        "discord": "\n\n⚡ **Get instant alerts on Telegram**: {telegram_url}",
    },
    
    "zerodev": {
        "telegram": "\n\n💻 **Full tutorial with code on Dev.to**: {devto_url}",
        "devto": "\n\n📱 **Daily no-code tips on Telegram**: {telegram_url}",
    },
    
    "flowpilot": {
        "telegram": "",  # No CTAs for single platform
    },
    
    "growthbyte": {
        "linkedin": "\n\n📱 **Follow us on Telegram for daily updates**: {telegram_url}",
        "telegram": "\n\n💼 **Professional insights on LinkedIn**: {linkedin_url}",
    },
    
    "robovai_ar": {
        "blogger": "\n\n---\n💬 **ناقش معانا على فيسبوك**: {facebook_url}\n📱 **تابع التحديثات على تليجرام**: {telegram_url}",
        "facebook": "\n\n📖 **اقرأ المقال كامل على البلوق**: {blogger_url}\n📱 **انضم لقناتنا على تليجرام**: {telegram_url}",
        "telegram": "\n\n📚 **التفاصيل الكاملة على البلوق**: {blogger_url}\n💬 **ناقش على فيسبوك**: {facebook_url}",
    },
}


def inject_ctas(
    content: str,
    platform: str,
    brand_name: str,
    published_urls: Dict[str, str]
) -> str:
    """
    Inject cross-platform CTAs at end of content
    
    Args:
        content: Original content
        platform: Current platform
        brand_name: Brand identifier
        published_urls: Dict of {platform: url} from previously published posts
    
    Returns:
        Content with CTAs appended
    """
    # Get template for brand/platform
    brand_templates = CTA_TEMPLATES.get(brand_name, {})
    template = brand_templates.get(platform, "")
    
    if not template:
        return content
    
    # Replace placeholders with actual URLs
    try:
        # Create dict with {platform_url: url} format
        url_dict = {f"{p}_url": url for p, url in published_urls.items()}
        cta = template.format(**url_dict)
        return content + cta
    except KeyError as e:
        # Missing URL for placeholder - return content without CTA
        print(f"⚠️ Missing URL for CTA placeholder: {e}")
        return content


# Cross-pollination config (10% of posts reference other brands)
CROSS_POLLINATION = {
    "blocksignals": {
        "zerodev": "💡 Building on Web3? @ZeroDev covers no-code Web3 tools weekly",
        "flowpilot": "⏰ Automate your portfolio tracking - @FlowPilot shares daily hacks",
    },
    "zerodev": {
        "blocksignals": "🪙 Integrate crypto payments? @BlockSignals tracks Web3 infrastructure news",
        "flowpilot": "⚡ Automate your no-code workflows - @FlowPilot has the tips",
    },
    "flowpilot": {
        "zerodev": "🛠️ Build your automation tools with no-code - @ZeroDev teaches how",
        "blocksignals": "💰 Automate crypto alerts - @BlockSignals covers the tools",
    },
    "robovai_ar": {
        "all": "📚 **مصادرنا المفضلة للتقنية**:\n🎯 BlockSignals (كريبتو)\n💻 ZeroDev (no-code)\n⏰ FlowPilot (إنتاجية)\n\nكل المحتوى مجاني - اشترك لو بتحب التقنية 🚀",
    },
}


def should_cross_pollinate(post_count: int) -> bool:
    """
    Determine if post should include cross-brand reference
    
    Args:
        post_count: Total number of posts published by brand
    
    Returns:
        True if this post (10% frequency) should cross-reference
    """
    return post_count % 10 == 0


def get_cross_pollination_snippet(brand_name: str) -> str:
    """
    Get cross-brand mention snippet
    
    Args:
        brand_name: Current brand
    
    Returns:
        Snippet mentioning other brands
    """
    import random
    
    snippets = CROSS_POLLINATION.get(brand_name, {})
    
    if not snippets:
        return ""
    
    # For robovai_ar, always return the "all" snippet
    if brand_name == "robovai_ar":
        return snippets.get("all", "")
    
    # For others, pick random brand to reference
    return random.choice(list(snippets.values()))


# Legacy RSS_FEEDS for backward compatibility (aggregates all brands)
RSS_FEEDS = []
for brand_feeds in BRAND_FEEDS.values():
    RSS_FEEDS.extend(brand_feeds)

# Remove duplicates
RSS_FEEDS = list(set(RSS_FEEDS))
