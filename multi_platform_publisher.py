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
]


class MultiPlatformPublisher:
    """Publish content to multiple platforms from a single interface"""

    def __init__(self, use_scheduler: bool = False):
        self.enabled_platforms = self._get_enabled_platforms()
        self.use_scheduler = use_scheduler
        self.scheduler = None
        self.reporter = None

        if use_scheduler:
            try:
                from publishing_scheduler import PublishingScheduler
                from publishing_reporter import get_reporter

                self.scheduler = PublishingScheduler()
                self.reporter = get_reporter()
            except Exception as e:
                print(f"Failed to initialize scheduler: {e}")
                self.use_scheduler = False

    def _get_enabled_platforms(self) -> list[PlatformType]:
        """Detect which platforms are configured"""
        platforms: list[PlatformType] = []

        # Telegram is always enabled (base platform)
        if os.getenv("TELEGRAM_TOKEN"):
            platforms.append("telegram")

        # LinkedIn is optional
        if os.getenv("LINKEDIN_ACCESS_TOKEN"):
            platforms.append("linkedin")

        # Discord (webhook-based)
        if os.getenv("DISCORD_WEBHOOK_URL"):
            platforms.append("discord")

        # Medium (requires token + user ID)
        if os.getenv("MEDIUM_INTEGRATION_TOKEN") and os.getenv("MEDIUM_USER_ID"):
            platforms.append("medium")

        # Twitter/X (requires OAuth 1.0a credentials)
        if all(
            [
                os.getenv("TWITTER_API_KEY"),
                os.getenv("TWITTER_API_SECRET"),
                os.getenv("TWITTER_ACCESS_TOKEN"),
                os.getenv("TWITTER_ACCESS_SECRET"),
            ]
        ):
            platforms.append("twitter")

        # Blogger (requires Blog ID and API key or OAuth)
        if os.getenv("BLOGGER_BLOG_ID") and (
            os.getenv("BLOGGER_API_KEY") or os.getenv("BLOGGER_ACCESS_TOKEN")
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
        ):
            platforms.append("reddit")

        # Facebook (requires Page Access Token and Page ID)
        if os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN") and os.getenv("FACEBOOK_PAGE_ID"):
            platforms.append("facebook")

        return platforms

        return platforms

    async def publish(
        self,
        caption: str,
        link: Optional[str] = None,
        image_url: Optional[str] = None,
        platforms: Optional[list[PlatformType]] = None,
        telegram_context: Optional[Any] = None,
        send_reports: bool = True,
    ) -> Dict[str, Any]:
        """
        Publish content to multiple platforms with optional scheduling

        Args:
            caption: Post text content
            link: Optional source URL
            image_url: Optional image URL
            platforms: List of platforms to publish to (None = all enabled)
            telegram_context: Telegram bot context (required for Telegram)
            send_reports: Whether to send progress reports to admin

        Returns:
            Dict with results per platform
        """
        start_time = time.time()
        target_platforms = platforms or self.enabled_platforms
        results = {}

        # Send start report
        if send_reports and self.reporter:
            await self.reporter.report_post_start(
                total_platforms=len(target_platforms),
                caption_preview=caption,
            )

        for platform in target_platforms:
            try:
                # Check if we should delay this platform
                if self.scheduler and self.use_scheduler:
                    config = self.scheduler.get_platform_config(platform)
                    if (
                        config
                        and config.publish_mode == "delayed"
                        and config.delay_minutes > 0
                    ):
                        # Schedule for later
                        scheduled_post = self.scheduler.schedule_post(
                            platform=platform,
                            caption=caption,
                            link=link,
                            image_url=image_url,
                        )

                        results[platform] = {
                            "status": "scheduled",
                            "scheduled_time": scheduled_post.scheduled_time.isoformat(),
                            "delay_minutes": config.delay_minutes,
                        }

                        # Send schedule report
                        if send_reports and self.reporter:
                            await self.reporter.report_scheduled_post(
                                platform=platform,
                                scheduled_time=scheduled_post.scheduled_time,
                            )

                        continue

                # Publish immediately
                if platform == "telegram":
                    result = await self._publish_telegram(
                        caption, link, image_url, telegram_context
                    )
                    results["telegram"] = result

                elif platform == "linkedin":
                    result = self._publish_linkedin(caption, link, image_url)
                    results["linkedin"] = result

                elif platform == "discord":
                    result = self._publish_discord(caption, link, image_url)
                    results["discord"] = result

                elif platform == "medium":
                    result = self._publish_medium(caption, link, image_url)
                    results["medium"] = result

                elif platform == "twitter":
                    result = self._publish_twitter(caption, link, image_url)
                    results["twitter"] = result

                elif platform == "blogger":
                    result = self._publish_blogger(caption, link, image_url)
                    results["blogger"] = result

                elif platform == "reddit":
                    result = self._publish_reddit(caption, link, image_url)
                    results["reddit"] = result

                elif platform == "facebook":
                    result = self._publish_facebook(caption, link, image_url)
                    results["facebook"] = result

                # Send success report
                if send_reports and self.reporter:
                    post_url = result.get("url") if isinstance(result, dict) else None
                    if result.get("status") == "success" or result.get("success"):
                        await self.reporter.report_platform_success(
                            platform=platform,
                            post_url=post_url,
                        )
                    else:
                        error_msg = result.get("error") or result.get("message", "Unknown error")
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
                1 for r in results.values()
                if isinstance(r, dict) and (r.get("status") in ["success", "scheduled"] or r.get("success"))
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

        def _compose_text(c: str, l: Optional[str], has_photo: bool) -> str:
            base = (
                c
                if (l and l in c)
                else (c + (f"\n\n🔗 لينك الخبر/الأداة: {l}" if l else ""))
            )
            limit = 1024 if has_photo else 4096
            if len(base) > limit:
                ellipsis = "…"
                if l and l in base:
                    keep_tail = base[-120:]
                    head = base[: limit - len(keep_tail) - 1]
                    return head + ellipsis + keep_tail
                return base[: limit - 1] + ellipsis
            return base

        text = _compose_text(caption, link, bool(image_url))

        if image_url:
            try:
                await context.bot.send_photo(
                    chat_id=channel_id, photo=image_url, caption=text
                )
            except Exception:
                await context.bot.send_message(chat_id=channel_id, text=text)
        else:
            await context.bot.send_message(chat_id=channel_id, text=text)

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
        self, caption: str, link: Optional[str], image_url: Optional[str]
    ) -> Dict[str, Any]:
        """Publish to Blogger"""
        from blogger_publisher import BloggerPublisher

        publisher = BloggerPublisher()
        # Extract title from caption (first line or first 100 chars)
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
        self, caption: str, link: Optional[str], image_url: Optional[str]
    ) -> Dict[str, Any]:
        """Publish to Facebook Page"""
        from facebook_publisher import FacebookPublisher

        publisher = FacebookPublisher()

        # Facebook prefers photo posts over link posts for engagement
        if image_url:
            # Post with photo (caption + image)
            return publisher.publish_photo(message=caption, image_url=image_url)
        elif link:
            # Post with link preview
            return publisher.publish_link(message=caption, link=link)
        else:
            # Text-only post
            return publisher.publish_text(message=caption)

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

        return status
