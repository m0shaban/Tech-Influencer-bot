"""
Sequential Publisher - Multi-Brand Publishing with CTA Injection

Handles sequential publishing across platforms with delays and cross-platform CTAs.
"""

import asyncio
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
import os
import re
from urllib.parse import urlparse

from ai_processor import rewrite_with_ai
from feeds_config import (
    get_publishing_order,
    inject_ctas,
    should_cross_pollinate,
    get_cross_pollination_snippet,
)


def _extract_source_name(url: str) -> str:
    """Extract readable source name from URL."""
    if not url:
        return "المصدر" if True else "Source"  # Placeholder
    
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # Remove common prefixes
        domain = re.sub(r'^(www\.|blog\.|news\.)', '', domain)
        
        # Known source mappings
        source_names = {
            "coindesk.com": "CoinDesk",
            "cointelegraph.com": "Cointelegraph",
            "theblock.co": "The Block",
            "decrypt.co": "Decrypt",
            "blockworks.co": "Blockworks",
            "bitcoinmagazine.com": "Bitcoin Magazine",
            "theverge.com": "The Verge",
            "techcrunch.com": "TechCrunch",
            "wired.com": "Wired",
            "arstechnica.com": "Ars Technica",
            "engadget.com": "Engadget",
            "zdnet.com": "ZDNet",
            "cnet.com": "CNET",
            "mashable.com": "Mashable",
            "venturebeat.com": "VentureBeat",
            "thenextweb.com": "The Next Web",
            "openai.com": "OpenAI",
            "google.com": "Google",
            "microsoft.com": "Microsoft",
            "nvidia.com": "NVIDIA",
            "huggingface.co": "Hugging Face",
            "deepmind.google": "DeepMind",
            "anthropic.com": "Anthropic",
            "aitnews.com": "AI Tech News (عربي)",
            "wamda.com": "Wamda",
            "menabytes.com": "MENABytes",
            "arabnet.me": "ArabNet",
            "zapier.com": "Zapier",
            "bubble.io": "Bubble",
            "webflow.com": "Webflow",
            "producthunt.com": "Product Hunt",
            "indiehackers.com": "Indie Hackers",
            "dev.to": "Dev.to",
            "medium.com": "Medium",
            "reddit.com": "Reddit",
        }
        
        # Check for known sources
        for key, name in source_names.items():
            if key in domain:
                return name
        
        # Fallback: capitalize domain name
        name = domain.split('.')[0].replace('-', ' ').title()
        return name
        
    except Exception:
        return "Source"


def _format_source_attribution(source_name: str, source_url: str, language: str) -> str:
    """Format source attribution text."""
    if language == "ar":
        return f"\n\n📰 المصدر: {source_name}"
    else:
        return f"\n\n📰 Source: {source_name}"


class SequentialPublisher:
    """
    Manages sequential publishing workflow for multi-brand system

    Features:
    - Platform-specific content generation
    - Sequential publishing with delays
    - URL collection and CTA injection
    - Cross-brand pollination (10% of posts)
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize sequential publisher

        Args:
            config: Full config.json data
        """
        self.config = config
        self.brands = config.get("brands", {})
        self.post_count = {}  # Track posts per brand for cross-pollination
        self.last_errors: List[Dict[str, str]] = []

    async def publish_item(
        self,
        brand_name: str,
        feed_item: Dict[str, Any],
        platform_publisher: Any,  # The multi_platform_publisher instance
        telegram_context: Any = None,
        *,
        fast_mode: bool = False,
    ) -> Dict[str, str]:
        """
        Process and publish one feed item across all enabled platforms

        Args:
            brand_name: Brand identifier (blocksignals, zerodev, etc.)
            feed_item: Dict with title, summary, link
            platform_publisher: Instance of MultiPlatformPublisher

        Returns:
            Dict of {platform: published_url}
        """
        self.last_errors = []

        # Get brand config
        brand_config = self.brands.get(brand_name)
        if not brand_config:
            print(f"Brand {brand_name} not found in config")
            self.last_errors.append({"platform": "config", "error": "brand not found"})
            return {}

        # Get enabled platforms
        enabled_platforms = self._get_enabled_platforms(brand_config)
        if not enabled_platforms:
            print(f"No enabled platforms for {brand_name}")
            self.last_errors.append(
                {"platform": "config", "error": "no enabled platforms"}
            )
            return {}

        # Get publishing order with delays
        publishing_order = get_publishing_order(brand_name, enabled_platforms)
        if not publishing_order:
            print(f"No publishing order defined for {brand_name}")
            self.last_errors.append(
                {"platform": "config", "error": "no publishing order"}
            )
            return {}

        # Get brand language
        brand_language = brand_config.get("language", "en")
        brand_persona = brand_config.get("system_prompt", "")

        # Track published URLs for CTA injection (only real URLs)
        published_urls: Dict[str, str] = {}
        # Track platforms published (for success accounting even when no URL is returned)
        published_platforms: Dict[str, str] = {}

        start_ts = asyncio.get_event_loop().time()

        reporter = getattr(platform_publisher, "reporter", None)
        if reporter:
            try:
                await reporter.report_post_start(
                    total_platforms=len(publishing_order),
                    caption_preview=str(feed_item.get("title", "") or ""),
                )
            except Exception:
                reporter = None

        # Track post count for cross-pollination
        if brand_name not in self.post_count:
            self.post_count[brand_name] = 0
        self.post_count[brand_name] += 1

        # Check if this post should cross-pollinate
        add_cross_pollination = should_cross_pollinate(self.post_count[brand_name])

        print(f"\n{'='*60}")
        print(f"Publishing for {brand_config.get('display_name', brand_name)}")
        try:
            print(f"Title: {feed_item.get('title', 'Untitled')[:80]}...")
        except UnicodeEncodeError:
            print("Title: (title contains unicode characters)")
        print(f"Language: {brand_language}")
        print(
            f"Platforms: {len(publishing_order)} ({', '.join([p['platform'] for p in publishing_order])})"
        )
        print(f"{'='*60}\n")

        # Publish to each platform sequentially
        for idx, platform_config in enumerate(publishing_order, 1):
            platform = platform_config["platform"]
            delay_minutes = platform_config["delay_minutes"]
            enable_cta = platform_config.get("enable_cta", False)

            # Wait for delay (skip for first platform)
            if (not fast_mode) and delay_minutes > 0 and idx > 1:
                print(
                    f"Waiting {delay_minutes} minutes before publishing to {platform}..."
                )
                await asyncio.sleep(delay_minutes * 60)

            try:
                # Generate platform-specific content
                print(
                    f"\n[{idx}/{len(publishing_order)}] Generating content for {platform}..."
                )

                content_data = rewrite_with_ai(
                    title=feed_item.get("title", ""),
                    summary=feed_item.get("summary", ""),
                    link=feed_item.get("link", ""),
                    system_prompt=brand_persona,
                    platform=platform,
                    brand_name=brand_name,
                    brand_language=brand_language,
                )

                if not content_data:
                    print(f"Content generation failed for {platform} — using fallback")
                    content_data = {}

                # Get platform-specific content field
                content_field = self._get_content_field_for_platform(platform)
                content = str(content_data.get(content_field, "") or "").strip()
                if not content:
                    content = self._fallback_content_for_platform(
                        platform=platform,
                        brand_name=brand_name,
                        brand_language=brand_language,
                        feed_item=feed_item,
                        content_data=content_data,
                    )

                # Add source attribution (CRITICAL: always cite the original source)
                source_url = str(feed_item.get("link", "") or "").strip()
                if source_url:
                    source_name = _extract_source_name(source_url)
                    source_text = _format_source_attribution(source_name, source_url, brand_language)
                    content = content + source_text

                # Inject CTAs if enabled and we have URLs
                if enable_cta and any(v for v in published_urls.values()):
                    print(
                        f"Injecting CTAs from {len(published_urls)} previous platforms..."
                    )
                    content = inject_ctas(content, platform, brand_name, published_urls)

                # Add cross-pollination snippet (10% of posts)
                if add_cross_pollination and idx == len(
                    publishing_order
                ):  # Only on last platform
                    cross_snippet = get_cross_pollination_snippet(brand_name)
                    if cross_snippet:
                        print(f"Adding cross-brand reference...")
                        content += f"\n\n{cross_snippet}"

                # Build CTA buttons (Telegram only; URLs are not embedded in body by design)
                cta_buttons = None
                if platform == "telegram":
                    source_url = str(feed_item.get("link", "") or "").strip() or None

                    # Prefer previous platform URL (Dev.to/Blogger) when available
                    preferred_url = None
                    if enable_cta and published_urls:
                        if brand_name == "zerodev" and published_urls.get("devto"):
                            preferred_url = published_urls.get("devto")
                        elif brand_name == "robovai_ar" and published_urls.get(
                            "blogger"
                        ):
                            preferred_url = published_urls.get("blogger")
                        else:
                            # First non-empty URL
                            for u in published_urls.values():
                                if u:
                                    preferred_url = u
                                    break

                    url_for_button = preferred_url or source_url
                    if url_for_button:
                        if brand_language == "ar":
                            btn_text = "🔗 اقرأ المزيد"
                        else:
                            btn_text = "🔗 Read more"
                        cta_buttons = [{"text": btn_text, "url": url_for_button}]

                # Publish to platform
                print(f"Publishing to {platform}...")
                result = await self._publish_to_platform(
                    platform=platform,
                    content=content,
                    content_data=content_data,
                    brand_name=brand_name,
                    brand_config=brand_config,
                    platform_publisher=platform_publisher,
                    feed_item=feed_item,
                    telegram_context=telegram_context,
                    cta_buttons=cta_buttons,
                )

                if result:
                    url = (
                        str(result.get("url") or "").strip()
                        if isinstance(result, dict)
                        else ""
                    )
                    published_platforms[platform] = url or "ok"
                    if url:
                        published_urls[platform] = url
                        print(f"{platform.upper()}: {url}")
                    else:
                        print(f"{platform.upper()}: published")
                    if reporter:
                        try:
                            await reporter.report_platform_success(
                                platform=platform,
                                post_url=(url or None),
                            )
                        except Exception:
                            pass
                else:
                    print(f"{platform}: publish returned no result")
                    self.last_errors.append(
                        {"platform": platform, "error": "publish returned no result"}
                    )
                    if reporter:
                        try:
                            await reporter.report_platform_failure(
                                platform=platform,
                                error="publish returned no result",
                            )
                        except Exception:
                            pass

                # Micro delay between platforms (kept tiny; avoids hammering APIs)
                if idx < len(publishing_order):
                    try:
                        inter_delay = max(
                            0,
                            int(os.getenv("INTER_PLATFORM_DELAY_SECONDS", "1") or "1"),
                        )
                    except Exception:
                        inter_delay = 1
                    if (not fast_mode) and inter_delay > 0:
                        await asyncio.sleep(inter_delay)

            except Exception as e:
                print(f"Error publishing to {platform}: {e}")
                self.last_errors.append({"platform": platform, "error": str(e)})
                if reporter:
                    try:
                        await reporter.report_platform_failure(
                            platform=platform,
                            error=str(e),
                        )
                    except Exception:
                        pass
                continue

        print(f"\n{'='*60}")
        print(f"Publishing complete for {brand_config.get('display_name', brand_name)}")
        print(
            f"Published to {len(published_platforms)}/{len(publishing_order)} platforms"
        )
        print(f"{'='*60}\n")

        if reporter:
            try:
                successful = len(published_platforms)
                failed = max(0, len(publishing_order) - successful)
                duration_seconds = max(0.0, asyncio.get_event_loop().time() - start_ts)
                await reporter.report_post_complete(
                    successful=successful,
                    failed=failed,
                    total=len(publishing_order),
                    duration_seconds=duration_seconds,
                )
            except Exception:
                pass

        return published_platforms

    def _fallback_content_for_platform(
        self,
        *,
        platform: str,
        brand_name: str,
        brand_language: str,
        feed_item: Dict[str, Any],
        content_data: Dict[str, Any],
    ) -> str:
        title = str(feed_item.get("title", "") or "").strip()
        summary = str(feed_item.get("summary", "") or "").strip()

        if brand_language == "ar":
            if platform in {"blogger", "devto"}:
                return (
                    f"# {title or 'تحديث تقني'}\n\n"
                    f"{summary or 'ملخص سريع للخبر/الأداة.'}\n\n"
                    "## أهم النقاط\n"
                    "- الفكرة الأساسية\n"
                    "- ليه ده مهم\n"
                    "- إزاي تستفيد منه عملياً\n\n"
                    "## خطوات سريعة\n"
                    "1) جرّبه بنفسك\n"
                    "2) طبّقه على شغلك\n"
                    "3) شاركنا رأيك\n"
                )
            return (
                f"{title}\n\n"
                f"• {summary[:220]}\n\n"
                "قولّي: إيه أكتر حاجة عجبتك/مضايقاك في الخبر ده؟"
            ).strip()

        # English fallback
        if platform in {"blogger", "devto"}:
            return (
                f"# {title or 'Tech Update'}\n\n"
                f"{summary or 'Quick summary of the update.'}\n\n"
                "## Key takeaways\n"
                "- What changed\n"
                "- Why it matters\n"
                "- How to apply it\n\n"
                "## Next steps\n"
                "1) Try it today\n"
                "2) Adapt it to your workflow\n"
                "3) Share your results\n"
            )
        return (
            f"{title}\n\n"
            f"• {summary[:220]}\n\n"
            "What’s one workflow you’d automate with this?"
        ).strip()

    def _get_enabled_platforms(self, brand_config: Dict[str, Any]) -> List[str]:
        """Get list of enabled platforms for brand"""
        platforms = brand_config.get("platforms", {})
        return [p for p, config in platforms.items() if config.get("enabled", False)]

    def _get_content_field_for_platform(self, platform: str) -> str:
        """Map platform to content field in AI response"""
        field_map = {
            "telegram": "telegram_post",
            "facebook": "facebook_post",
            "discord": "discord_msg",
            "blogger": "blog_content_md",
            "devto": "blog_content_md",
            "linkedin": "linkedin_post",
            "twitter": "telegram_post",  # Short content
            "reddit": "facebook_post",  # Medium content
            "medium": "blog_content_md",  # Long content
        }
        return field_map.get(platform, "telegram_post")

    async def _publish_to_platform(
        self,
        platform: str,
        content: str,
        content_data: Dict[str, Any],
        brand_name: str,
        brand_config: Dict[str, Any],
        platform_publisher: Any,
        feed_item: Dict[str, Any],
        telegram_context: Any,
        cta_buttons: Optional[Any] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Publish content to specific platform

        Returns:
            Dict with 'url' key if successful
        """
        try:
            # Import platform-specific publishers dynamically
            if platform == "telegram":
                return await self._publish_telegram(
                    content,
                    brand_config,
                    platform_publisher,
                    telegram_context,
                    cta_buttons=cta_buttons,
                )
            elif platform == "facebook":
                return await self._publish_facebook(content, platform_publisher)
            elif platform == "discord":
                return await self._publish_discord(content, platform_publisher)
            elif platform == "blogger":
                return await self._publish_blogger(content_data, platform_publisher)
            elif platform == "devto":
                return await self._publish_devto(
                    content_data, platform_publisher, feed_item
                )
            elif platform == "linkedin":
                return await self._publish_linkedin(content, platform_publisher)
            else:
                print(f"⚠️ Platform {platform} not yet implemented")
                return None

        except Exception as e:
            print(f"❌ Publishing error for {platform}: {e}")
            return None

    async def _publish_telegram(
        self,
        content: str,
        brand_config: Dict[str, Any],
        platform_publisher: Any,
        telegram_context: Any,
        *,
        cta_buttons: Optional[Any] = None,
    ) -> Optional[Dict[str, Any]]:
        """Publish to Telegram"""
        channel_id = brand_config.get("channel_id")
        if not channel_id:
            print("⚠️ No Telegram channel_id configured")
            return None

        # Use platform_publisher's telegram method
        result = await platform_publisher.publish_to_telegram(
            channel_id=channel_id,
            message=content,
            telegram_context=telegram_context,
            cta_buttons=cta_buttons,
        )

        if isinstance(result, dict) and (
            result.get("status") == "success" or result.get("success")
        ):
            return {"url": ""}
        return None

    async def _publish_facebook(
        self,
        content: str,
        platform_publisher: Any,
    ) -> Optional[Dict[str, Any]]:
        """Publish to Facebook"""
        result = await platform_publisher.publish_to_facebook(
            message=content,
        )

        if result:
            # Extract post URL if available
            if result.get("success"):
                post_id = result.get("post_id") or result.get("id")
                url = result.get("url")
                if url:
                    return {"url": url}
                if post_id:
                    return {"url": f"https://facebook.com/{post_id}"}
                return {"url": "https://facebook.com"}

            # If not success, logged error might have happened
            if result.get("error") or not result.get("success"):
                print(f"Facebook publish failed: {result}")
        return None

    async def _publish_discord(
        self,
        content: str,
        platform_publisher: Any,
    ) -> Optional[Dict[str, Any]]:
        """Publish to Discord"""
        result = await platform_publisher.publish_to_discord(
            message=content,
        )

        if result:
            # Discord webhooks return message URL
            return {"url": result.get("url", "Discord message posted")}
        return None

    async def _publish_blogger(
        self,
        content_data: Dict[str, Any],
        platform_publisher: Any,
    ) -> Optional[Dict[str, Any]]:
        """Publish to Blogger"""
        title = content_data.get("blog_title", "Untitled Post")
        content = content_data.get("blog_content_md", "")

        result = await platform_publisher.publish_to_blogger(
            title=title,
            content=content,
        )

        if result:
            return {"url": result.get("url", "")}
        return None

    async def _publish_devto(
        self,
        content_data: Dict[str, Any],
        platform_publisher: Any,
        feed_item: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Publish to Dev.to"""
        title = content_data.get("blog_title", feed_item.get("title", "Untitled"))
        content = content_data.get("blog_content_md", "")

        result = await platform_publisher.publish_to_devto(
            title=title,
            content=content,
        )

        if result:
            return {"url": result.get("url", "")}
        return None

    async def _publish_linkedin(
        self,
        content: str,
        platform_publisher: Any,
    ) -> Optional[Dict[str, Any]]:
        """Publish to LinkedIn"""
        result = await platform_publisher.publish_to_linkedin(
            message=content,
        )

        if result:
            return {"url": result.get("url", "LinkedIn post published")}
        return None

    # NOTE: Brand/account resolution is handled by brand_context.py via brand.accounts.
