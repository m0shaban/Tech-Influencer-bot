"""
Multi-Platform Publisher
Unified interface for publishing to multiple platforms with scheduling support
"""

from typing import Any, Dict, Optional, Literal
import os
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

PlatformType = Literal[
    "telegram",
    "linkedin",
    "discord",
    "medium",
    "twitter",
    "blogger",
    "reddit",
    "facebook",
    "devto",
]


# Delay between platform publishes to prevent rate limiting
PLATFORM_DELAY_SECONDS = 5


class MultiPlatformPublisher:
    """Publish content to multiple platforms from a single interface"""

    def __init__(self, use_scheduler: bool = False):
        # use_scheduler is ignored - we always publish immediately now
        self.enabled_platforms = self._get_enabled_platforms()
        self.reporter = None

        try:
            from publishing_reporter import get_reporter

            self.reporter = get_reporter()
        except Exception as e:
            print(f"Failed to initialize reporter: {e}")

    def _get_enabled_platforms(self) -> list[PlatformType]:
        """Detect which platforms are configured"""
        platforms: list[PlatformType] = []

        # Load dynamic config from dashboard if available
        config_enabled = {}
        try:
            import json
            from pathlib import Path

            config_path = Path(__file__).parent / "platform_config.json"
            if config_path.exists():
                data = json.loads(config_path.read_text(encoding="utf-8"))
                # Map 'platforms' -> 'telegram' -> 'enabled'
                if "platforms" in data:
                    for k, v in data["platforms"].items():
                        config_enabled[k] = v.get("enabled", True)
        except Exception as e:
            print(f"⚠️ Failed to load platform_config.json: {e}")

        def is_enabled(name):
            # Default to True if not in config, otherwise use config value
            return config_enabled.get(name, True)

        # Telegram is always enabled (base platform)
        if os.getenv("TELEGRAM_TOKEN") and is_enabled("telegram"):
            platforms.append("telegram")

        # LinkedIn is optional
        if os.getenv("LINKEDIN_ACCESS_TOKEN") and is_enabled("linkedin"):
            platforms.append("linkedin")

        # Discord (webhook-based)
        if os.getenv("DISCORD_WEBHOOK_URL") and is_enabled("discord"):
            platforms.append("discord")

        # Medium (requires token + user ID)
        if (
            os.getenv("MEDIUM_INTEGRATION_TOKEN")
            and os.getenv("MEDIUM_USER_ID")
            and is_enabled("medium")
        ):
            platforms.append("medium")

        # Twitter/X (requires OAuth 1.0a credentials)
        if all(
            [
                os.getenv("TWITTER_API_KEY"),
                os.getenv("TWITTER_API_SECRET"),
                os.getenv("TWITTER_ACCESS_TOKEN"),
                os.getenv("TWITTER_ACCESS_SECRET"),
            ]
        ) and is_enabled("twitter"):
            platforms.append("twitter")

        # Blogger (requires Blog ID and API key or OAuth)
        if (
            os.getenv("BLOGGER_BLOG_ID")
            and (os.getenv("BLOGGER_API_KEY") or os.getenv("BLOGGER_ACCESS_TOKEN"))
            and is_enabled("blogger")
        ):
            platforms.append("blogger")

        # Reddit (requires OAuth credentials)
        if all(
            [
                os.getenv("REDDIT_CLIENT_ID"),
                os.getenv("REDDIT_CLIENT_SECRET"),
                os.getenv("REDDIT_USERNAME"),
                os.getenv("REDDIT_PASSWORD"),
            ]
        ) and is_enabled("reddit"):
            platforms.append("reddit")

        # Facebook (requires Page Access Token and Page ID)
        if (
            os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
            and os.getenv("FACEBOOK_PAGE_ID")
            and is_enabled("facebook")
        ):
            platforms.append("facebook")

        # Dev.to (requires API key)
        if os.getenv("DEVTO_API_KEY") and is_enabled("devto"):
            platforms.append("devto")

        return platforms

    async def publish(
        self,
        caption: str,
        link: Optional[str] = None,
        image_url: Optional[str] = None,
        image_local_path: Optional[str] = None,
        platforms: Optional[list[PlatformType]] = None,
        platform_payloads: Optional[Dict[PlatformType, Dict[str, Any]]] = None,
        telegram_context: Optional[Any] = None,
        send_reports: bool = True,
    ) -> Dict[str, Any]:
        """
        Publish content to multiple platforms with optional scheduling

        Args:
            caption: Post text content
            link: Optional source URL
            image_url: Optional image URL (public, for non-Telegram platforms)
            image_local_path: Optional local image path (for Telegram only)
            platforms: List of platforms to publish to (None = all enabled)
            telegram_context: Telegram bot context (required for Telegram)
            send_reports: Whether to send progress reports to admin

        Returns:
            Dict with results per platform
        """
        start_time = time.time()
        target_platforms = platforms or self.enabled_platforms
        results = {}

        payloads = platform_payloads or {}

        # Send start report
        if send_reports and self.reporter:
            await self.reporter.report_post_start(
                total_platforms=len(target_platforms),
                caption_preview=caption,
            )

        for platform in target_platforms:
            try:
                payload = payloads.get(platform) if isinstance(payloads, dict) else None
                caption_for_platform = (
                    str(payload.get("caption", "")).strip()
                    if isinstance(payload, dict) and payload.get("caption") is not None
                    else caption
                )
                title_for_platform = (
                    str(payload.get("title", "")).strip()
                    if isinstance(payload, dict) and payload.get("title") is not None
                    else ""
                )

                # Image handling: Use local path for Telegram/Facebook, public URL for others
                image_for_platform = image_url
                local_image_path_for_platform = None

                if platform == "telegram" and image_local_path:
                    # Telegram can use local paths
                    image_for_platform = image_local_path
                elif platform == "facebook":
                    # Facebook handles both, prefers local if available
                    if image_local_path:
                        local_image_path_for_platform = image_local_path

                    if image_url and image_url.lower().startswith("http"):
                        image_for_platform = image_url
                    else:
                        image_for_platform = None

                elif platform != "telegram":
                    # Other platforms need public URLs only
                    if image_url and image_url.lower().startswith("http"):
                        image_for_platform = image_url
                    else:
                        image_for_platform = None

                # Small delay between platforms to prevent rate limiting
                # (skip delay for the first platform)
                if results:  # Not the first platform
                    time.sleep(PLATFORM_DELAY_SECONDS)

                # Publish immediately to this platform
                if platform == "telegram":
                    result = await self._publish_telegram(
                        caption_for_platform, link, image_for_platform, telegram_context
                    )
                    results["telegram"] = result

                elif platform == "linkedin":
                    result = self._publish_linkedin(
                        caption_for_platform, link, image_for_platform
                    )
                    results["linkedin"] = result

                elif platform == "discord":
                    result = self._publish_discord(
                        caption_for_platform, link, image_for_platform
                    )
                    results["discord"] = result

                elif platform == "medium":
                    result = self._publish_medium(
                        caption_for_platform, link, image_for_platform
                    )
                    results["medium"] = result

                elif platform == "twitter":
                    result = self._publish_twitter(
                        caption_for_platform, link, image_for_platform
                    )
                    results["twitter"] = result

                elif platform == "blogger":
                    result = self._publish_blogger(
                        caption_for_platform,
                        link,
                        image_for_platform,
                        title_override=title_for_platform or None,
                    )
                    results["blogger"] = result

                elif platform == "reddit":
                    result = self._publish_reddit(
                        caption_for_platform, link, image_for_platform
                    )
                    results["reddit"] = result

                elif platform == "facebook":
                    result = self._publish_facebook(
                        caption_for_platform,
                        link,
                        image_for_platform,
                        image_path=local_image_path_for_platform,
                    )
                    results["facebook"] = result

                elif platform == "devto":
                    result = self._publish_devto(
                        caption_for_platform,
                        link,
                        image_for_platform,
                        title_override=title_for_platform or None,
                    )
                    results["devto"] = result

                # Send success report
                if send_reports and self.reporter:
                    post_url = result.get("url") if isinstance(result, dict) else None
                    if result.get("status") == "success" or result.get("success"):
                        await self.reporter.report_platform_success(
                            platform=platform,
                            post_url=post_url,
                        )
                    else:
                        error_msg = result.get("error") or result.get(
                            "message", "Unknown error"
                        )
                        await self.reporter.report_platform_failure(
                            platform=platform,
                            error=error_msg,
                        )

            except Exception as e:
                results[platform] = {"status": "error", "error": str(e)}

                # Send failure report
                if send_reports and self.reporter:
                    await self.reporter.report_platform_failure(
                        platform=platform,
                        error=str(e),
                    )

        # Send completion report
        if send_reports and self.reporter:
            successful = sum(
                1
                for r in results.values()
                if isinstance(r, dict)
                and (r.get("status") == "success" or r.get("success"))
            )
            failed = len(results) - successful
            duration = time.time() - start_time

            await self.reporter.report_post_complete(
                successful=successful,
                failed=failed,
                total=len(results),
                duration_seconds=duration,
            )

        return results

    async def _publish_telegram(
        self, caption: str, link: Optional[str], image_url: Optional[str], context: Any
    ) -> Dict[str, Any]:
        """Publish to Telegram (existing logic)"""
        channel_id = os.getenv("CHANNEL_ID")
        if not channel_id:
            raise ValueError("CHANNEL_ID is not set")
        if context is None:
            raise ValueError("telegram_context is required for Telegram publishing")

        def _compose_text(c: str, _l: Optional[str], has_photo: bool) -> str:
            # DO NOT append links inside the body (handled programmatically)
            base = c
            limit = 1024 if has_photo else 4096
            if len(base) > limit:
                ellipsis = "…"
                return base[: limit - 1] + ellipsis
            return base

        text = _compose_text(caption, link, bool(image_url))

        reply_markup = None
        if link:
            try:
                from telegram import InlineKeyboardButton, InlineKeyboardMarkup

                reply_markup = InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🔗 اقرأ التفاصيل", url=link)]]
                )
            except Exception:
                reply_markup = None

        if image_url:
            try:
                await context.bot.send_photo(
                    chat_id=channel_id,
                    photo=image_url,
                    caption=text,
                    reply_markup=reply_markup,
                )
            except Exception:
                await context.bot.send_message(
                    chat_id=channel_id,
                    text=text,
                    reply_markup=reply_markup,
                )
        else:
            await context.bot.send_message(
                chat_id=channel_id,
                text=text,
                reply_markup=reply_markup,
            )

        return {"status": "success", "platform": "telegram"}

    def _publish_linkedin(
        self, caption: str, link: Optional[str], image_url: Optional[str]
    ) -> Dict[str, Any]:
        """Publish to LinkedIn"""
        from linkedin_publisher import LinkedInPublisher

        publisher = LinkedInPublisher()

        # Choose best LinkedIn format based on content
        if image_url:
            # Post with image
            return publisher.publish_image_post(caption, image_url, link)
        elif link:
            # Article share with preview
            return publisher.publish_article(caption, link)
        else:
            # Text-only post
            return publisher.publish_text_post(caption, link)

    def _publish_discord(
        self, caption: str, link: Optional[str], image_url: Optional[str]
    ) -> Dict[str, Any]:
        """Publish to Discord via webhook"""
        from discord_publisher import DiscordPublisher

        publisher = DiscordPublisher()
        return publisher.publish(caption=caption, link=link, image_url=image_url)

    def _publish_medium(
        self, caption: str, link: Optional[str], image_url: Optional[str]
    ) -> Dict[str, Any]:
        """Publish to Medium"""
        from medium_publisher import MediumPublisher

        publisher = MediumPublisher()
        return publisher.publish_article(
            title=caption[:80], content=caption, canonical_url=link, image_url=image_url
        )

    def _publish_twitter(
        self, caption: str, link: Optional[str], image_url: Optional[str]
    ) -> Dict[str, Any]:
        """Publish to Twitter/X"""
        from twitter_publisher import TwitterPublisher

        publisher = TwitterPublisher()
        # Compose tweet text with link if not already included
        tweet_text = (
            caption
            if (link and link in caption)
            else f"{caption}\n\n{link}" if link else caption
        )
        return publisher.publish_tweet(text=tweet_text, image_url=image_url)

    def _publish_blogger(
        self,
        caption: str,
        link: Optional[str],
        image_url: Optional[str],
        *,
        title_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Publish to Blogger"""
        from blogger_publisher import BloggerPublisher

        publisher = BloggerPublisher()
        # Extract title from caption (first line or first 100 chars)
        if title_override and title_override.strip():
            title = title_override.strip()[:100]
        else:
            lines = caption.split("\n")
            title = lines[0][:100] if lines else caption[:100]
        # Add AI/Tech label by default
        labels = ["AI", "Technology", "Tech News"]
        return publisher.publish_post(
            title=title, caption=caption, link=link, image_url=image_url, labels=labels
        )

    def _publish_reddit(
        self, caption: str, link: Optional[str], image_url: Optional[str]
    ) -> Dict[str, Any]:
        """Publish to Reddit"""
        from reddit_publisher import RedditPublisher

        publisher = RedditPublisher()
        # Get target subreddit from env (default to a tech subreddit)
        subreddit = os.getenv("REDDIT_SUBREDDIT", "technology")

        # Extract title from caption (first line or first 200 chars)
        lines = caption.split("\n")
        title = lines[0][:250] if lines else caption[:250]

        # If we have a link, post as link submission
        if link:
            return publisher.submit_link(subreddit=subreddit, title=title, url=link)
        else:
            # Post as text submission with full caption
            return publisher.submit_text(subreddit=subreddit, title=title, text=caption)

    def _publish_facebook(
        self,
        caption: str,
        link: Optional[str],
        image_url: Optional[str],
        image_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Publish to Facebook Page"""
        from facebook_publisher import FacebookPublisher

        publisher = FacebookPublisher()

        # Facebook prefers photo posts over link posts for engagement
        if image_path or image_url:
            # Post with photo (caption + image)
            return publisher.publish_photo(
                message=caption, image_url=image_url, image_path=image_path
            )
        elif link:
            # Post with link preview
            return publisher.publish_link(message=caption, link=link)
        else:
            # Text-only post
            return publisher.publish_text(message=caption)

    def _publish_devto(
        self,
        caption: str,
        link: str,
        image_url: str,
        *,
        title_override: Optional[str] = None,
    ):
        """Publish to Dev.to"""
        from devto_publisher import DevtoPublisher

        publisher = DevtoPublisher()
        return publisher.publish(
            caption=caption,
            title=title_override,
            link=link,
            image_url=image_url,
        )

    def get_platform_status(self) -> Dict[str, bool]:
        """Check which platforms are configured and ready"""
        status = {}

        # Telegram
        status["telegram"] = bool(os.getenv("TELEGRAM_TOKEN"))

        # LinkedIn
        if os.getenv("LINKEDIN_ACCESS_TOKEN"):
            try:
                from linkedin_publisher import test_linkedin_connection

                status["linkedin"] = test_linkedin_connection()
            except Exception:
                status["linkedin"] = False
        else:
            status["linkedin"] = False

        # Discord
        if os.getenv("DISCORD_WEBHOOK_URL"):
            try:
                from discord_publisher import test_discord_connection

                status["discord"] = test_discord_connection()
            except Exception:
                status["discord"] = False
        else:
            status["discord"] = False

        # Medium
        if os.getenv("MEDIUM_INTEGRATION_TOKEN") and os.getenv("MEDIUM_USER_ID"):
            try:
                from medium_publisher import test_medium_connection

                status["medium"] = test_medium_connection()
            except Exception:
                status["medium"] = False
        else:
            status["medium"] = False

        # Twitter
        if all(
            [
                os.getenv("TWITTER_API_KEY"),
                os.getenv("TWITTER_API_SECRET"),
                os.getenv("TWITTER_ACCESS_TOKEN"),
                os.getenv("TWITTER_ACCESS_SECRET"),
            ]
        ):
            try:
                from twitter_publisher import test_twitter_connection

                status["twitter"] = test_twitter_connection()
            except Exception:
                status["twitter"] = False
        else:
            status["twitter"] = False

        # Blogger
        if os.getenv("BLOGGER_BLOG_ID") and (
            os.getenv("BLOGGER_API_KEY") or os.getenv("BLOGGER_ACCESS_TOKEN")
        ):
            try:
                from blogger_publisher import BloggerPublisher

                publisher = BloggerPublisher()
                result = publisher.test_connection()
                status["blogger"] = result.get("success", False)
            except Exception:
                status["blogger"] = False
        else:
            status["blogger"] = False

        # Reddit
        if all(
            [
                os.getenv("REDDIT_CLIENT_ID"),
                os.getenv("REDDIT_CLIENT_SECRET"),
                os.getenv("REDDIT_USERNAME"),
                os.getenv("REDDIT_PASSWORD"),
            ]
        ):
            try:
                from reddit_publisher import RedditPublisher

                publisher = RedditPublisher()
                result = publisher.test_connection()
                status["reddit"] = result.get("success", False)
            except Exception:
                status["reddit"] = False
        else:
            status["reddit"] = False

        # Facebook
        if os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN") and os.getenv("FACEBOOK_PAGE_ID"):
            try:
                from facebook_publisher import FacebookPublisher

                publisher = FacebookPublisher()
                result = publisher.test_connection()
                status["facebook"] = result.get("success", False)
            except Exception:
                status["facebook"] = False
        else:
            status["facebook"] = False

        # Dev.to
        if os.getenv("DEVTO_API_KEY"):
            try:
                from devto_publisher import DevtoPublisher

                publisher = DevtoPublisher()
                status["devto"] = publisher.is_configured()
            except Exception:
                status["devto"] = False
        else:
            status["devto"] = False

        return status
