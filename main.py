import json
import os
from datetime import datetime
import time
from pathlib import Path
from typing import Any, Dict, Literal, Optional, TypedDict

import requests

from dotenv import load_dotenv
from telegram import (
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

load_dotenv()

# Import scheduling task
from scheduled_publisher_task import start_scheduler_task

# Start keep-alive HTTP server (for Render web service)
try:
    from keep_alive import keep_alive

    keep_alive()
except ImportError:
    print("⚠️ keep_alive not available (OK for local dev)")

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"
SEEN_POSTS_PATH = BASE_DIR / "data" / "seen_posts.json"
LOG_PATH = BASE_DIR / "bot.log"

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0") or "0")
CHANNEL_ID = os.getenv("CHANNEL_ID")
GROUP_ID = os.getenv("GROUP_ID")

# Broadcast conversation states
GET_MSG = 1
CONFIRM = 2

CHANNEL_URL = "https://t.me/nextlevelegypt"
GROUP_URL = "https://t.me/nextlevelegyptt"


SALES_COPY = (
    "👋 أهلاً بيك في RoboVAI Solutions\n\n"
    "إحنا بنبني حلول AI و Automation للشركات بشكل عملي وسريع.\n\n"
    "🤖 شات بوت خدمة عملاء 24/7\n"
    "⚙️ أتمتة شغل الشركة وتقليل التكاليف\n"
    "📊 حلول بيانات وذكاء أعمال\n\n"
    "لو مهتم—تابعنا وجرب بنفسك."
)


class PublishResult(TypedDict, total=False):
    status: Literal["published", "no_news", "error"]
    title: str
    error: str


def _log(message: str) -> None:
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat(timespec='seconds')} | {message}\n")
    except Exception:
        pass


def _load_config() -> dict:
    try:
        if not CONFIG_PATH.exists():
            return {}
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_config(data: dict) -> None:
    try:
        CONFIG_PATH.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        pass


def _get_system_prompt_from_config() -> Optional[str]:
    cfg = _load_config()
    prompt = cfg.get("system_prompt")
    if isinstance(prompt, str) and prompt.strip():
        return prompt.strip()
    return None


def _is_system_active() -> bool:
    cfg = _load_config()
    return cfg.get("status", "active") == "active"


def _toggle_status() -> str:
    cfg = _load_config()
    current = cfg.get("status", "active")
    new_status = "paused" if current == "active" else "active"
    cfg["status"] = new_status
    _save_config(cfg)
    return new_status


def get_admin_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            ["⚡ Force Fetch", "📊 Stats"],
            ["📢 Broadcast", "🛑 Status Toggle"],
            ["📝 Edit Prompt", "📡 Feeds"],
            ["📋 Logs", "ℹ️ System Info"],
            ["🌐 Platform Status", "🧪 Test Platforms"],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def get_sales_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("📢 تابعنا على القناة", url=CHANNEL_URL),
                InlineKeyboardButton("💬 جروب المناقشة", url=GROUP_URL),
            ]
        ]
    )


def _get_stats_text() -> str:
    cfg = _load_config()
    feeds = cfg.get("feeds")
    feeds_count = len(feeds) if isinstance(feeds, list) else 0

    seen_count = 0
    try:
        if SEEN_POSTS_PATH.exists():
            data = json.loads(SEEN_POSTS_PATH.read_text(encoding="utf-8"))
            if isinstance(data, list):
                seen_count = len(data)
            elif isinstance(data, dict):
                seen_count = len(data)
    except Exception:
        pass

    status = "active" if _is_system_active() else "paused"
    status_emoji = "🟢" if status == "active" else "🔴"

    return (
        "📊 Stats\n\n"
        f"{status_emoji} Status: {status}\n"
        f"🧩 Feeds: {feeds_count}\n"
        f"💾 Seen posts: {seen_count}"
    )


def prepare_media(post: Dict[str, Any], title: str) -> Dict[str, Optional[str]]:
    """
    CRITICAL MediaPipeline: Guarantee image availability with Storj upload.
    
    Returns:
        Dict with 'image_url' (public Storj URL) and 'image_local_path' (for Telegram)
    """
    print("🖼️ MediaPipeline: Starting...")
    
    def _download_image(url: str) -> Optional[str]:
        try:
            images_dir = BASE_DIR / "images" / "downloaded"
            images_dir.mkdir(parents=True, exist_ok=True)

            resp = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()

            content_type = (resp.headers.get("content-type") or "").lower()
            ext = "jpg"
            if "png" in content_type:
                ext = "png"
            elif "jpeg" in content_type or "jpg" in content_type:
                ext = "jpg"
            elif url.lower().endswith(".png"):
                ext = "png"
            elif url.lower().endswith(".jpg") or url.lower().endswith(".jpeg"):
                ext = "jpg"

            stamp = int(time.time() * 1000)
            filename = f"rss_{stamp}.{ext}"
            out = images_dir / filename
            out.write_bytes(resp.content)
            return str(out)
        except Exception as exc:
            print(f"⚠️ MediaPipeline: RSS image download failed: {exc}")
            return None

    def _upload_to_storj(local_path: str) -> Optional[str]:
        try:
            from r2_uploader import upload_image_if_configured

            name = Path(local_path).name
            return upload_image_if_configured(local_path, name)
        except Exception as exc:
            print(f"⚠️ MediaPipeline: Storj upload failed: {exc}")
            return None

    # Strategy 1: Use RSS image if available (download locally then upload to Storj)
    rss_image = post.get("image")
    if rss_image and isinstance(rss_image, str) and rss_image.startswith("http"):
        print(f"✅ Strategy 1: Found RSS image: {rss_image[:60]}...")
        local = _download_image(rss_image)
        if local:
            public = _upload_to_storj(local)
            if public:
                return {"image_url": public, "image_local_path": local}
            # If upload fails, still return local for Telegram and RSS URL for others
            return {"image_url": rss_image, "image_local_path": local}
        return {"image_url": rss_image, "image_local_path": None}
    
    # Strategy 2: Generate OG Image and upload to Storj
    print("🎨 Strategy 2: Generating OG Image...")
    try:
        from image_generator import get_article_image
        
        result = get_article_image(title, post.get("link"))
        if result:
            local_path = result.get("local_path")
            public_url = result.get("public_url")
            if not public_url and local_path:
                public_url = _upload_to_storj(str(local_path))
            if public_url:
                print(f"✅ OG Image ready: {public_url[:60]}...")
                return {"image_url": public_url, "image_local_path": local_path}
        print("⚠️ OG Image generation returned no usable URL")
    except Exception as e:
        print(f"❌ OG Image generation failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Fallback: generate a simple placeholder image locally then upload
    try:
        from PIL import Image, ImageDraw, ImageFont

        images_dir = BASE_DIR / "images" / "generated"
        images_dir.mkdir(parents=True, exist_ok=True)
        stamp = int(time.time() * 1000)
        fallback_path = images_dir / f"og_fallback_{stamp}.png"

        img = Image.new("RGB", (1200, 630), color=(15, 23, 42))
        draw = ImageDraw.Draw(img)
        text = (title or "RoboVAI").strip()[:120]

        try:
            font = ImageFont.truetype("C:\\Windows\\Fonts\\tahoma.ttf", 48)
        except Exception:
            font = ImageFont.load_default()

        draw.text((60, 260), text, fill=(96, 165, 250), font=font)
        img.save(fallback_path)

        public = _upload_to_storj(str(fallback_path))
        if public:
            return {"image_url": public, "image_local_path": str(fallback_path)}
        return {"image_url": None, "image_local_path": str(fallback_path)}
    except Exception as exc:
        print(f"⚠️ MediaPipeline: fallback image failed: {exc}")
        return {"image_url": None, "image_local_path": None}


async def fetch_and_publish(
    context: ContextTypes.DEFAULT_TYPE, *, override_status: bool = False
) -> PublishResult:
    """Existing pipeline wrapper: fetch from RSS then publish to channel.

    Args:
        override_status: If True, bypass the paused status check (for admin Force Fetch).
    """
    try:
        from feed_manager import fetch_random_new_post
        from ai_processor import rewrite_with_ai, get_last_ai_error
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "error": f"Import error: {exc}"}

    if not CHANNEL_ID:
        return {"status": "error", "error": "CHANNEL_ID is not set"}

    if not override_status and not _is_system_active():
        return {"status": "error", "error": "System is paused"}

    post = fetch_random_new_post()
    if not post:
        return {"status": "no_news"}

    system_prompt = _get_system_prompt_from_config()
    ai = rewrite_with_ai(
        post.get("title", ""),
        post.get("summary", ""),
        post.get("link", ""),
        system_prompt=system_prompt,
    )
    if not ai:
        return {"status": "error", "error": get_last_ai_error() or "AI failed"}

    telegram_post = str(ai.get("telegram_post", "") or "").strip()
    facebook_post = str(ai.get("facebook_post", "") or "").strip()
    blog_title = str(ai.get("blog_title", "") or "").strip()
    blog_content_md = str(ai.get("blog_content_md", "") or "").strip()
    discord_msg = str(ai.get("discord_msg", "") or "").strip()

    # Default caption fallback for platforms not explicitly tailored.
    caption = facebook_post or telegram_post
    link = str(post.get("link", "") or "").strip()
    title = str(post.get("title", "") or "").strip()
    
    # 🚀 NEW: Use MediaPipeline to guarantee image availability
    media_result = prepare_media(post, title)
    image_url = media_result.get("image_url")
    image_local_path = media_result.get("image_local_path")

    def _compose_text(c: str, l: str, has_photo: bool) -> str:
        base = (
            c
            if (l and l in c)
            else (c + ("\n\n🔗 لينك الخبر/الأداة: " + l if l else ""))
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

    # Multi-platform publish with scheduling support
    try:
        from multi_platform_publisher import MultiPlatformPublisher

        payloads = {
            "telegram": {"caption": telegram_post or caption},
            "facebook": {"caption": facebook_post or caption},
            "discord": {"caption": discord_msg or caption},
            "blogger": {
                "caption": blog_content_md or caption,
                "title": blog_title or None,
            },
            "devto": {
                "caption": blog_content_md or caption,
                "title": blog_title or None,
            },
        }

        # Publish immediately to all platforms (no fake scheduling)
        publisher = MultiPlatformPublisher(use_scheduler=False)
        results = await publisher.publish(
            caption=caption,
            link=link or None,
            image_url=image_url or None,
            image_local_path=image_local_path or None,
            platform_payloads=payloads,
            telegram_context=context,
            send_reports=True,  # Enable real-time reports to admin
        )

        any_success = any(
            isinstance(v, dict) and (v.get("status") == "success" or v.get("success"))
            for v in results.values()
        )
        if not any_success:
            return {"status": "error", "error": f"Publish failed: {results}"}

        _log(f"Published: {link} | results={results}")
        return {"status": "published", "title": title}
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "error": f"Publish error: {exc}"}


async def admin_test_discord(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not update.message or not update.effective_user:
        return
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ غير مصرح")
        return

    if not os.getenv("DISCORD_WEBHOOK_URL"):
        await update.message.reply_text("❌ DISCORD_WEBHOOK_URL مش موجود في .env")
        return

    try:
        from discord_publisher import DiscordPublisher

        publisher = DiscordPublisher()
        publisher.publish(
            caption=f"Test from RoboBot ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})",
            link=None,
            image_url=None,
        )
        await update.message.reply_text("✅ تم إرسال رسالة اختبار على Discord")
    except Exception as exc:  # noqa: BLE001
        await update.message.reply_text(f"❌ فشل اختبار Discord: {exc}")


async def admin_platform_status(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Show status of all configured platforms"""
    if not update.message or not update.effective_user:
        return
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ غير مصرح")
        return

    try:
        from multi_platform_publisher import MultiPlatformPublisher

        publisher = MultiPlatformPublisher()
        status = publisher.get_platform_status()

        # Build status message
        message = "🌐 **Platform Status**\n\n"

        platforms = {
            "telegram": "📱 Telegram",
            "discord": "💬 Discord",
            "blogger": "📝 Blogger",
            "facebook": "👥 Facebook",
            "linkedin": "💼 LinkedIn",
            "twitter": "🐦 Twitter/X",
            "reddit": "🔴 Reddit",
            "medium": "📖 Medium",
        }

        for key, name in platforms.items():
            if key in status:
                emoji = "✅" if status[key] else "❌"
                message += f"{emoji} {name}\n"

        enabled_count = sum(1 for v in status.values() if v)
        message += f"\n**Active:** {enabled_count}/{len(status)} platforms"

        await update.message.reply_text(message, parse_mode="Markdown")
    except Exception as exc:  # noqa: BLE001
        await update.message.reply_text(f"❌ Error: {exc}")


async def admin_test_platforms(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Send test messages to all configured platforms"""
    if not update.message or not update.effective_user:
        return
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ غير مصرح")
        return

    test_caption = (
        f"🧪 Test from RoboBot\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    test_link = "https://github.com/m0shaban/Tech-Influencer-bot"

    await update.message.reply_text("⏳ Testing all platforms...")

    try:
        from multi_platform_publisher import MultiPlatformPublisher

        publisher = MultiPlatformPublisher()
        results = await publisher.publish(
            caption=test_caption,
            link=test_link,
            image_url=None,
            telegram_context=context,
        )

        # Build results message
        message = "🧪 **Test Results**\n\n"
        for platform, result in results.items():
            status_emoji = (
                "✅"
                if result.get("status") == "success" or result.get("success")
                else "❌"
            )
            platform_name = platform.capitalize()
            message += f"{status_emoji} {platform_name}\n"

        await update.message.reply_text(message, parse_mode="Markdown")
    except Exception as exc:  # noqa: BLE001
        await update.message.reply_text(f"❌ Test failed: {exc}")


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return

    if update.effective_user.id == ADMIN_USER_ID:
        await update.message.reply_text(
            "أهلاً يا هندسة! 🚀 غرفة التحكم جاهزة.",
            reply_markup=get_admin_keyboard(),
        )
        return

    await update.message.reply_text(
        SALES_COPY,
        reply_markup=get_sales_keyboard(),
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    await update.message.reply_text(
        "الأوامر:\n"
        "/start - Start\n"
        "/help - How to use\n"
        "/contact - Contact Support"
    )


async def cmd_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    await update.message.reply_text("للتواصل والدعم: @mohamedshabanai")


async def admin_force_fetch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return

    msg = await update.message.reply_text("🕵️‍♂️ جاري الفحص: بتصل بالمصادر...")

    # Cooldown to avoid spamming Groq/Telegram
    if not hasattr(admin_force_fetch, "_last_time"):
        admin_force_fetch._last_time = 0.0  # type: ignore[attr-defined]
    now = time.time()
    if now - admin_force_fetch._last_time < 20:
        await msg.edit_text("⏳ استنى 20 ثانية قبل الطلب التالي")
        return
    admin_force_fetch._last_time = now  # type: ignore[attr-defined]

    try:
        result = await fetch_and_publish(context, override_status=True)
        status = result.get("status")
        if status == "published":
            title = result.get("title", "")
            await msg.edit_text(f"✅ تم النشر! {title}")
            return
        if status == "no_news":
            await msg.edit_text("⚠️ مفيش أخبار جديدة. (Evergreen logic skipped for now)")
            return
        await msg.edit_text(f"❌ خطأ: {result.get('error', 'Unknown error')}")
    except Exception as exc:  # noqa: BLE001
        await msg.edit_text(f"❌ خطأ: {exc}")


async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    await update.message.reply_text(_get_stats_text())


async def admin_status_toggle(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not update.message:
        return
    new_status = _toggle_status()
    emoji = "🟢" if new_status == "active" else "🔴"
    await update.message.reply_text(f"{emoji} Status: {new_status}")


async def admin_view_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    cfg = _load_config()
    prompt = cfg.get("system_prompt", "(No custom prompt set - using default)")
    preview = prompt[:500] + "..." if len(prompt) > 500 else prompt
    await update.message.reply_text(
        f"📝 **Current System Prompt:**\n\n{preview}\n\n"
        "Send /setprompt <your_new_prompt> to update.",
        parse_mode="Markdown",
    )


async def admin_set_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not context.args:
        (
            await update.message.reply_text(
                "Usage: /setprompt <your new prompt text>\n\n"
                "Or reply to this with multi-line text."
            )
            if update.message
            else None
        )
        return
    new_prompt = " ".join(context.args)
    cfg = _load_config()
    cfg["system_prompt"] = new_prompt
    _save_config(cfg)
    await update.message.reply_text(f"✅ Prompt updated! ({len(new_prompt)} chars)")


async def admin_list_feeds(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    cfg = _load_config()
    feeds = cfg.get("feeds", [])
    if not feeds:
        await update.message.reply_text(
            "📡 No custom feeds. Using defaults from feeds_config.py"
        )
        return
    text = f"📡 **Active Feeds** ({len(feeds)}):\n\n"
    for i, feed in enumerate(feeds[:20], 1):  # Show first 20
        text += f"{i}. {feed[:50]}...\n"
    if len(feeds) > 20:
        text += f"\n...and {len(feeds) - 20} more."
    await update.message.reply_text(text, parse_mode="Markdown")


async def admin_add_feed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not context.args:
        (
            await update.message.reply_text(
                "Usage: /addfeed <RSS_URL>\n\nExample:\n/addfeed https://example.com/feed.xml"
            )
            if update.message
            else None
        )
        return
    new_feed = context.args[0].strip()
    if not new_feed.startswith(("http://", "https://")):
        await update.message.reply_text(
            "❌ Invalid URL. Must start with http:// or https://"
        )
        return
    cfg = _load_config()
    feeds = cfg.get("feeds", [])
    if new_feed in feeds:
        await update.message.reply_text("⚠️ Feed already exists.")
        return
    feeds.append(new_feed)
    cfg["feeds"] = feeds
    _save_config(cfg)
    await update.message.reply_text(f"✅ Feed added! Total: {len(feeds)}")


async def admin_remove_feed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not context.args:
        (
            await update.message.reply_text(
                "Usage: /removefeed <URL_or_index>\n\n"
                "Example:\n/removefeed 5\nor\n/removefeed https://example.com/feed.xml"
            )
            if update.message
            else None
        )
        return
    cfg = _load_config()
    feeds = cfg.get("feeds", [])
    if not feeds:
        await update.message.reply_text("❌ No custom feeds to remove.")
        return

    target = " ".join(context.args)
    # Try as index first
    if target.isdigit():
        idx = int(target) - 1
        if 0 <= idx < len(feeds):
            removed = feeds.pop(idx)
            cfg["feeds"] = feeds
            _save_config(cfg)
            await update.message.reply_text(f"✅ Removed: {removed[:50]}...")
            return
    # Try as URL
    if target in feeds:
        feeds.remove(target)
        cfg["feeds"] = feeds
        _save_config(cfg)
        await update.message.reply_text(f"✅ Removed: {target[:50]}...")
        return

    await update.message.reply_text(
        "❌ Feed not found. Use /feeds to see current list."
    )


async def admin_view_logs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    if not LOG_PATH.exists():
        await update.message.reply_text("📋 No logs yet.")
        return

    try:
        with LOG_PATH.open("r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        last_lines = lines[-30:]  # Last 30 lines
        log_text = "".join(last_lines)
        if len(log_text) > 4000:
            log_text = "..." + log_text[-4000:]
        await update.message.reply_text(
            f"📋 **Recent Logs:**\n\n```\n{log_text}\n```", parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error reading logs: {e}")


async def admin_system_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return

    cfg = _load_config()
    status = cfg.get("status", "unknown")
    model = cfg.get("model", "llama-3.3-70b-versatile")
    feeds_count = len(cfg.get("feeds", []))

    seen_count = 0
    if SEEN_POSTS_PATH.exists():
        try:
            import json

            data = json.loads(SEEN_POSTS_PATH.read_text(encoding="utf-8"))
            seen_count = len(data) if isinstance(data, list) else 0
        except:
            pass

    info = (
        f"ℹ️ **System Info**\n\n"
        f"Status: {status} {'🟢' if status == 'active' else '🔴'}\n"
        f"Model: {model}\n"
        f"Custom Feeds: {feeds_count}\n"
        f"Posts Published: {seen_count}\n"
        f"Channel: {CHANNEL_ID}\n"
        f"Group: {GROUP_ID or 'N/A'}\n\n"
        f"Use the buttons below to manage the bot."
    )

    await update.message.reply_text(info, parse_mode="Markdown")


def _broadcast_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📢 للقناة فقط", callback_data="bcast:channel")],
            [InlineKeyboardButton("👥 للجروب فقط", callback_data="bcast:group")],
            [InlineKeyboardButton("🚀 للاثنين", callback_data="bcast:both")],
            [InlineKeyboardButton("❌ إلغاء", callback_data="bcast:cancel")],
        ]
    )


async def broadcast_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message:
        return ConversationHandler.END

    await update.message.reply_text("📝 اكتب الرسالة (أو ابعت صورة) اللي عايز تنشرها:")
    return GET_MSG


async def broadcast_get_msg(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or context.user_data is None:
        return GET_MSG

    # Persist message payload in user_data
    payload: dict[str, Any] = {}
    if update.message.text:
        payload["kind"] = "text"
        payload["text"] = update.message.text
    elif update.message.photo:
        payload["kind"] = "photo"
        payload["file_id"] = update.message.photo[-1].file_id
        payload["caption"] = update.message.caption or ""
    else:
        await update.message.reply_text("❌ ابعت نص أو صورة بس.")
        return GET_MSG

    context.user_data["broadcast_payload"] = payload

    # Preview
    if payload["kind"] == "text":
        preview_text = f"📋 معاينة الرسالة:\n\n{payload['text']}"
        await update.message.reply_text(
            preview_text, reply_markup=_broadcast_keyboard()
        )
    else:
        caption = payload.get("caption", "")
        preview_text = "📋 معاينة الصورة:\n\n" + (
            caption if caption else "(بدون كابشن)"
        )
        if not update.effective_chat:
            await update.message.reply_text("❌ خطأ: chat غير متاح")
            return ConversationHandler.END
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=payload["file_id"],
            caption=preview_text,
            reply_markup=_broadcast_keyboard(),
        )

    return CONFIRM


async def broadcast_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if not query or not query.data:
        return CONFIRM
    await query.answer()

    if context.user_data is None:
        await query.edit_message_text("❌ خطأ داخلي")
        return ConversationHandler.END

    if update.effective_user and update.effective_user.id != ADMIN_USER_ID:
        await query.edit_message_text("❌ غير مصرح")
        return ConversationHandler.END

    payload = context.user_data.get("broadcast_payload")
    if not isinstance(payload, dict) or "kind" not in payload:
        await query.edit_message_text("❌ مفيش رسالة محفوظة")
        return ConversationHandler.END

    action = query.data
    if action == "bcast:cancel":
        await query.edit_message_text("تم الإلغاء")
        return ConversationHandler.END

    if not CHANNEL_ID and action in {"bcast:channel", "bcast:both"}:
        await query.edit_message_text("❌ CHANNEL_ID مش مضبوط")
        return ConversationHandler.END
    if not GROUP_ID and action in {"bcast:group", "bcast:both"}:
        await query.edit_message_text("❌ GROUP_ID مش مضبوط")
        return ConversationHandler.END

    try:
        targets: list[str] = []
        if action in {"bcast:channel", "bcast:both"} and CHANNEL_ID:
            targets.append(CHANNEL_ID)
        if action in {"bcast:group", "bcast:both"} and GROUP_ID:
            targets.append(GROUP_ID)

        for chat_id in targets:
            if payload["kind"] == "text":
                await context.bot.send_message(
                    chat_id=chat_id, text=str(payload.get("text", ""))
                )
            else:
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=str(payload.get("file_id")),
                    caption=str(payload.get("caption", "")) or None,
                )

        _log(f"Broadcast sent: {action}")
        await query.edit_message_text("✅ تم الإرسال")
        return ConversationHandler.END
    except Exception as exc:  # noqa: BLE001
        await query.edit_message_text(f"❌ خطأ: {exc}")
        return ConversationHandler.END


async def post_init(app: Application) -> None:
    # Ensure polling mode (not webhook) and clean pending updates
    try:
        await app.bot.delete_webhook(drop_pending_updates=True)
    except Exception:
        pass
    await app.bot.set_my_commands(
        [
            BotCommand("start", "Start the bot"),
            BotCommand("help", "How to use"),
            BotCommand("contact", "Contact Support"),
            BotCommand("test_discord", "Admin: test Discord"),
        ]
    )

    # Start Auto Publisher (smart pacing with business hours)
    print("🚀 Starting Auto Publisher...")
    try:
        from auto_publisher import get_auto_publisher
        import asyncio

        auto_pub = get_auto_publisher()

        # Create a wrapper that captures the context
        async def publish_wrapper(ctx, override_status=False):
            return await fetch_and_publish(ctx, override_status=override_status)

        # Create a fake context object that can access the bot
        class BotContext:
            def __init__(self, bot):
                self.bot = bot

        ctx = BotContext(app.bot)

        # Start auto publishing in background
        asyncio.create_task(auto_pub.run(publish_wrapper, ctx))
        print("✅ Auto Publisher started successfully")
    except Exception as e:
        print(f"⚠️ Failed to start Auto Publisher: {e}")


def main() -> None:
    if not TELEGRAM_TOKEN:
        raise RuntimeError("Missing TELEGRAM_TOKEN")
    if not ADMIN_USER_ID:
        raise RuntimeError("Missing/invalid ADMIN_USER_ID")

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).post_init(post_init).build()

    # Global commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("contact", cmd_contact))

    # Admin commands
    app.add_handler(CommandHandler("setprompt", admin_set_prompt))
    app.add_handler(CommandHandler("addfeed", admin_add_feed))
    app.add_handler(CommandHandler("removefeed", admin_remove_feed))
    app.add_handler(CommandHandler("feeds", admin_list_feeds))
    app.add_handler(CommandHandler("logs", admin_view_logs))
    app.add_handler(CommandHandler("info", admin_system_info))
    app.add_handler(CommandHandler("test_discord", admin_test_discord))

    admin_filter = filters.User(user_id=ADMIN_USER_ID)

    # Admin buttons (outside conversations)
    app.add_handler(
        MessageHandler(
            admin_filter & filters.Regex(r"^⚡ Force Fetch$"), admin_force_fetch
        )
    )
    app.add_handler(
        MessageHandler(admin_filter & filters.Regex(r"^📊 Stats$"), admin_stats)
    )
    app.add_handler(
        MessageHandler(
            admin_filter & filters.Regex(r"^🛑 Status Toggle$"), admin_status_toggle
        )
    )
    app.add_handler(
        MessageHandler(
            admin_filter & filters.Regex(r"^📝 Edit Prompt$"), admin_view_prompt
        )
    )
    app.add_handler(
        MessageHandler(admin_filter & filters.Regex(r"^📡 Feeds$"), admin_list_feeds)
    )
    app.add_handler(
        MessageHandler(admin_filter & filters.Regex(r"^📋 Logs$"), admin_view_logs)
    )
    app.add_handler(
        MessageHandler(
            admin_filter & filters.Regex(r"^ℹ️ System Info$"), admin_system_info
        )
    )
    app.add_handler(
        MessageHandler(
            admin_filter & filters.Regex(r"^🌐 Platform Status$"), admin_platform_status
        )
    )
    app.add_handler(
        MessageHandler(
            admin_filter & filters.Regex(r"^🧪 Test Platforms$"), admin_test_platforms
        )
    )

    # Broadcast wizard
    broadcast_conv = ConversationHandler(
        entry_points=[
            MessageHandler(
                admin_filter & filters.Regex(r"^📢 Broadcast$"), broadcast_entry
            )
        ],
        states={
            GET_MSG: [
                MessageHandler(
                    admin_filter & (filters.TEXT | filters.PHOTO), broadcast_get_msg
                )
            ],
            CONFIRM: [CallbackQueryHandler(broadcast_confirm, pattern=r"^bcast:")],
        },
        fallbacks=[],
        per_message=False,
    )
    app.add_handler(broadcast_conv)

    print("🚀 RoboVAI Bot running. Press Ctrl+C to stop.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
