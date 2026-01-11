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
import re
import threading
import traceback
import pytz
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Callable

from telegram import (
    Bot,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    Update,
)
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

from image_manager import get_best_image
from ai_processor import rewrite_with_ai


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


async def send_success_report_to_admin(
    *,
    brand_name: str,
    topic_title: str,
    had_image: bool,
    timestamp: str,
) -> None:
    """Send a clean HTML success report to the admin via Master bot."""
    if not MASTER_BOT_TOKEN or not ADMIN_USER_ID:
        return

    try:
        master_bot = Bot(token=MASTER_BOT_TOKEN)
        img_txt = "Attached" if had_image else "Missing"
        text = (
            f"<b>✅ MISSION SUCCESS | {brand_name}</b>\n"
            "——————————————————\n"
            f"<b>🗞 Topic:</b> {topic_title}\n"
            f"<b>🖼 Image:</b> {img_txt}\n"
            f"<b>🕒 Time:</b> {timestamp}\n"
            "——————————————————\n"
            "<i>🚀 Post is live on channel.</i>"
        )
        await master_bot.send_message(
            chat_id=ADMIN_USER_ID, text=text, parse_mode="HTML"
        )
    except Exception:
        return


_TEASER_PHRASES = [
    # English
    "read more",
    "click the link",
    "click link",
    "full article",
    "link in bio",
    "read the full",
    "see full",
    # Arabic
    "اقرأ المزيد",
    "اضغط",
    "الرابط",
    "التفاصيل في",
    "شوف المقال",
    "اقرأ المقال",
]


def _looks_like_teaser(text: str) -> bool:
    t = (text or "").strip().lower()
    if not t:
        return True
    if len(t) < 280:
        return True
    return any(p in t for p in _TEASER_PHRASES)


def _split_text_chunks(text: str, limit: int) -> list[str]:
    """Split by paragraphs first, then hard-split as last resort."""
    t = (text or "").strip()
    if not t:
        return []

    parts = [p.strip() for p in t.split("\n\n") if p.strip()]
    chunks: list[str] = []
    buf = ""

    def flush() -> None:
        nonlocal buf
        if buf.strip():
            chunks.append(buf.strip())
        buf = ""

    for p in parts:
        candidate = (buf + "\n\n" + p).strip() if buf else p
        if len(candidate) <= limit:
            buf = candidate
            continue

        if buf:
            flush()

        # If single paragraph is too long, hard split it
        while len(p) > limit:
            chunks.append(p[:limit].strip())
            p = p[limit:]
        buf = p.strip()

    flush()
    return chunks


def _build_source_button(*, url: str, lang: str, label_override: str = "") -> Optional[InlineKeyboardMarkup]:
    """
    Builds the CTA button.
    If 'label_override' is set, use it. Otherwise default to 'Reference'.
    Uses 'url' which should now be the USER'S CTA URL (Blog/Channel), not the RSS source.
    """
    u = (url or "").strip()
    if not u:
        return None
        
    is_ar = (lang or "").lower().startswith("ar")
    
    if label_override:
        label = label_override
    else:
        # Dynamic label based on URL type
        if "t.me/" in u:
            label = "📢 اشترك في القناة" if is_ar else "📢 Join Channel"
        elif "blogspot" in u or "dev.to" in u:
            label = "📝 اقرأ المزيد على المدونة" if is_ar else "📝 Read on Blog"
        else:
            label = "🔗 المصدر" if is_ar else "🔗 Reference"

    return InlineKeyboardMarkup([[InlineKeyboardButton(label, url=u)]])


def _strip_urls(text: str) -> str:
    t = text or ""
    # Remove raw URLs if the model leaks them; reference is via button.
    t = re.sub(r"https?://\S+", "", t, flags=re.IGNORECASE)
    t = re.sub(r"www\.[^\s]+", "", t, flags=re.IGNORECASE)
    # Normalize excess blank lines
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


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
        self, context: Optional[ContextTypes.DEFAULT_TYPE] = None
    ) -> Dict[str, Any]:
        """
        Fetch news and generate NATIVE Telegram content.

        Args:
            context: Optional telegram context (unused in logic, kept for compat)
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
        telegram_post = str(content_data.get("telegram_post", "") or "").strip()
        if not telegram_post or _looks_like_teaser(telegram_post):
            # One retry with even stricter instruction (models sometimes ignore first pass)
            retry_prompt = (
                self._get_native_prompt()
                + "\n\nCRITICAL: Your previous output looked like a teaser/gateway. "
                + "Rewrite as a standalone Telegram post that teaches EVERYTHING inside Telegram. "
                + "Do not mention clicking links."
            )
            retry = rewrite_with_ai(
                title=title,
                summary=summary,
                link=link,
                system_prompt=retry_prompt,
                platform="telegram",
                brand_name=self.brand.key,
                brand_language=self.brand.language,
            )
            telegram_post2 = str((retry or {}).get("telegram_post", "") or "").strip()
            if telegram_post2 and not _looks_like_teaser(telegram_post2):
                telegram_post = telegram_post2

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
        context: Optional[ContextTypes.DEFAULT_TYPE],
        content: str,
        *,
        title: str = "",
        source_url: str = "",
        _bot_instance: Optional[Bot] = None,
    ) -> Dict[str, Any]:
        """Publish native content to the brand's Telegram channel.

        Requirements:
        - EVERY post must include an image (ImgBB URL preferred).
        - Publish via send_photo() with caption.
        """
        try:
            bot = _bot_instance or (context.bot if context else None)
            if not bot:
                # Fallback if no context provided (async loop case)
                if self.app:
                    bot = self.app.bot
                else:
                    return {"status": "error", "error": "No bot instance available"}

            channel_id = self.brand.channel_id

            # Always resolve an image (best effort) and prefer ImgBB URL
            img = get_best_image(
                title or "RoboVAI", source_url or "", brand_key=self.brand.key
            )
            image_url = str((img or {}).get("url") or "").strip()
            if not image_url:
                return {"status": "error", "error": "ImageManager returned no image"}

            # Split content: caption <= 1024, remainder as messages
            safe_content = _strip_urls(content)
            caption_chunks = _split_text_chunks(safe_content, 1024)
            caption = caption_chunks[0] if caption_chunks else ""
            remainder = caption_chunks[1:] if len(caption_chunks) > 1 else []

            reply_markup = _build_source_button(
                url=source_url, lang=self.brand.language
            )

            # Send photo with caption (no parse_mode to avoid formatting failures)
            await bot.send_photo(
                chat_id=channel_id,
                photo=image_url,
                caption=caption,
                reply_markup=reply_markup,
            )

            # Send remainder inside Telegram (still standalone; no leaving TG)
            if remainder:
                # Telegram message limit is 4096; keep some headroom
                for chunk in remainder:
                    for msg_chunk in _split_text_chunks(chunk, 3800):
                        await bot.send_message(chat_id=channel_id, text=msg_chunk)

            # Admin UX report
            await send_success_report_to_admin(
                brand_name=self.brand.display_name,
                topic_title=(title or "").strip() or "(no title)",
                had_image=True,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )

            self.posts_today += 1
            self.last_post_time = datetime.now()

            return {"status": "success", "channel_id": channel_id, "image": image_url}

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
            title = str(result.get("title", "") or "").strip()
            link = str(result.get("link", "") or "").strip()

            # Publish to channel
            pub_result = await self._publish_to_channel(
                context,
                content,
                title=title,
                source_url=link,
            )

            if pub_result.get("status") == "success":
                await msg.edit_text(
                    f"✅ Published to {self.brand.display_name}!\n\n"
                    f"📝 {result.get('title', '')[:80]}..."
                )

                # If FUNNEL or DUAL mode, also publish to external platforms
                if self.brand.mode in [PublishingMode.FUNNEL, PublishingMode.DUAL]:
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
        context: Optional[ContextTypes.DEFAULT_TYPE],
        result: Dict[str, Any],
    ) -> None:
        """
        Publish to ALL platforms sequentially with CTAs.
        Uses SequentialPublisher to ensure proper CTA injection between platforms.
        
        Strategy:
        - BlockSignals: Telegram first (HUB) → Discord with CTA to Telegram
        - ZeroDev: Dev.to first (HUB) → Telegram with CTA to Dev.to
        - RoboVAI_AR: Blogger first (HUB) → Facebook with CTA → Telegram with CTA
        """
        from sequential_publisher import SequentialPublisher
        from multi_platform_publisher import MultiPlatformPublisher

        try:
            feed_item = result.get("feed_item", {})
            if not feed_item:
                feed_item = {
                    "title": result.get("title", ""),
                    "summary": result.get("summary", ""),
                    "link": result.get("link", ""),
                }

            # Load full config for SequentialPublisher
            config_path = Path(__file__).parent / "config.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))

            # Initialize publishers
            seq_publisher = SequentialPublisher(config)
            multi_publisher = MultiPlatformPublisher()

            self._log(f"📤 Starting sequential publish for {self.brand.display_name}")
            
            # Use sequential publisher for proper CTA flow
            published = await seq_publisher.publish_item(
                brand_name=self.brand.key,
                feed_item=feed_item,
                platform_publisher=multi_publisher,
                telegram_context=context,
                fast_mode=False,  # Use delays for proper CTA injection
            )

            if published:
                platforms_str = ", ".join(published.keys())
                self._log(f"✅ Published to: {platforms_str}")
            else:
                self._log("⚠️ No platforms published successfully")

        except Exception as e:
            self._log(f"External platforms error: {e}")
            tb = traceback.format_exc()
            await send_alert_to_admin(self.brand.key, f"External publish failed: {e}", tb)

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
        if app.updater is None:
            raise RuntimeError(
                "Application.updater is None; cannot start polling. "
                "Ensure python-telegram-bot polling is enabled."
            )
        await app.updater.start_polling(drop_pending_updates=True)

        # Keep running
        try:
            while self.is_running:
                # --- SCHEDULER LOGIC ---
                try:
                    await self._check_schedule_and_post()
                except Exception as e:
                    self._log(f"Scheduler error: {e}")

                await asyncio.sleep(60)
        finally:
            await app.stop()

    async def _check_schedule_and_post(self) -> None:
        """Check if it's time to post and execute if so."""
        tz_name = self.brand.schedule.get("timezone", "UTC")
        try:
            local_tz = pytz.timezone(tz_name)
        except:
            local_tz = pytz.UTC

        now_aware = datetime.now(local_tz)
        current_hour = now_aware.hour

        wake = self.brand.schedule.get("wake_hour", 9)
        sleep = self.brand.schedule.get("sleep_hour", 22)
        limit = self.brand.schedule.get("posts_per_day", 8)

        # Check Business Hours
        if not (wake <= current_hour < sleep):
            return

        # Check Daily Limit
        if self.posts_today >= limit:
            return

        # Check Interval (Spread posts evenly)
        # e.g. 14 hours / 8 posts = ~1.75 hours = 105 minutes
        active_hours = max(1, sleep - wake)
        interval_minutes = (active_hours * 60) / max(1, limit)

        should_post = False
        if not self.last_post_time:
            # First run: start straight away (or maybe slight delay?)
            should_post = True
        else:
            # Compare with system time (self.last_post_time is system time)
            delta = datetime.now() - self.last_post_time
            if delta.total_seconds() > (interval_minutes * 60):
                should_post = True

        if should_post:
            self._log(
                f"⏰ Scheduled post triggering (Interval: {interval_minutes:.0f}m)"
            )

            # Fetch & Generate content
            res = await self._fetch_and_generate_native_content(None)

            if res.get("status") == "success":
                # Use SequentialPublisher for ALL platforms (including Telegram)
                # This ensures proper CTA flow:
                # - BlockSignals: Telegram → Discord (with CTA to Telegram)
                # - ZeroDev: Dev.to → Telegram (with CTA to Dev.to)  
                # - RoboVAI: Blogger → Facebook → Telegram (with CTAs)
                await self._publish_to_external_platforms(
                    context=None,
                    result=res,
                )
            elif res.get("status") == "no_news":
                self._log("No news found for scheduled post.")
            else:
                self._log(f"Scheduled generation failed: {res.get('error')}")

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
