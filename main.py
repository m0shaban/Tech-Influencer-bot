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
from telegram.error import Conflict
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
BRAND_STATS_PATH = BASE_DIR / "data" / "brand_stats.json"

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0") or "0")
CHANNEL_ID = os.getenv("CHANNEL_ID")
GROUP_ID = os.getenv("GROUP_ID")

_conflict_notified = False


async def _error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Global error handler to keep polling stable and avoid noisy tracebacks."""
    global _conflict_notified  # noqa: PLW0603
    err = getattr(context, "error", None)
    if isinstance(err, Conflict):
        if not _conflict_notified and ADMIN_USER_ID:
            _conflict_notified = True
            try:
                await context.bot.send_message(
                    chat_id=ADMIN_USER_ID,
                    text=(
                        "⚠️ Telegram Conflict: في نسخة تانية شغالة بنفس التوكن. "
                        "اقفل أي نسخة تانية (local/Render) عشان يمنع getUpdates conflict."
                    ),
                )
            except Exception:
                pass
        # Avoid re-raising to prevent repeated stack traces
        return

    # Fallback logging
    try:
        _log(f"Unhandled error: {err}")
    except Exception:
        pass


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
    status: Literal["published", "no_news", "sleeping", "error"]
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


def _get_channel_id_from_config() -> Optional[str]:
    cfg = _load_config()
    cid = cfg.get("channel_id")
    if isinstance(cid, str) and cid.strip():
        return cid.strip()
    if CHANNEL_ID and str(CHANNEL_ID).strip():
        return str(CHANNEL_ID).strip()
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


def _load_platform_config() -> dict:
    """Load platform configuration with CTA templates and priorities."""
    try:
        config_path = BASE_DIR / "platform_config.json"
        if config_path.exists():
            data = json.loads(config_path.read_text(encoding="utf-8"))

            # Apply active brand overrides from config.json (non-secret, dashboard-managed)
            try:
                cfg = _load_config()
                active_key = str(cfg.get("active_brand") or "").strip()
                brands = (
                    cfg.get("brands") if isinstance(cfg.get("brands"), dict) else {}
                )
                brand = (
                    brands.get(active_key)
                    if active_key and isinstance(brands, dict)
                    else None
                )
                if isinstance(brand, dict):
                    overrides = brand.get("platforms")
                    if isinstance(overrides, dict):
                        data.setdefault("platforms", {})
                        for k, v in overrides.items():
                            if not isinstance(v, dict):
                                continue
                            data["platforms"].setdefault(k, {})
                            data["platforms"][k].update(v)

                    fb_url = str(brand.get("facebook_page_url") or "").strip()
                    if fb_url:
                        data.setdefault("platforms", {})
                        data["platforms"].setdefault("facebook", {})
                        data["platforms"]["facebook"]["page_url"] = fb_url
            except Exception:
                pass

            return data
    except Exception as e:
        print(f"⚠️ Failed to load platform_config.json: {e}")
    return {"platforms": {}, "cross_platform_cta": {"enabled": False}}


def get_admin_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            ["⚡ Force Fetch", "📊 Stats"],
            ["📢 Broadcast", "🛑 Status Toggle"],
            ["📝 Edit Prompt", "📡 Feeds"],
            ["📋 Logs", "ℹ️ System Info"],
            ["🤖 Brands Status", "🌐 Platform Status"],
            ["🧪 Test Platforms"],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def _parse_hhmm(value: str, *, fallback: str = "09:00") -> str:
    s = str(value or "").strip()
    if not s:
        return fallback
    parts = s.split(":")
    if len(parts) != 2:
        return fallback
    try:
        hh = int(parts[0])
        mm = int(parts[1])
    except Exception:
        return fallback
    if hh < 0 or hh > 23 or mm < 0 or mm > 59:
        return fallback
    return f"{hh:02d}:{mm:02d}"


def _get_brand_schedule(brand_key: str, brand_cfg: dict) -> dict:
    """Resolve brand schedule. Defaults: Arabic=Cairo, others=America/New_York."""
    # Defaults
    default_tz = "Africa/Cairo" if str(brand_key).endswith("_ar") or str(brand_cfg.get("language") or "").lower().startswith("ar") else "America/New_York"
    default_start = "09:00"
    default_end = "23:00"

    raw = brand_cfg.get("schedule") if isinstance(brand_cfg, dict) else None
    if not isinstance(raw, dict):
        raw = {}

    tz = str(raw.get("timezone") or default_tz).strip() or default_tz
    start = _parse_hhmm(raw.get("start") or "", fallback=default_start)
    end = _parse_hhmm(raw.get("end") or "", fallback=default_end)
    return {"timezone": tz, "start": start, "end": end}


def _brand_awake_status(brand_key: str, brand_cfg: dict) -> dict:
    """Return {awake: bool, tz, now, start, end, until_seconds}.

    Note: If schedule window crosses midnight, we treat it as overnight.
    """
    sched = _get_brand_schedule(brand_key, brand_cfg)
    tz_name = sched["timezone"]
    start = sched["start"]
    end = sched["end"]

    try:
        import pytz

        tz = pytz.timezone(tz_name)
        now_local = datetime.now(tz)
    except Exception:
        now_local = datetime.utcnow()
        tz_name = "UTC"

    hh, mm = (int(x) for x in start.split(":"))
    eh, em = (int(x) for x in end.split(":"))
    start_min = hh * 60 + mm
    end_min = eh * 60 + em
    now_min = now_local.hour * 60 + now_local.minute

    if start_min <= end_min:
        awake = start_min <= now_min <= end_min
        if awake:
            until = 0
        else:
            # seconds until next start
            if now_min < start_min:
                delta_min = start_min - now_min
            else:
                delta_min = (24 * 60 - now_min) + start_min
            until = delta_min * 60
    else:
        # Overnight window (e.g. 20:00-06:00)
        awake = now_min >= start_min or now_min <= end_min
        if awake:
            until = 0
        else:
            delta_min = start_min - now_min
            until = max(delta_min, 0) * 60

    return {
        "awake": bool(awake),
        "timezone": tz_name,
        "now": now_local.strftime("%H:%M"),
        "start": start,
        "end": end,
        "until_seconds": int(until),
    }


def _read_brand_stats() -> dict:
    try:
        if not BRAND_STATS_PATH.exists():
            return {}
        data = json.loads(BRAND_STATS_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_brand_stats(data: dict) -> None:
    try:
        BRAND_STATS_PATH.parent.mkdir(parents=True, exist_ok=True)
        BRAND_STATS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def _touch_brand_stats(brand_key: str, *, title: str = "") -> None:
    data = _read_brand_stats()
    existing = data.get(brand_key)
    row = existing if isinstance(existing, dict) else {}
    posts = int(row.get("posts", 0) or 0)
    row["posts"] = posts + 1
    row["last_published_at"] = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    if title:
        row["last_title"] = str(title)[:160]
    data[brand_key] = row
    _write_brand_stats(data)


def get_sales_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("📢 تابعنا على القناة", url=CHANNEL_URL),
                InlineKeyboardButton("💬 جروب المناقشة", url=GROUP_URL),
            ]
        ]
    )


def get_brand_keyboard() -> ReplyKeyboardMarkup:
    """Keyboard for brand-specific bots (admin-only)."""
    return ReplyKeyboardMarkup(
        [
            ["⚡ Force Fetch", "📊 Stats"],
            ["📡 Feeds", "🧪 Test Platforms"],
            ["🌐 Platform Status", "ℹ️ System Info"],
            ["📋 Logs"],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def _get_brand_stats_text(brand_key: str) -> str:
    cfg = _load_config()
    brands = cfg.get("brands") if isinstance(cfg.get("brands"), dict) else {}
    brand_cfg = brands.get(brand_key) if isinstance(brands, dict) else None
    if not isinstance(brand_cfg, dict):
        return f"❌ Unknown brand: {brand_key}"

    feeds = brand_cfg.get("feeds")
    feeds_count = len(feeds) if isinstance(feeds, list) else 0

    enabled_cfg: list[str] = []
    if isinstance(brand_cfg.get("platforms"), dict):
        for p, v in (brand_cfg.get("platforms") or {}).items():
            if isinstance(v, dict) and v.get("enabled") is True:
                enabled_cfg.append(str(p))

    sched = _brand_awake_status(brand_key, brand_cfg)
    if sched.get("awake") is True:
        sched_txt = f"Awake ({sched.get('timezone')} {sched.get('now')}, {sched.get('start')}-{sched.get('end')})"
    else:
        mins = max(1, int((sched.get("until_seconds") or 0) / 60))
        sched_txt = f"Sleeping ({sched.get('timezone')} {sched.get('now')}, wakes in ~{mins}m)"

    st = _read_brand_stats()
    row_any = st.get(brand_key)
    row = row_any if isinstance(row_any, dict) else {}
    posts = int(row.get("posts", 0) or 0)
    last_at = str(row.get("last_published_at") or "")
    last_title = str(row.get("last_title") or "")

    channel_id = str(brand_cfg.get("channel_id") or "").strip() or "None"
    lang = str(brand_cfg.get("language") or "").strip() or "?"
    name = str(brand_cfg.get("display_name") or brand_key)

    msg = (
        f"📊 Stats ({name} | {brand_key} | {lang})\n\n"
        f"🕒 {sched_txt}\n"
        f"🧩 Feeds: {feeds_count}\n"
        f"📱 Platforms(cfg): {', '.join(enabled_cfg) if enabled_cfg else 'none'}\n"
        f"📣 Channel: {channel_id}\n"
        f"✅ Published: {posts}\n"
    )
    if last_at:
        msg += f"🕐 Last: {last_at}\n"
    if last_title:
        msg += f"📝 Last title: {last_title[:120]}"
    return msg


async def admin_list_feeds_for_brand(
    update: Update, context: ContextTypes.DEFAULT_TYPE, *, brand_key: str
) -> None:
    if not update.message:
        return
    cfg = _load_config()
    brands = cfg.get("brands") if isinstance(cfg.get("brands"), dict) else {}
    brand_cfg = brands.get(brand_key) if isinstance(brands, dict) else None
    feeds = brand_cfg.get("feeds") if isinstance(brand_cfg, dict) else None
    if not isinstance(feeds, list) or not feeds:
        await update.message.reply_text(f"📡 Active Feeds (0) for {brand_key}")
        return

    cleaned = [str(x).strip() for x in feeds if isinstance(x, str) and str(x).strip()]
    preview = cleaned[:20]
    lines = [f"📡 Active Feeds ({len(cleaned)}) for {brand_key}:\n"]
    for i, url in enumerate(preview, 1):
        short = (url[:60] + "...") if len(url) > 60 else url
        lines.append(f"{i}. {short}")
    if len(cleaned) > len(preview):
        lines.append(f"\n...and {len(cleaned) - len(preview)} more.")
    await update.message.reply_text("\n".join(lines))


def _is_admin(update: Update) -> bool:
    return bool(update.effective_user and update.effective_user.id == ADMIN_USER_ID)


def _start_brand_bots() -> None:
    """Start one polling bot per configured brand that has a TELEGRAM_TOKEN_<SUFFIX>.

    Controlled by env ENABLE_BRAND_BOTS=1.
    """
    if str(os.getenv("ENABLE_BRAND_BOTS", "") or "").strip().lower() not in {"1", "true", "yes", "on"}:
        print("ℹ️ Brand bots are disabled (set ENABLE_BRAND_BOTS=1 to enable)")
        return

    try:
        import threading
        import traceback
        from brand_context import env_get

        cfg = _load_config()
        brands = cfg.get("brands") if isinstance(cfg.get("brands"), dict) else {}
        if not isinstance(brands, dict) or not brands:
            print("ℹ️ No brands configured; skipping brand bots")
            return

        for brand_key, brand_cfg in brands.items():
            if not isinstance(brand_key, str) or not isinstance(brand_cfg, dict):
                continue
            token = env_get("TELEGRAM_TOKEN", platform="telegram", brand=brand_cfg)
            token = str(token or "").strip()
            if not token:
                continue

            # Do not start a duplicate of the supervisor bot
            if TELEGRAM_TOKEN and token == TELEGRAM_TOKEN:
                continue

            def _runner(bk: str, tkn: str) -> None:
                try:
                    app_b = ApplicationBuilder().token(tkn).build()

                    async def _start_brand(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
                        if not update.message:
                            return
                        if not _is_admin(update):
                            await update.message.reply_text("❌ غير مصرح")
                            return
                        await update.message.reply_text(
                            f"✅ {bk} bot ready.",
                            reply_markup=get_brand_keyboard(),
                        )

                    async def _brand_force_fetch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
                        if not update.message:
                            return
                        if not _is_admin(update):
                            await update.message.reply_text("❌ غير مصرح")
                            return
                        msg = await update.message.reply_text("🕵️‍♂️ جاري الفحص: بتصل بالمصادر...")
                        try:
                            import asyncio

                            result = await asyncio.wait_for(
                                fetch_and_publish(
                                    context,
                                    override_status=True,
                                    brand_override=bk,
                                ),
                                timeout=180,
                            )
                            status = result.get("status")
                            if status == "published":
                                await msg.edit_text(f"✅ تم النشر! {result.get('title','')}")
                                return
                            if status == "no_news":
                                await msg.edit_text("⚠️ مفيش أخبار جديدة.")
                                return
                            if status == "sleeping":
                                await msg.edit_text(f"😴 نايم دلوقتي. {result.get('error','')}")
                                return
                            await msg.edit_text(f"❌ خطأ: {result.get('error','Unknown error')}")
                        except asyncio.TimeoutError:
                            await msg.edit_text("⏱️ العملية طولت (تحميل صورة/AI). جرّب تاني.")
                        except Exception as exc:  # noqa: BLE001
                            await msg.edit_text(f"❌ خطأ: {exc}")

                    async def _brand_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
                        if not update.message:
                            return
                        if not _is_admin(update):
                            await update.message.reply_text("❌ غير مصرح")
                            return
                        await update.message.reply_text(_get_brand_stats_text(bk))

                    async def _brand_feeds(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
                        if not update.message:
                            return
                        if not _is_admin(update):
                            await update.message.reply_text("❌ غير مصرح")
                            return
                        await admin_list_feeds_for_brand(update, context, brand_key=bk)

                    async def _brand_test_platforms(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
                        if not update.message:
                            return
                        if not _is_admin(update):
                            await update.message.reply_text("❌ غير مصرح")
                            return
                        # Temporarily set active_brand for better UX in platform status (non-critical)
                        cfg2 = _load_config()
                        cfg2["active_brand"] = bk
                        _save_config(cfg2)
                        await admin_test_platforms(update, context)

                    async def _brand_platform_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
                        if not update.message:
                            return
                        if not _is_admin(update):
                            await update.message.reply_text("❌ غير مصرح")
                            return
                        cfg2 = _load_config()
                        cfg2["active_brand"] = bk
                        _save_config(cfg2)
                        await admin_platform_status(update, context)

                    async def _brand_system_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
                        if not update.message:
                            return
                        if not _is_admin(update):
                            await update.message.reply_text("❌ غير مصرح")
                            return
                        cfg2 = _load_config()
                        cfg2["active_brand"] = bk
                        _save_config(cfg2)
                        await admin_system_info(update, context)

                    async def _brand_logs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
                        if not update.message:
                            return
                        if not _is_admin(update):
                            await update.message.reply_text("❌ غير مصرح")
                            return
                        await admin_view_logs(update, context)

                    app_b.add_error_handler(_error_handler)
                    app_b.add_handler(CommandHandler("start", _start_brand))
                    app_b.add_handler(MessageHandler(filters.User(user_id=ADMIN_USER_ID) & filters.Regex(r"^⚡ Force Fetch$"), _brand_force_fetch))
                    app_b.add_handler(MessageHandler(filters.User(user_id=ADMIN_USER_ID) & filters.Regex(r"^📊 Stats$"), _brand_stats))
                    app_b.add_handler(MessageHandler(filters.User(user_id=ADMIN_USER_ID) & filters.Regex(r"^📡 Feeds$"), _brand_feeds))
                    app_b.add_handler(MessageHandler(filters.User(user_id=ADMIN_USER_ID) & filters.Regex(r"^🧪 Test Platforms$"), _brand_test_platforms))
                    app_b.add_handler(MessageHandler(filters.User(user_id=ADMIN_USER_ID) & filters.Regex(r"^🌐 Platform Status$"), _brand_platform_status))
                    app_b.add_handler(MessageHandler(filters.User(user_id=ADMIN_USER_ID) & filters.Regex(r"^ℹ️ System Info$"), _brand_system_info))
                    app_b.add_handler(MessageHandler(filters.User(user_id=ADMIN_USER_ID) & filters.Regex(r"^📋 Logs$"), _brand_logs))

                    print(f"🤖 Starting brand bot polling: {bk}")
                    # IMPORTANT: Brand bots run in background threads (supervisor bot is in main thread).
                    # On Linux (Render), registering signal handlers from a non-main thread crashes with:
                    # "set_wakeup_fd only works in main thread".
                    # Disabling stop_signals avoids signal registration inside the thread.
                    app_b.run_polling(drop_pending_updates=True, stop_signals=None)
                except Exception:
                    print(f"❌ Brand bot failed: {bk}")
                    traceback.print_exc()

            th = threading.Thread(target=_runner, args=(brand_key, token), daemon=True)
            th.start()
    except Exception:
        import traceback

        print("❌ Failed to start brand bots")
        traceback.print_exc()


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


async def _generate_platform_contents(
    post: dict,
    title: str,
    link: str,
    system_prompt: Optional[str],
    telegram_post: str,
    facebook_post: str,
    blog_title: str,
    blog_content_md: str,
    discord_msg: str,
) -> dict:
    """Generate platform-specific content using AI routing."""
    from ai_processor import rewrite_with_ai

    cfg = _load_config()
    active_key = str(cfg.get("active_brand") or "").strip() or "robovai_ar"
    brands = cfg.get("brands") if isinstance(cfg.get("brands"), dict) else {}
    brand_cfg = brands.get(active_key) if isinstance(brands, dict) else None
    brand_language = (
        str(brand_cfg.get("language") or "en")
        if isinstance(brand_cfg, dict)
        else "en"
    )

    platforms_to_generate = [
        "blogger",
        "devto",
        "facebook",
        "telegram",
        "linkedin",
        "discord",
    ]

    contents: dict = {}

    for platform in platforms_to_generate:
        try:
            ai_result = rewrite_with_ai(
                title=post.get("title", ""),
                summary=post.get("summary", ""),
                link=link,
                system_prompt=system_prompt,
                platform=platform,
                brand_name=active_key,
                brand_language=brand_language,
            )

            if ai_result:
                if platform in ["blogger", "devto"]:
                    contents[platform] = {
                        "caption": ai_result.get("blog_content_md", ""),
                        "title": ai_result.get("blog_title", ""),
                    }
                elif platform == "facebook":
                    contents[platform] = {"caption": ai_result.get("facebook_post", "")}
                elif platform == "telegram":
                    contents[platform] = {"caption": ai_result.get("telegram_post", "")}
                elif platform == "linkedin":
                    contents[platform] = {
                        "caption": ai_result.get("linkedin_post")
                        or ai_result.get("facebook_post", "")
                    }
                elif platform == "discord":
                    contents[platform] = {
                        "caption": ai_result.get("discord_msg")
                        or ai_result.get("telegram_post", "")
                    }
                continue

            raise ValueError("Empty AI result")

        except Exception as e:
            print(f"⚠️ Failed to generate content for {platform}: {e}")
            if platform == "blogger":
                contents[platform] = {"caption": blog_content_md, "title": blog_title}
            elif platform == "devto":
                contents[platform] = {"caption": blog_content_md, "title": blog_title}
            elif platform == "facebook":
                contents[platform] = {"caption": facebook_post}
            elif platform == "telegram":
                contents[platform] = {"caption": telegram_post}
            elif platform == "linkedin":
                contents[platform] = {"caption": facebook_post or telegram_post}
            elif platform == "discord":
                contents[platform] = {"caption": discord_msg or telegram_post}

    contents.setdefault("discord", {"caption": discord_msg or telegram_post})
    contents.setdefault("linkedin", {"caption": facebook_post or telegram_post})

    return contents


def _pick_next_brand_key(cfg: dict, *, ignore_schedule: bool = False) -> str:
    """Pick next brand to publish for (round-robin).

    Skips brands without feeds/platforms and (by default) brands that are sleeping.
    """
    brands = cfg.get("brands") if isinstance(cfg.get("brands"), dict) else {}
    if not isinstance(brands, dict) or not brands:
        return str(cfg.get("active_brand") or "").strip() or "robovai_ar"

    candidates_all: list[str] = []
    for key, brand in brands.items():
        if not isinstance(key, str) or not key.strip() or not isinstance(brand, dict):
            continue
        feeds = brand.get("feeds")
        if not isinstance(feeds, list) or not any(isinstance(f, str) and f.strip() for f in feeds):
            continue
        platforms = brand.get("platforms")
        if not isinstance(platforms, dict):
            continue
        if not any(isinstance(v, dict) and v.get("enabled") is True for v in platforms.values()):
            continue
        candidates_all.append(key.strip())

    # Apply schedule filter unless overridden (Force Fetch)
    candidates = list(candidates_all)
    if not ignore_schedule:
        filtered: list[str] = []
        for k in candidates:
            brand_cfg = brands.get(k) if isinstance(brands, dict) else None
            if isinstance(brand_cfg, dict):
                st = _brand_awake_status(k, brand_cfg)
                if st.get("awake") is True:
                    filtered.append(k)
        candidates = filtered

    if not candidates:
        # If we had candidates but all are sleeping, signal no-publish.
        if candidates_all and not ignore_schedule:
            return ""
        return str(cfg.get("active_brand") or "").strip() or "robovai_ar"

    candidates = sorted(set(candidates))
    idx_raw = cfg.get("brand_rotation_index", 0)
    idx = idx_raw if isinstance(idx_raw, int) and idx_raw >= 0 else 0
    chosen = candidates[idx % len(candidates)]
    cfg["brand_rotation_index"] = (idx + 1) % len(candidates)
    cfg["active_brand"] = chosen

    # Keep top-level compatibility keys in sync
    brand_cfg = brands.get(chosen)
    if isinstance(brand_cfg, dict):
        if isinstance(brand_cfg.get("system_prompt"), str):
            cfg["system_prompt"] = brand_cfg.get("system_prompt", "")
        if isinstance(brand_cfg.get("feeds"), list):
            cfg["feeds"] = brand_cfg.get("feeds", [])
        if isinstance(brand_cfg.get("channel_id"), str):
            cfg["channel_id"] = brand_cfg.get("channel_id", "")
        if isinstance(brand_cfg.get("group_id"), str):
            cfg["group_id"] = brand_cfg.get("group_id", "")

    return chosen


async def _publish_sequential_with_ctas(
    publisher,
    platform_contents: dict,
    platform_config: dict,
    image_url: Optional[str],
    image_local_path: Optional[str],
    link: Optional[str],
    telegram_context,
) -> dict:
    """Publish platforms sequentially with URL collection and CTA injection."""
    import asyncio

    enabled_platforms = publisher.enabled_platforms
    platforms_config = platform_config.get("platforms", {})
    cta_config = platform_config.get("cross_platform_cta", {})
    cta_enabled = bool(cta_config.get("enabled", False))
    cta_templates = cta_config.get("templates", {})

    platform_priority: list[tuple[str, int]] = []
    for p in enabled_platforms:
        priority = platforms_config.get(p, {}).get("priority", 99)
        platform_priority.append((p, priority))
    platform_priority.sort(key=lambda x: x[1])
    sorted_platforms = [p[0] for p in platform_priority]

    print(f"🔄 Sequential publishing order: {sorted_platforms}")

    published_urls: dict[str, str] = {}
    results: dict[str, Any] = {}

    def _canonical_url() -> Optional[str]:
        return published_urls.get("blogger") or published_urls.get("devto")

    def _facebook_page_url() -> str:
        cfg_url = str(
            platforms_config.get("facebook", {}).get("page_url", "") or ""
        ).strip()
        if cfg_url:
            return cfg_url
        fb_page_id = (os.getenv("FACEBOOK_PAGE_ID") or "").strip()
        if fb_page_id:
            return f"https://www.facebook.com/{fb_page_id}"
        return ""

    def _cta_buttons() -> list[dict[str, str]]:
        buttons: list[dict[str, str]] = []
        if published_urls.get("blogger"):
            buttons.append({"text": "📝 المقال كامل", "url": published_urls["blogger"]})
        if published_urls.get("devto"):
            buttons.append({"text": "📌 نسخة Dev.to", "url": published_urls["devto"]})
        if published_urls.get("facebook"):
            buttons.append(
                {"text": "💬 ناقش على فيسبوك", "url": published_urls["facebook"]}
            )
        return buttons

    def _filter_cta_text(cta_text: str, url_candidates: list[str]) -> str:
        lines: list[str] = []
        for raw in cta_text.split("\n"):
            line = raw.rstrip()
            stripped = line.strip()
            if not stripped:
                continue
            # Empty markdown links like [X]() or ( )
            if "]()" in stripped or stripped.endswith("()"):
                continue
            if stripped.endswith(":"):
                continue
            if (
                ":" in stripped
                and url_candidates
                and not any(u in stripped for u in url_candidates)
            ):
                continue
            lines.append(line)
        return "\n".join(lines).strip()

    for platform in sorted_platforms:
        try:
            p_config = platforms_config.get(platform, {})
            delay_minutes = int(p_config.get("delay_minutes", 0) or 0)
            enable_cta = bool(p_config.get("enable_cta", False))

            if published_urls and delay_minutes > 0:
                print(
                    f"⏳ Waiting {delay_minutes} minutes before publishing to {platform}..."
                )
                await asyncio.sleep(delay_minutes * 60)

            content_data = platform_contents.get(platform, {})
            caption = str(content_data.get("caption") or "").strip()
            title = content_data.get("title")

            # TEXT CTAs only where it makes sense (blog/devto). Not Telegram/Facebook.
            if (
                cta_enabled
                and enable_cta
                and caption
                and platform not in {"telegram", "facebook"}
            ):
                cta_template = str(cta_templates.get(platform, "") or "")
                if cta_template and published_urls:
                    blogger_url = published_urls.get("blogger", "")
                    devto_url = published_urls.get("devto", "")
                    # Dev.to wants stable page URL even before FB post exists
                    facebook_url = _facebook_page_url() or published_urls.get(
                        "facebook", ""
                    )
                    url_candidates = [
                        u for u in [blogger_url, devto_url, facebook_url] if u
                    ]

                    raw_cta = cta_template.format(
                        blogger_url=blogger_url,
                        devto_url=devto_url,
                        facebook_url=facebook_url,
                    )
                    filtered = _filter_cta_text(raw_cta, url_candidates)
                    if filtered:
                        caption = caption.rstrip() + "\n\n" + filtered
                        print(f"✅ Injected CTA for {platform}")

            payload_for_platform: dict[str, Any] = {"caption": caption}
            if title:
                payload_for_platform["title"] = title

            canonical = _canonical_url()
            if platform in {"facebook", "linkedin"} and canonical:
                payload_for_platform["link_override"] = canonical
            if platform == "facebook" and canonical:
                payload_for_platform["force_link_post"] = True
            if platform == "devto" and canonical:
                payload_for_platform["link_override"] = canonical

            if platform == "telegram":
                payload_for_platform["disable_link"] = True
                payload_for_platform["cta_buttons"] = _cta_buttons()
                try:
                    cfg = _load_config()
                    cid = cfg.get("channel_id")
                    if isinstance(cid, str) and cid.strip():
                        payload_for_platform["channel_id"] = cid.strip()
                except Exception:
                    pass

            if platform == "discord" and canonical:
                payload_for_platform["caption"] = (
                    caption.rstrip() + f"\n\nاقرأ المزيد: {canonical}"
                    if caption
                    else f"اقرأ المزيد: {canonical}"
                )

            payloads = {platform: payload_for_platform}

            print(f"📤 Publishing to {platform}...")
            platform_results = await publisher.publish(
                caption=caption,
                link=None,
                image_url=image_url,
                image_local_path=image_local_path,
                platforms=[platform],
                platform_payloads=payloads,
                telegram_context=telegram_context,
                send_reports=True,
            )

            result = platform_results.get(platform, {})
            results[platform] = result

            if isinstance(result, dict) and (
                result.get("status") == "success" or result.get("success")
            ):
                url = result.get("url") or result.get("post_url") or result.get("link")
                if url:
                    published_urls[platform] = url
                    print(f"✅ {platform} published: {url}")
                else:
                    print(f"✅ {platform} published (no URL returned)")
            else:
                error = result.get("error") or result.get("message", "Unknown error")
                print(f"❌ {platform} failed: {error}")

        except Exception as e:
            print(f"❌ Error publishing to {platform}: {e}")
            import traceback

            traceback.print_exc()
            results[platform] = {"status": "error", "error": str(e)}

    print(f"\n✅ Published URLs: {published_urls}")
    return results


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
            result = upload_image_if_configured(local_path, name)
            if result:
                return result
            print("⚠️ MediaPipeline: Storj returned None")
        except Exception as exc:
            print(f"⚠️ MediaPipeline: Storj upload failed: {exc}")
        return None

    def _upload_to_imgbb(local_path: str) -> Optional[str]:
        """Upload image to ImgBB as fallback (free, stable, no expiry)"""
        try:
            api_key = os.getenv("IMGBB_API_KEY")
            if not api_key:
                print("⚠️ MediaPipeline: IMGBB_API_KEY not set")
                return None

            with open(local_path, "rb") as img_file:
                response = requests.post(
                    "https://api.imgbb.com/1/upload",
                    data={"key": api_key},
                    files={"image": img_file},
                    timeout=30,
                )

            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    url = data.get("data", {}).get("url")
                    if url:
                        print(f"✅ ImgBB upload successful: {url[:60]}...")
                        return url
            print(f"⚠️ ImgBB upload failed: {response.status_code}")
        except Exception as exc:
            print(f"⚠️ MediaPipeline: ImgBB upload failed: {exc}")
        return None

    # Strategy 1: Use RSS image if available (download locally then upload to ImgBB)
    rss_image = post.get("image")
    if rss_image and isinstance(rss_image, str) and rss_image.startswith("http"):
        print(f"✅ Strategy 1: Found RSS image: {rss_image[:60]}...")
        local = _download_image(rss_image)
        if local:
            public = _upload_to_imgbb(local)
            if not public:
                print("🔄 MediaPipeline: Trying Storj fallback...")
                public = _upload_to_storj(local)
            if public:
                return {"image_url": public, "image_local_path": local}
            # If both fail, return local for Telegram and RSS URL for others
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
                public_url = _upload_to_imgbb(str(local_path))
                if not public_url:
                    print("🔄 MediaPipeline: Trying Storj fallback...")
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

        public = _upload_to_imgbb(str(fallback_path))
        if not public:
            print("🔄 MediaPipeline: Trying Storj fallback for placeholder...")
            public = _upload_to_storj(str(fallback_path))
        if public:
            return {"image_url": public, "image_local_path": str(fallback_path)}
        return {"image_url": None, "image_local_path": str(fallback_path)}
    except Exception as exc:
        print(f"⚠️ MediaPipeline: fallback image failed: {exc}")
        return {"image_url": None, "image_local_path": None}


async def fetch_and_publish(
    context: ContextTypes.DEFAULT_TYPE,
    *,
    override_status: bool = False,
    brand_override: Optional[str] = None,
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

    if not override_status and not _is_system_active():
        return {"status": "error", "error": "System is paused"}

    # Multi-brand sequential publishing (preferred)
    cfg = _load_config()
    if isinstance(cfg.get("brands"), dict) and cfg.get("brands"):
        brands = cfg.get("brands") if isinstance(cfg.get("brands"), dict) else {}

        if brand_override:
            brand_key = str(brand_override).strip()
        else:
            if cfg.get("auto_rotate_brands", True):
                brand_key = _pick_next_brand_key(cfg, ignore_schedule=override_status)
            else:
                brand_key = str(cfg.get("active_brand") or "").strip()

        # Validate requested brand exists
        if brand_key and isinstance(brands, dict) and brand_key not in brands:
            return {
                "status": "error",
                "error": f"Unknown brand: {brand_key}",
            }

        if not brand_key and not override_status and not brand_override:
            # All brands are sleeping
            try:
                waits: list[tuple[int, str]] = []
                for k, b in (brands or {}).items():
                    if not isinstance(k, str) or not isinstance(b, dict):
                        continue
                    st = _brand_awake_status(k, b)
                    if st.get("awake") is True:
                        waits.append((0, k))
                    else:
                        waits.append((int(st.get("until_seconds") or 0), k))
                waits = [w for w in waits if w[0] > 0]
                if waits:
                    waits.sort(key=lambda x: x[0])
                    mins = max(1, int(waits[0][0] / 60))
                    return {
                        "status": "sleeping",
                        "error": f"All brands are sleeping. Next wake in ~{mins} min.",
                    }
            except Exception:
                pass
            return {
                "status": "sleeping",
                "error": "All brands are sleeping right now.",
            }

        # Only persist rotation/active brand when we are actually rotating
        if not brand_override:
            _save_config(cfg)

        try:
            brands_dbg = cfg.get("brands") if isinstance(cfg.get("brands"), dict) else {}
            brand_dbg = brands_dbg.get(brand_key) if isinstance(brands_dbg, dict) else None
            enabled_dbg = []
            if isinstance(brand_dbg, dict) and isinstance(brand_dbg.get("platforms"), dict):
                for p, v in brand_dbg.get("platforms", {}).items():
                    if isinstance(v, dict) and v.get("enabled") is True:
                        enabled_dbg.append(str(p))
            print(f"🧭 Selected brand: {brand_key} | enabled_platforms_in_config={enabled_dbg}")
        except Exception:
            pass

        brand_cfg = brands.get(brand_key) if isinstance(brands, dict) else None
        brand_language = (
            str(brand_cfg.get("language") or "en")
            if isinstance(brand_cfg, dict)
            else "en"
        )

        post = fetch_random_new_post(brand=brand_key)
        if not post:
            return {"status": "no_news"}

        # Ensure media availability (for platform publishers that need it)
        title = str(post.get("title", "") or "").strip()
        media_result = prepare_media(post, title)
        # Attach (used by some publishers)
        post["image"] = media_result.get("image_url")
        post["image_local_path"] = media_result.get("image_local_path")

        try:
            from multi_platform_publisher import MultiPlatformPublisher
            from sequential_publisher import SequentialPublisher

            platform_publisher = MultiPlatformPublisher(brand_key=brand_key)
            try:
                print(
                    f"🔐 Runtime enabled platforms (env+brand): {getattr(platform_publisher, 'enabled_platforms', [])}"
                )
            except Exception:
                pass
            seq = SequentialPublisher(cfg)
            published = await seq.publish_item(
                brand_name=brand_key,
                feed_item=post,
                platform_publisher=platform_publisher,
                telegram_context=context,
                fast_mode=override_status,
            )

            if published:
                _touch_brand_stats(brand_key, title=str(post.get("title", "") or "").strip())
                return {
                    "status": "published",
                    "title": str(post.get("title", "") or "").strip(),
                }
            # Provide a more actionable error for ops
            enabled_runtime = []
            try:
                enabled_runtime = list(getattr(platform_publisher, "enabled_platforms", []) or [])
            except Exception:
                enabled_runtime = []

            brands = cfg.get("brands") if isinstance(cfg.get("brands"), dict) else {}
            brand_cfg = brands.get(brand_key) if isinstance(brands, dict) else None
            enabled_cfg = []
            if isinstance(brand_cfg, dict) and isinstance(brand_cfg.get("platforms"), dict):
                for p, v in brand_cfg.get("platforms", {}).items():
                    if isinstance(v, dict) and v.get("enabled") is True:
                        enabled_cfg.append(str(p))

            missing = [p for p in enabled_cfg if p not in enabled_runtime]
            errors_hint = ""
            try:
                last_errors = getattr(seq, "last_errors", [])
                if isinstance(last_errors, list) and last_errors:
                    sample = last_errors[:3]
                    parts = []
                    for e in sample:
                        if isinstance(e, dict):
                            p = str(e.get("platform") or "")
                            msg = str(e.get("error") or "")
                            if p and msg:
                                parts.append(f"{p}: {msg[:80]}")
                    if parts:
                        errors_hint = " | errors=" + "; ".join(parts)
            except Exception:
                errors_hint = ""
            hint = ""
            if missing:
                hint = f" | missing_credentials_for={missing} (check Render env vars for this brand suffix)"
            return {
                "status": "error",
                "error": f"No platforms published (brand={brand_key}, enabled_in_config={enabled_cfg}, enabled_runtime={enabled_runtime}){hint}{errors_hint}",
            }

        except Exception as exc:  # noqa: BLE001
            return {"status": "error", "error": f"Sequential publish failed: {exc}"}

    # Legacy single-brand pipeline

    channel_id = _get_channel_id_from_config()
    if not channel_id:
        return {
            "status": "error",
            "error": "CHANNEL_ID is not set (env or config.json)",
        }

    post = fetch_random_new_post()
    if not post:
        return {"status": "no_news"}

    system_prompt = _get_system_prompt_from_config()

    legacy_cfg = _load_config()
    legacy_brand_key = str(legacy_cfg.get("active_brand") or "").strip() or "robovai_ar"
    legacy_brands = legacy_cfg.get("brands") if isinstance(legacy_cfg.get("brands"), dict) else {}
    legacy_brand_cfg = legacy_brands.get(legacy_brand_key) if isinstance(legacy_brands, dict) else None
    legacy_lang = (
        str(legacy_brand_cfg.get("language") or "en")
        if isinstance(legacy_brand_cfg, dict)
        else "en"
    )

    ai = rewrite_with_ai(
        post.get("title", ""),
        post.get("summary", ""),
        post.get("link", ""),
        system_prompt=system_prompt,
        platform="telegram",
        brand_name=legacy_brand_key,
        brand_language=legacy_lang,
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

    # Multi-platform publish with sequential publishing and URL collection
    try:
        from multi_platform_publisher import MultiPlatformPublisher
        import asyncio

        # Load platform config for priority-based sequential publishing
        platform_config = _load_platform_config()

        # Generate platform-specific content with AI routing
        platform_contents = await _generate_platform_contents(
            post,
            title,
            link,
            system_prompt,
            telegram_post,
            facebook_post,
            blog_title,
            blog_content_md,
            discord_msg,
        )

        # Publish sequentially with URL collection and CTA injection
        publisher = MultiPlatformPublisher(use_scheduler=False)
        results = await _publish_sequential_with_ctas(
            publisher=publisher,
            platform_contents=platform_contents,
            platform_config=platform_config,
            image_url=image_url,
            image_local_path=image_local_path,
            link=link,
            telegram_context=context,
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

        cfg = _load_config()
        active_brand_key = str(cfg.get("active_brand") or "").strip()
        brands = cfg.get("brands") if isinstance(cfg.get("brands"), dict) else {}
        brand_cfg = (
            brands.get(active_brand_key)
            if active_brand_key and isinstance(brands, dict)
            else None
        )

        publisher = MultiPlatformPublisher(brand_key=active_brand_key or None)

        platform_payloads: Dict[Any, Dict[str, Any]] = {}
        brand_channel_id = None
        if isinstance(brand_cfg, dict):
            brand_channel_id = str(brand_cfg.get("channel_id") or "").strip() or None

        # Ensure Telegram test targets the configured brand channel (avoids needing env CHANNEL_ID)
        if "telegram" in getattr(publisher, "enabled_platforms", []):
            if not brand_channel_id:
                await update.message.reply_text(
                    "⚠️ Telegram enabled لكن مفيش channel_id للبراند الحالي في config.json"
                )
            else:
                platform_payloads["telegram"] = {"channel_id": brand_channel_id}

        results = await publisher.publish(
            caption=test_caption,
            link=test_link,
            image_url=None,
            telegram_context=context,
            platform_payloads=platform_payloads,
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
        import asyncio

        # Protect against long blocking network calls (image pipeline / external APIs)
        result = await asyncio.wait_for(
            fetch_and_publish(context, override_status=True), timeout=180
        )
        status = result.get("status")
        if status == "published":
            title = result.get("title", "")
            await msg.edit_text(f"✅ تم النشر! {title}")
            return
        if status == "no_news":
            await msg.edit_text("⚠️ مفيش أخبار جديدة. (Evergreen logic skipped for now)")
            return
        await msg.edit_text(f"❌ خطأ: {result.get('error', 'Unknown error')}")
    except asyncio.TimeoutError:
        await msg.edit_text(
            "⏱️ العملية أخدت وقت طويل وممكن تكون علّقت في تحميل صورة/AI. جرّب تاني، أو عطّل توليد الصور مؤقتًا."
        )
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

    active_brand_key = str(cfg.get("active_brand") or "").strip()
    brands = cfg.get("brands") if isinstance(cfg.get("brands"), dict) else {}
    brand_cfg = brands.get(active_brand_key) if active_brand_key and isinstance(brands, dict) else None

    brand_channel = None
    brand_lang = None
    brand_awake = None
    brand_sched = None
    if isinstance(brand_cfg, dict):
        brand_channel = str(brand_cfg.get("channel_id") or "").strip() or None
        brand_lang = str(brand_cfg.get("language") or "").strip() or None
        brand_sched = _brand_awake_status(active_brand_key, brand_cfg)
        brand_awake = bool(brand_sched.get("awake"))

    sched_line = ""
    if isinstance(brand_sched, dict):
        if brand_awake:
            sched_line = f"Schedule: Awake ({brand_sched.get('timezone')} {brand_sched.get('now')}, {brand_sched.get('start')}-{brand_sched.get('end')})\n"
        else:
            mins = max(1, int((brand_sched.get("until_seconds") or 0) / 60))
            sched_line = f"Schedule: Sleeping ({brand_sched.get('timezone')} {brand_sched.get('now')}, wakes in ~{mins} min)\n"

    info = (
        f"ℹ️ **System Info**\n\n"
        f"Status: {status} {'🟢' if status == 'active' else '🔴'}\n"
        f"Model: {model}\n"
        f"Custom Feeds: {feeds_count}\n"
        f"Posts Published: {seen_count}\n\n"
        f"Active brand: {active_brand_key or 'N/A'} ({brand_lang or 'n/a'})\n"
        f"Brand channel: {brand_channel or 'None'}\n"
        + sched_line
        + f"Env CHANNEL_ID: {CHANNEL_ID or 'None'}\n"
        + f"Env GROUP_ID: {GROUP_ID or 'N/A'}\n\n"
        f"Use the buttons below to manage the bot."
    )

    await update.message.reply_text(info, parse_mode="Markdown")


async def admin_brands_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return

    cfg = _load_config()
    brands = cfg.get("brands") if isinstance(cfg.get("brands"), dict) else {}
    if not isinstance(brands, dict) or not brands:
        await update.message.reply_text("❌ No brands found in config.json")
        return

    try:
        from brand_context import env_get
        from multi_platform_publisher import MultiPlatformPublisher
        from telegram import Bot
    except Exception as exc:  # noqa: BLE001
        await update.message.reply_text(f"❌ Import error: {exc}")
        return

    stats = _read_brand_stats()
    lines: list[str] = []
    lines.append("🤖 Brands Status")

    # Keep it short to avoid Telegram 4096 limit
    max_brands = 10
    count = 0
    for brand_key in sorted(brands.keys()):
        if count >= max_brands:
            break
        brand_cfg = brands.get(brand_key)
        if not isinstance(brand_cfg, dict):
            continue
        count += 1

        display = str(brand_cfg.get("display_name") or brand_key)
        lang = str(brand_cfg.get("language") or "").strip() or "?"
        channel_id = str(brand_cfg.get("channel_id") or "").strip() or None

        sched = _brand_awake_status(brand_key, brand_cfg)
        awake = bool(sched.get("awake"))
        if awake:
            sched_txt = f"Awake ({sched.get('timezone')} {sched.get('now')})"
        else:
            mins = max(1, int((sched.get("until_seconds") or 0) / 60))
            sched_txt = f"Sleeping ({sched.get('timezone')} {sched.get('now')}, ~{mins}m)"

        enabled_cfg: list[str] = []
        if isinstance(brand_cfg.get("platforms"), dict):
            for p, v in (brand_cfg.get("platforms") or {}).items():
                if isinstance(v, dict) and v.get("enabled") is True:
                    enabled_cfg.append(str(p))

        runtime_enabled: list[str] = []
        try:
            pub = MultiPlatformPublisher(brand_key=str(brand_key))
            runtime_enabled = list(getattr(pub, "enabled_platforms", []) or [])
        except Exception:
            runtime_enabled = []

        missing = [p for p in enabled_cfg if p not in runtime_enabled]

        # Telegram connectivity check (token valid + channel access)
        tg_ok = "n/a"
        if "telegram" in enabled_cfg:
            token = env_get("TELEGRAM_TOKEN", platform="telegram", brand=brand_cfg)
            token = str(token or "").strip() or None
            if not token:
                tg_ok = "missing token"
            else:
                try:
                    bot = Bot(token=token)
                    me = await bot.get_me()
                    if not me:
                        tg_ok = "invalid token"
                    elif channel_id:
                        try:
                            await bot.get_chat(chat_id=channel_id)
                            tg_ok = "ok"
                        except Exception as e:
                            tg_ok = f"no access ({str(e)[:40]})"
                    else:
                        tg_ok = "missing channel_id"
                except Exception as e:
                    tg_ok = f"invalid ({str(e)[:40]})"

        st_existing = stats.get(brand_key)
        st_row = st_existing if isinstance(st_existing, dict) else {}
        posts = int(st_row.get("posts", 0) or 0)
        last_at = str(st_row.get("last_published_at") or "")

        lines.append(
            f"\n• {display} ({brand_key} | {lang})\n"
            f"  - {sched_txt}\n"
            f"  - cfg: {', '.join(enabled_cfg) if enabled_cfg else 'none'}\n"
            f"  - runtime: {', '.join(runtime_enabled) if runtime_enabled else 'none'}\n"
            f"  - telegram: {tg_ok}\n"
            f"  - missing: {', '.join(missing) if missing else 'none'}\n"
            f"  - published: {posts}{(' | last: ' + last_at) if last_at else ''}"
        )

    msg = "\n".join(lines)
    if len(msg) > 3900:
        msg = msg[:3900] + "\n…(truncated)"
    await update.message.reply_text(msg)


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
    """Initialize bot after startup - clean webhooks and set commands"""
    # Force delete webhook and clear any pending updates to avoid conflicts
    try:
        print("🔧 Cleaning up old webhooks and pending updates...")
        await app.bot.delete_webhook(drop_pending_updates=True)
        # Give Telegram API time to process
        import asyncio

        await asyncio.sleep(1)
        print("✅ Webhooks cleaned successfully")
    except Exception as e:
        print(f"⚠️ Warning during webhook cleanup: {e}")

    # Set bot commands
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

    # Start per-brand bots (optional)
    try:
        _start_brand_bots()
    except Exception as e:
        print(f"⚠️ Failed to start brand bots: {e}")


def main() -> None:
    if not TELEGRAM_TOKEN:
        raise RuntimeError("Missing TELEGRAM_TOKEN")
    if not ADMIN_USER_ID:
        raise RuntimeError("Missing/invalid ADMIN_USER_ID")

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).post_init(post_init).build()

    # Global error handler (prevents noisy tracebacks and handles Conflict gracefully)
    app.add_error_handler(_error_handler)

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
            admin_filter & filters.Regex(r"^🤖 Brands Status$"), admin_brands_status
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
