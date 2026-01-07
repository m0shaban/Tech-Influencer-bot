import json
import os
from datetime import datetime
import time
from pathlib import Path
from typing import Any, Literal, Optional, TypedDict

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

    caption = str(ai.get("caption", "") or "").strip()
    link = str(post.get("link", "") or "").strip()
    title = str(post.get("title", "") or "").strip()
    image_url = post.get("image")

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

    text = _compose_text(caption, link, bool(image_url))

    # Try sending with image first; if it fails, fallback to text-only
    if image_url:
        try:
            await context.bot.send_photo(
                chat_id=CHANNEL_ID, photo=image_url, caption=text
            )
        except Exception as e:
            # Fallback: send as text if image fails
            await context.bot.send_message(chat_id=CHANNEL_ID, text=text)
    else:
        await context.bot.send_message(chat_id=CHANNEL_ID, text=text)

    _log(f"Published: {link}")
    return {"status": "published", "title": title}


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
        ]
    )


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
    )
    app.add_handler(broadcast_conv)

    print("🚀 RoboVAI Bot running. Press Ctrl+C to stop.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
