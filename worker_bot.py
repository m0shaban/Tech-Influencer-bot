"""
Worker Bot Module - Brand Agent Implementation
==============================================

Each brand runs as an independent Telegram bot that:
1. Fetches content from RSS feeds
2. Generates native, high-value content using AI
3. Posts directly to its designated channel
4. Operates autonomously with its own schedule
5. Reports errors to Master Controller for admin alerts

This module implements the "Worker" pattern in the Hub-and-Spoke architecture.
"""

import asyncio
import json
import os
import random
import threading
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Callable

from telegram import Update, ReplyKeyboardMarkup, Bot
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from brands_config import (
    BrandConfig,
    PublishingMode,
    get_brand_configs,
    get_brand_by_key,
    ADMIN_USER_ID,
    MASTER_BOT_TOKEN,
)


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
SEEN_POSTS_PATH = DATA_DIR / "seen_posts.json"


# ============================================================
# CROSS-BOT ERROR ALERTING SYSTEM
# ============================================================


async def send_alert_to_admin(brand_key: str, error_message: str, tb: str = "") -> None:
    """
    Send error alert to admin via the Master Bot.
    This allows workers to notify admin even if they crash.
    """
    if not MASTER_BOT_TOKEN or not ADMIN_USER_ID:
        return

    try:
        master_bot = Bot(token=MASTER_BOT_TOKEN)

        alert_text = f"""🚨 **WORKER ALERT** 🚨
═══════════════════════

⚠️ Brand: **{brand_key}**
🕐 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

❌ **Error:**
{error_message[:500]}
"""
        if tb:
            alert_text += f"""
📋 **Traceback:**
```
{tb[:1000]}
```"""

        await master_bot.send_message(
            chat_id=ADMIN_USER_ID,
            text=alert_text,
            parse_mode="Markdown",
        )
    except Exception as e:
        # Fail silently - don't crash if alert fails
        try:
            print(f"[ALERT] Failed to send alert: {e}")
        except:
            pass


def send_alert_sync(brand_key: str, error_message: str, tb: str = "") -> None:
    """Synchronous wrapper for send_alert_to_admin."""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(send_alert_to_admin(brand_key, error_message, tb))
        loop.close()
    except Exception:
        pass


def _get_worker_keyboard() -> ReplyKeyboardMarkup:
    """Keyboard for brand worker bots."""
    return ReplyKeyboardMarkup(
        [
            ["⚡ Force Fetch", "📊 Stats"],
            ["📡 Feeds", "🧪 Test"],
            ["ℹ️ Info", "📋 Logs"],
        ],
        resize_keyboard=True,
    )


def _is_admin(update: Update) -> bool:
    """Check if user is admin."""
    return bool(update.effective_user and update.effective_user.id == ADMIN_USER_ID)


class BrandWorker:
    """
    Independent worker bot for a single brand.

    Responsibilities:
    - Content fetching from RSS
    - AI content generation (native posts)
    - Publishing to Telegram channel
    - Optional cross-platform publishing
    """

    def __init__(self, brand: BrandConfig):
        self.brand = brand
        self.app: Optional[Application] = None
        self.is_running = False
        self.posts_today = 0
        self.last_post_time: Optional[datetime] = None

    def _log(self, message: str) -> None:
        """Safe logging that handles Unicode on Windows."""
        try:
            print(f"[{self.brand.key}] {message}")
        except UnicodeEncodeError:
            # Fallback for Windows console
            safe_msg = message.encode("ascii", "replace").decode("ascii")
            print(f"[{self.brand.key}] {safe_msg}")

    async def _fetch_and_generate_native_content(
        self, context: ContextTypes.DEFAULT_TYPE
    ) -> Dict[str, Any]:
        """
        Fetch news and generate NATIVE Telegram content.

        This is the key difference from the old system:
        - Content is generated specifically for Telegram
        - Full value is delivered in the post
        - No "read more" links - the post IS the product
        """
        from feed_manager import fetch_random_new_post
        from ai_processor import rewrite_with_ai

        # Fetch new article
        feed_item = fetch_random_new_post(brand=self.brand.key)
        if not feed_item:
            return {"status": "no_news", "error": "No new articles found"}

        title = feed_item.get("title", "")
        summary = feed_item.get("summary", "")
        link = feed_item.get("link", "")

        self._log(f"Processing: {title[:50]}...")

        # Generate native Telegram content using brand persona
        content_data = rewrite_with_ai(
            title=title,
            summary=summary,
            link=link,
            system_prompt=self._get_native_prompt(),
            platform="telegram",
            brand_name=self.brand.key,
            brand_language=self.brand.language,
        )

        if not content_data:
            return {"status": "error", "error": "AI generation failed"}

        # Extract the native post
        telegram_post = content_data.get("telegram_post", "")
        if not telegram_post:
            # Fallback: Generate a simple but valuable post
            telegram_post = self._generate_fallback_post(title, summary)

        return {
            "status": "success",
            "content": telegram_post,
            "title": title,
            "link": link,
            "feed_item": feed_item,
            "content_data": content_data,
        }

    def _get_native_prompt(self) -> str:
        """
        Get the system prompt optimized for NATIVE Telegram content.
        This enforces the "full value in post" requirement.
        """
        base_prompt = self.brand.system_prompt

        native_enforcement = """

=== CRITICAL OUTPUT REQUIREMENTS ===

You are generating content for Telegram. The output MUST:

1. BE COMPLETE: Deliver full value without any external links
2. BE NATIVE: Written specifically for Telegram's format
3. NO "READ MORE": Never say "read the full article" or "link in bio"
4. STANDALONE: A user should get 100% of the value from this post alone

FORMAT YOUR RESPONSE AS JSON:
{
    "telegram_post": "Your complete, value-packed Telegram post here (200-400 words)"
}

The telegram_post MUST:
- Start with a compelling hook
- Include bullet points for key insights
- Provide actionable takeaways
- End with engagement CTA (question, poll prompt, etc.)
- Use appropriate emojis for visual scanning
- Include relevant hashtags at the end

DO NOT include any URLs, "source:", or external references in telegram_post.
The code will handle any necessary links programmatically.
"""
        return base_prompt + native_enforcement

    def _generate_fallback_post(self, title: str, summary: str) -> str:
        """Generate a fallback post if AI fails."""
        if self.brand.language == "ar":
            return f"""🚀 **{title}**

{summary[:300]}...

💡 **إيه رأيك؟**
شاركنا في التعليقات 👇

#تقنية #AI #أتمتة"""
        else:
            return f"""🚀 **{title}**

{summary[:300]}...

💡 **What do you think?**
Share your thoughts below 👇

#Tech #AI #Automation"""

    async def _publish_to_channel(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        content: str,
        image_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Publish native content to the brand's Telegram channel."""
        try:
            bot = context.bot
            channel_id = self.brand.channel_id

            if image_url:
                try:
                    await bot.send_photo(
                        chat_id=channel_id,
                        photo=image_url,
                        caption=content[:1024],  # Telegram caption limit
                        parse_mode="Markdown",
                    )
                except Exception:
                    # Fallback to text-only
                    await bot.send_message(
                        chat_id=channel_id,
                        text=content,
                        parse_mode="Markdown",
                    )
            else:
                await bot.send_message(
                    chat_id=channel_id,
                    text=content,
                    parse_mode="Markdown",
                )

            self.posts_today += 1
            self.last_post_time = datetime.now()

            return {"status": "success", "channel_id": channel_id}

        except Exception as e:
            self._log(f"Publish error: {e}")
            return {"status": "error", "error": str(e)}

    async def force_fetch(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Admin command: Force fetch and publish immediately."""
        if not _is_admin(update):
            if update.message:
                await update.message.reply_text("Not authorized")
            return

        if not update.message:
            return

        msg = await update.message.reply_text(
            f"🔄 [{self.brand.display_name}] Fetching content..."
        )

        try:
            # Generate native content
            result = await asyncio.wait_for(
                self._fetch_and_generate_native_content(context),
                timeout=120,
            )

            if result.get("status") != "success":
                await msg.edit_text(f"❌ {result.get('error', 'Unknown error')}")
                return

            content = result.get("content", "")
            feed_item = result.get("feed_item", {})
            image_url = feed_item.get("image")

            # Publish to channel
            pub_result = await self._publish_to_channel(context, content, image_url)

            if pub_result.get("status") == "success":
                await msg.edit_text(
                    f"✅ Published to {self.brand.display_name}!\n\n"
                    f"📝 {result.get('title', '')[:80]}..."
                )

                # If FUNNEL mode, also publish to external platforms
                if self.brand.mode == PublishingMode.FUNNEL:
                    await self._publish_to_external_platforms(context, result)
            else:
                await msg.edit_text(f"❌ Publish failed: {pub_result.get('error')}")

        except asyncio.TimeoutError:
            await msg.edit_text("⏱️ Timeout. Try again.")
            # Alert admin about timeout
            await send_alert_to_admin(
                self.brand.key,
                "Content generation timeout (120s exceeded)",
            )
        except Exception as e:
            await msg.edit_text(f"❌ Error: {e}")
            # Alert admin about error
            tb = traceback.format_exc()
            await send_alert_to_admin(self.brand.key, str(e), tb)

    async def _publish_to_external_platforms(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        result: Dict[str, Any],
    ) -> None:
        """
        For FUNNEL mode: Also publish to Blogger, Facebook, etc.
        This runs AFTER the native Telegram post.
        """
        from multi_platform_publisher import MultiPlatformPublisher
        from sequential_publisher import SequentialPublisher

        try:
            feed_item = result.get("feed_item", {})
            content_data = result.get("content_data", {})

            # Get platforms config
            platforms = self.brand.platforms
            external_platforms = [
                p
                for p in platforms.keys()
                if p != "telegram" and platforms[p].get("enabled")
            ]

            if not external_platforms:
                return

            self._log(f"Publishing to external: {external_platforms}")

            # Use existing sequential publisher for external platforms
            publisher = MultiPlatformPublisher()

            for platform in external_platforms:
                try:
                    if platform == "blogger":
                        title = content_data.get(
                            "blog_title", feed_item.get("title", "")
                        )
                        content = content_data.get("blog_content_md", "")
                        await publisher.publish_to_blogger(
                            title=title,
                            content=content,
                        )
                    elif platform == "facebook":
                        fb_content = content_data.get("facebook_post", "")
                        await publisher.publish_to_facebook(
                            message=fb_content,
                        )
                    elif platform == "discord":
                        discord_content = content_data.get("discord_msg", "")
                        await publisher.publish_to_discord(
                            message=discord_content,
                        )
                    elif platform == "devto":
                        title = content_data.get(
                            "blog_title", feed_item.get("title", "")
                        )
                        content = content_data.get("blog_content_md", "")
                        await publisher.publish_to_devto(
                            title=title,
                            content=content,
                        )
                except Exception as e:
                    self._log(f"External publish error ({platform}): {e}")

        except Exception as e:
            self._log(f"External platforms error: {e}")

    async def show_stats(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Show brand statistics."""
        if not _is_admin(update) or not update.message:
            return

        stats_text = f"""📊 **{self.brand.display_name} Stats**
═══════════════════════

📤 Posts today: {self.posts_today}
🕐 Last post: {self.last_post_time.strftime('%H:%M') if self.last_post_time else 'Never'}
🌐 Mode: {self.brand.mode.value.upper()}
📡 Channel: {self.brand.channel_id}

📚 Feeds: {len(self.brand.feeds)}
🎭 Persona: {self.brand.persona}
"""
        await update.message.reply_text(stats_text, parse_mode="Markdown")

    async def show_info(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Show brand info."""
        if not _is_admin(update) or not update.message:
            return

        platforms_str = ", ".join(
            [
                f"{p}({'ON' if cfg.get('enabled') else 'OFF'})"
                for p, cfg in self.brand.platforms.items()
            ]
        )

        info_text = f"""ℹ️ **{self.brand.display_name}**
═══════════════════════

🔑 Key: {self.brand.key}
🌐 Language: {self.brand.language}
📺 Channel: {self.brand.channel_id}
🎯 Mode: {self.brand.mode.value}

📱 Platforms: {platforms_str}

⏰ Schedule:
   • Timezone: {self.brand.schedule.get('timezone', 'UTC')}
   • Active: {self.brand.schedule.get('wake_hour', 9)}:00 - {self.brand.schedule.get('sleep_hour', 22)}:00
   • Max posts/day: {self.brand.schedule.get('posts_per_day', 8)}
"""
        await update.message.reply_text(info_text, parse_mode="Markdown")

    async def _cmd_start(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle /start command."""
        if not update.message:
            return

        if not _is_admin(update):
            await update.message.reply_text("🚫 Not authorized")
            return

        welcome = f"""🎯 **{self.brand.display_name}**
═══════════════════════

✅ Worker Bot Online!

📊 Mode: {self.brand.mode.value.upper()}
📺 Channel: {self.brand.channel_id}
📚 Feeds: {len(self.brand.feeds)}

Use the keyboard below to control this brand.
"""
        await update.message.reply_text(
            welcome,
            reply_markup=_get_worker_keyboard(),
            parse_mode="Markdown",
        )

    def build_application(self) -> Application:
        """Build the Telegram application for this worker."""
        app = ApplicationBuilder().token(self.brand.token).build()

        # Add handlers
        app.add_handler(CommandHandler("start", self._cmd_start))

        admin_filter = filters.User(user_id=ADMIN_USER_ID)

        app.add_handler(
            MessageHandler(
                admin_filter & filters.Regex(r"^⚡ Force Fetch$"),
                self.force_fetch,
            )
        )
        app.add_handler(
            MessageHandler(
                admin_filter & filters.Regex(r"^📊 Stats$"),
                self.show_stats,
            )
        )
        app.add_handler(
            MessageHandler(
                admin_filter & filters.Regex(r"^ℹ️ Info$"),
                self.show_info,
            )
        )

        self.app = app
        return app

    def start_polling(self) -> None:
        """Start polling in the current thread."""
        app = self.build_application()

        self._log(f"Starting polling for {self.brand.display_name}")
        self.is_running = True

        # Run polling without signal handlers (for threading)
        app.run_polling(
            drop_pending_updates=True,
            stop_signals=None,  # Critical for non-main thread
        )

    async def start(self) -> None:
        """Async start method for the worker bot."""
        app = self.build_application()

        self._log(f"Starting async polling for {self.brand.display_name}")
        self.is_running = True

        # Initialize and run
        await app.initialize()
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)

        # Keep running
        try:
            while self.is_running:
                await asyncio.sleep(1)
        finally:
            await app.stop()

    async def stop(self) -> None:
        """Stop the worker bot."""
        self.is_running = False
        if self.app:
            await self.app.stop()


def start_worker_in_thread(brand_key: str) -> Optional[threading.Thread]:
    """Start a brand worker in a background thread with error alerting."""
    brand = get_brand_by_key(brand_key)
    if not brand:
        print(f"Brand not found: {brand_key}")
        return None

    worker = BrandWorker(brand)

    def _runner():
        try:
            worker.start_polling()
        except Exception as e:
            error_msg = str(e)
            tb = traceback.format_exc()
            print(f"Worker {brand_key} crashed: {e}")
            traceback.print_exc()

            # ALERT ADMIN via Master Bot
            send_alert_sync(brand_key, error_msg, tb)

    thread = threading.Thread(target=_runner, daemon=True, name=f"worker-{brand_key}")
    thread.start()
    return thread


def start_all_workers() -> Dict[str, threading.Thread]:
    """Start all configured brand workers."""
    brands = get_brand_configs()
    threads = {}

    for key in brands:
        thread = start_worker_in_thread(key)
        if thread:
            threads[key] = thread

    return threads
