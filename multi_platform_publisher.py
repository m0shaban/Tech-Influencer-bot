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

from brand_context import get_active_brand, env_get, has_env

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
        self.active_brand = get_active_brand()
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

            # Apply brand overrides from config.json (if present)
            cfg_path = Path(__file__).parent / "config.json"
            if cfg_path.exists():
                cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
                if isinstance(cfg, dict):
                    active_key = str(cfg.get("active_brand") or "").strip()
                    brands = cfg.get("brands") if isinstance(cfg.get("brands"), dict) else {}
                    brand = brands.get(active_key) if active_key and isinstance(brands, dict) else None
                    if isinstance(brand, dict) and isinstance(brand.get("platforms"), dict):
                        for k, v in brand["platforms"].items():
                            if isinstance(v, dict) and "enabled" in v:
                                config_enabled[k] = bool(v.get("enabled"))
        except Exception as e:
            print(f"⚠️ Failed to load platform_config.json: {e}")

        def is_enabled(name):
            # Default to True if not in config, otherwise use config value
            return config_enabled.get(name, True)

        # Telegram is always enabled (base platform)
        if has_env("TELEGRAM_TOKEN", platform="telegram", brand=self.active_brand) and is_enabled("telegram"):
            platforms.append("telegram")

        # LinkedIn is optional
        if has_env("LINKEDIN_ACCESS_TOKEN", platform="linkedin", brand=self.active_brand) and is_enabled("linkedin"):
            platforms.append("linkedin")

        # Discord (webhook-based)
        if has_env("DISCORD_WEBHOOK_URL", platform="discord", brand=self.active_brand) and is_enabled("discord"):
            platforms.append("discord")

        # Medium (requires token + user ID)
        if (
            has_env("MEDIUM_INTEGRATION_TOKEN", platform="medium", brand=self.active_brand)
            and has_env("MEDIUM_USER_ID", platform="medium", brand=self.active_brand)
            and is_enabled("medium")
        ):
            platforms.append("medium")

        # Twitter/X (requires OAuth 1.0a credentials)
        if all(
            [
                has_env("TWITTER_API_KEY", platform="twitter", brand=self.active_brand),
                has_env("TWITTER_API_SECRET", platform="twitter", brand=self.active_brand),
                has_env("TWITTER_ACCESS_TOKEN", platform="twitter", brand=self.active_brand),
                has_env("TWITTER_ACCESS_SECRET", platform="twitter", brand=self.active_brand),
            ]
        ) and is_enabled("twitter"):
            platforms.append("twitter")

        # Blogger (requires Blog ID and API key or OAuth)
        if (
            has_env("BLOGGER_BLOG_ID", platform="blogger", brand=self.active_brand)
            and (
                has_env("BLOGGER_API_KEY", platform="blogger", brand=self.active_brand)
                or has_env("BLOGGER_ACCESS_TOKEN", platform="blogger", brand=self.active_brand)
            )
            and is_enabled("blogger")
        ):
            platforms.append("blogger")

        # Reddit (requires OAuth credentials)
        if all(
            [
                has_env("REDDIT_CLIENT_ID", platform="reddit", brand=self.active_brand),
                has_env("REDDIT_CLIENT_SECRET", platform="reddit", brand=self.active_brand),
                has_env("REDDIT_USERNAME", platform="reddit", brand=self.active_brand),
                has_env("REDDIT_PASSWORD", platform="reddit", brand=self.active_brand),
            ]
        ) and is_enabled("reddit"):
            platforms.append("reddit")

        # Facebook (requires Page Access Token and Page ID)
        if (
            has_env("FACEBOOK_PAGE_ACCESS_TOKEN", platform="facebook", brand=self.active_brand)
            and has_env("FACEBOOK_PAGE_ID", platform="facebook", brand=self.active_brand)
            and is_enabled("facebook")
        ):
            platforms.append("facebook")

        # Dev.to (requires API key)
        if has_env("DEVTO_API_KEY", platform="devto", brand=self.active_brand) and is_enabled("devto"):
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

                link_for_platform: Optional[str] = link
                cta_buttons = None
                force_link_post = False
                if isinstance(payload, dict):
                    if payload.get("disable_link"):
                        link_for_platform = None
                    elif payload.get("link_override") is not None:
                        link_for_platform = (
                            str(payload.get("link_override") or "").strip() or None
                        )
                    cta_buttons = payload.get("cta_buttons")
                    force_link_post = bool(payload.get("force_link_post"))

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

                    # Some workflows want link-preview posts even when an image exists.
                    if force_link_post:
                        image_for_platform = None
                        local_image_path_for_platform = None

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
                        caption_for_platform,
                        link_for_platform,
                        image_for_platform,
                        telegram_context,
                        cta_buttons=cta_buttons,
                        channel_id_override=(
                            str(payload.get("channel_id") or "").strip()
                            if isinstance(payload, dict)
                            else None
                        ),
                    )
                    results["telegram"] = result

                elif platform == "linkedin":
                    result = self._publish_linkedin(
                        caption_for_platform, link_for_platform, image_for_platform
                    )
                    results["linkedin"] = result

                elif platform == "discord":
                    result = self._publish_discord(
                        caption_for_platform, link_for_platform, image_for_platform
                    )
                    results["discord"] = result

                elif platform == "medium":
                    result = self._publish_medium(
                        caption_for_platform, link_for_platform, image_for_platform
                    )
                    results["medium"] = result

                elif platform == "twitter":
                    result = self._publish_twitter(
                        caption_for_platform, link_for_platform, image_for_platform
                    )
                    results["twitter"] = result

                elif platform == "blogger":
                    result = self._publish_blogger(
                        caption_for_platform,
                        link_for_platform,
                        image_for_platform,
                        title_override=title_for_platform or None,
                    )
                    results["blogger"] = result

                elif platform == "reddit":
                    result = self._publish_reddit(
                        caption_for_platform, link_for_platform, image_for_platform
                    )
                    results["reddit"] = result

                elif platform == "facebook":
                    result = self._publish_facebook(
                        caption_for_platform,
                        link_for_platform,
                        image_for_platform,
                        image_path=local_image_path_for_platform,
                    )
                    results["facebook"] = result

                elif platform == "devto":
                    result = self._publish_devto(
                        caption_for_platform,
                        link_for_platform,
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
        self,
        caption: str,
        link: Optional[str],
        image_url: Optional[str],
        context: Any,
        *,
        cta_buttons: Optional[Any] = None,
        channel_id_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Publish to Telegram (existing logic)"""
        channel_id = (channel_id_override or os.getenv("CHANNEL_ID") or "").strip()
        if not channel_id:
            raise ValueError("CHANNEL_ID is not set")

        # Multi-account support: allow a per-brand TELEGRAM_TOKEN_<SUFFIX>.
        token_override = env_get("TELEGRAM_TOKEN", platform="telegram", brand=self.active_brand)
        bot = None
        if token_override and str(token_override).strip():
            try:
                from telegram import Bot

                bot = Bot(token=str(token_override).strip())
            except Exception:
                bot = None
        if bot is None:
            if context is None or not hasattr(context, "bot"):
                raise ValueError("telegram_context is required for Telegram publishing")
            bot = context.bot

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
        try:
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup

            buttons = []
            if isinstance(cta_buttons, list):
                for item in cta_buttons:
                    if isinstance(item, dict):
                        text = str(item.get("text", "")).strip()
                        url = str(item.get("url", "")).strip()
                        if text and url:
                            buttons.append((text, url))
                    elif isinstance(item, (list, tuple)) and len(item) >= 2:
                        text = str(item[0]).strip()
                        url = str(item[1]).strip()
                        if text and url:
                            buttons.append((text, url))

            if buttons:
                rows = []
                for i in range(0, len(buttons), 2):
                    row = [InlineKeyboardButton(buttons[i][0], url=buttons[i][1])]
                    if i + 1 < len(buttons):
                        row.append(
                            InlineKeyboardButton(
                                buttons[i + 1][0], url=buttons[i + 1][1]
                            )
                        )
                    rows.append(row)
                reply_markup = InlineKeyboardMarkup(rows)
            elif link:
                reply_markup = InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🔗 اقرأ التفاصيل", url=link)]]
                )
        except Exception:
            reply_markup = None

        if image_url:
            try:
                await bot.send_photo(
                    chat_id=channel_id,
                    photo=image_url,
                    caption=text,
                    reply_markup=reply_markup,
                )
            except Exception:
                await bot.send_message(
                    chat_id=channel_id,
                    text=text,
                    reply_markup=reply_markup,
                )
        else:
            await bot.send_message(
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

        webhook = env_get("DISCORD_WEBHOOK_URL", platform="discord", brand=self.active_brand)
        username = env_get("DISCORD_USERNAME", platform="discord", brand=self.active_brand)
        avatar = env_get("DISCORD_AVATAR_URL", platform="discord", brand=self.active_brand)
        publisher = DiscordPublisher(webhook_url=webhook, username=username, avatar_url=avatar)
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

        publisher = BloggerPublisher(
            api_key=env_get("BLOGGER_API_KEY", platform="blogger", brand=self.active_brand),
            blog_id=env_get("BLOGGER_BLOG_ID", platform="blogger", brand=self.active_brand),
            access_token=env_get("BLOGGER_ACCESS_TOKEN", platform="blogger", brand=self.active_brand),
            refresh_token=env_get("BLOGGER_REFRESH_TOKEN", platform="blogger", brand=self.active_brand),
            client_id=env_get("BLOGGER_CLIENT_ID", platform="blogger", brand=self.active_brand),
            client_secret=env_get("BLOGGER_CLIENT_SECRET", platform="blogger", brand=self.active_brand),
        )
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

        publisher = FacebookPublisher(
            access_token=env_get("FACEBOOK_PAGE_ACCESS_TOKEN", platform="facebook", brand=self.active_brand),
            page_id=env_get("FACEBOOK_PAGE_ID", platform="facebook", brand=self.active_brand),
        )

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
        link: Optional[str],
        image_url: Optional[str],
        *,
        title_override: Optional[str] = None,
    ):
        """Publish to Dev.to"""
        from devto_publisher import DevtoPublisher

        publisher = DevtoPublisher(api_key=env_get("DEVTO_API_KEY", platform="devto", brand=self.active_brand))
        return publisher.publish(
            caption=caption,
            title=title_override,
            link=link or "",
            image_url=image_url,
        )

    def get_platform_status(self) -> Dict[str, bool]:
        """Check which platforms are configured and ready"""
        status = {}

        # Telegram
        status["telegram"] = has_env("TELEGRAM_TOKEN", platform="telegram", brand=self.active_brand)

        # LinkedIn
        if has_env("LINKEDIN_ACCESS_TOKEN", platform="linkedin", brand=self.active_brand):
            try:
                from linkedin_publisher import test_linkedin_connection

                status["linkedin"] = test_linkedin_connection()
            except Exception:
                status["linkedin"] = False
        else:
            status["linkedin"] = False

        # Discord
        if has_env("DISCORD_WEBHOOK_URL", platform="discord", brand=self.active_brand):
            try:
                from discord_publisher import test_discord_connection

                status["discord"] = test_discord_connection()
            except Exception:
                status["discord"] = False
        else:
            status["discord"] = False

        # Medium
        if has_env("MEDIUM_INTEGRATION_TOKEN", platform="medium", brand=self.active_brand) and has_env("MEDIUM_USER_ID", platform="medium", brand=self.active_brand):
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
                has_env("TWITTER_API_KEY", platform="twitter", brand=self.active_brand),
                has_env("TWITTER_API_SECRET", platform="twitter", brand=self.active_brand),
                has_env("TWITTER_ACCESS_TOKEN", platform="twitter", brand=self.active_brand),
                has_env("TWITTER_ACCESS_SECRET", platform="twitter", brand=self.active_brand),
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
        if has_env("BLOGGER_BLOG_ID", platform="blogger", brand=self.active_brand) and (
            has_env("BLOGGER_API_KEY", platform="blogger", brand=self.active_brand)
            or has_env("BLOGGER_ACCESS_TOKEN", platform="blogger", brand=self.active_brand)
        ):
            try:
                from blogger_publisher import BloggerPublisher

                publisher = BloggerPublisher(
                    api_key=env_get("BLOGGER_API_KEY", platform="blogger", brand=self.active_brand),
                    blog_id=env_get("BLOGGER_BLOG_ID", platform="blogger", brand=self.active_brand),
                    access_token=env_get("BLOGGER_ACCESS_TOKEN", platform="blogger", brand=self.active_brand),
                    refresh_token=env_get("BLOGGER_REFRESH_TOKEN", platform="blogger", brand=self.active_brand),
                    client_id=env_get("BLOGGER_CLIENT_ID", platform="blogger", brand=self.active_brand),
                    client_secret=env_get("BLOGGER_CLIENT_SECRET", platform="blogger", brand=self.active_brand),
                )
                result = publisher.test_connection()
                status["blogger"] = result.get("success", False)
            except Exception:
                status["blogger"] = False
        else:
            status["blogger"] = False

        # Reddit
        if all(
            [
                has_env("REDDIT_CLIENT_ID", platform="reddit", brand=self.active_brand),
                has_env("REDDIT_CLIENT_SECRET", platform="reddit", brand=self.active_brand),
                has_env("REDDIT_USERNAME", platform="reddit", brand=self.active_brand),
                has_env("REDDIT_PASSWORD", platform="reddit", brand=self.active_brand),
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
        if has_env("FACEBOOK_PAGE_ACCESS_TOKEN", platform="facebook", brand=self.active_brand) and has_env("FACEBOOK_PAGE_ID", platform="facebook", brand=self.active_brand):
            try:
                from facebook_publisher import FacebookPublisher

                publisher = FacebookPublisher(
                    access_token=env_get("FACEBOOK_PAGE_ACCESS_TOKEN", platform="facebook", brand=self.active_brand),
                    page_id=env_get("FACEBOOK_PAGE_ID", platform="facebook", brand=self.active_brand),
                )
                result = publisher.test_connection()
                status["facebook"] = result.get("success", False)
            except Exception:
                status["facebook"] = False
        else:
            status["facebook"] = False

        # Dev.to
        if has_env("DEVTO_API_KEY", platform="devto", brand=self.active_brand):
            try:
                from devto_publisher import DevtoPublisher

                publisher = DevtoPublisher(api_key=env_get("DEVTO_API_KEY", platform="devto", brand=self.active_brand))
                status["devto"] = publisher.is_configured()
            except Exception:
                status["devto"] = False
        else:
            status["devto"] = False

        return status
