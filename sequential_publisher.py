"""
Sequential Publisher - Multi-Brand Publishing with CTA Injection

Handles sequential publishing across platforms with delays and cross-platform CTAs.
"""

import asyncio
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

from ai_processor import rewrite_with_ai
from feeds_config import (
    get_publishing_order,
    inject_ctas,
    should_cross_pollinate,
    get_cross_pollination_snippet,
)


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
            print(f"❌ Brand {brand_name} not found in config")
            self.last_errors.append({"platform": "config", "error": "brand not found"})
            return {}

        # Get enabled platforms
        enabled_platforms = self._get_enabled_platforms(brand_config)
        if not enabled_platforms:
            print(f"⚠️ No enabled platforms for {brand_name}")
            self.last_errors.append(
                {"platform": "config", "error": "no enabled platforms"}
            )
            return {}

        # Get publishing order with delays
        publishing_order = get_publishing_order(brand_name, enabled_platforms)
        if not publishing_order:
            print(f"⚠️ No publishing order defined for {brand_name}")
            self.last_errors.append(
                {"platform": "config", "error": "no publishing order"}
            )
            return {}

        # Get brand language
        brand_language = brand_config.get("language", "en")
        brand_persona = brand_config.get("system_prompt", "")

        # Track published URLs for CTAs
        published_urls = {}

        # Track post count for cross-pollination
        if brand_name not in self.post_count:
            self.post_count[brand_name] = 0
        self.post_count[brand_name] += 1

        # Check if this post should cross-pollinate
        add_cross_pollination = should_cross_pollinate(self.post_count[brand_name])

        print(f"\n{'='*60}")
        print(f"📢 Publishing for {brand_config.get('display_name', brand_name)}")
        print(f"📝 Title: {feed_item.get('title', 'Untitled')[:80]}...")
        print(f"🌐 Language: {brand_language}")
        print(
            f"📱 Platforms: {len(publishing_order)} ({', '.join([p['platform'] for p in publishing_order])})"
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
                    f"⏳ Waiting {delay_minutes} minutes before publishing to {platform}..."
                )
                await asyncio.sleep(delay_minutes * 60)

            try:
                # Generate platform-specific content
                print(
                    f"\n[{idx}/{len(publishing_order)}] 🤖 Generating content for {platform}..."
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
                    print(f"❌ Content generation failed for {platform}")
                    self.last_errors.append(
                        {"platform": platform, "error": "content generation failed"}
                    )
                    continue

                # Get platform-specific content field
                content_field = self._get_content_field_for_platform(platform)
                content = content_data.get(content_field, "")

                if not content:
                    print(f"❌ No content found in field '{content_field}'")
                    self.last_errors.append(
                        {
                            "platform": platform,
                            "error": f"empty content field {content_field}",
                        }
                    )
                    continue

                # Inject CTAs if enabled and we have URLs
                if enable_cta and published_urls:
                    print(
                        f"🔗 Injecting CTAs from {len(published_urls)} previous platforms..."
                    )
                    content = inject_ctas(content, platform, brand_name, published_urls)

                # Add cross-pollination snippet (10% of posts)
                if add_cross_pollination and idx == len(
                    publishing_order
                ):  # Only on last platform
                    cross_snippet = get_cross_pollination_snippet(brand_name)
                    if cross_snippet:
                        print(f"🌐 Adding cross-brand reference...")
                        content += f"\n\n{cross_snippet}"

                # Publish to platform
                print(f"📤 Publishing to {platform}...")
                result = await self._publish_to_platform(
                    platform=platform,
                    content=content,
                    content_data=content_data,
                    brand_name=brand_name,
                    brand_config=brand_config,
                    platform_publisher=platform_publisher,
                    feed_item=feed_item,
                    telegram_context=telegram_context,
                )

                if result and result.get("url"):
                    published_urls[platform] = result["url"]
                    print(f"✅ {platform.upper()}: {result['url']}")
                else:
                    print(f"⚠️ {platform}: Published but no URL returned")
                    # Some platforms don't return URLs; treat as soft-success if result exists
                    if not result:
                        self.last_errors.append(
                            {
                                "platform": platform,
                                "error": "publish returned no result",
                            }
                        )

            except Exception as e:
                print(f"❌ Error publishing to {platform}: {e}")
                self.last_errors.append({"platform": platform, "error": str(e)})
                continue

        print(f"\n{'='*60}")
        print(
            f"✅ Publishing complete for {brand_config.get('display_name', brand_name)}"
        )
        print(
            f"📊 Published to {len(published_urls)}/{len(publishing_order)} platforms"
        )
        print(f"{'='*60}\n")

        return published_urls

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
                    content, brand_config, platform_publisher, telegram_context
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
        )

        if result:
            # Telegram doesn't return public URLs easily
            return {"url": f"https://t.me/{channel_id.replace('-100', '')}"}
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
            post_id = result.get("id", "")
            if post_id:
                return {"url": f"https://facebook.com/{post_id}"}
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
