import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    ContextTypes,
    CommandHandler,
    filters,
    MessageHandler,
)

load_dotenv()

ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0") or "0")
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"
LOG_PATH = BASE_DIR / "bot.log"

WELCOME_LEAD = """👋 *أهلاً بك في RoboVAI Ecosystem*

نحن نصمم حلولاً ذكية لأعمالك 💡

*اختر من هنا:* ⬇️"""

SALES_COPY = """👋 أهلاً بك في RoboVAI Ecosystem

أنت تتحدث الآن مع المساعد الذكي لـ *م. محمد شعبان*. 💡 نحن لا نكتب الكود، نحن نصمم حلولاً للأعمال.

*هل تبحث عن:*
🤖 *Smart Chatbots*: خدمة عملاء آلية 24/7
⚙️ *Business Automation*: تقليل التكاليف وأتمتة العمليات
📊 *Data Solutions*: قرارات مبنية على البيانات

*ابدأ رحلتك الآن:*
📢 تابع أحدث التقنيات: @nextlevelegypt
💬 انضم لمجتمع المناقشة: @nextlevelegyptt

💼 *لطلب استشارة أو تصميم بوت خاص*:
تواصل مباشرة: @mohamedshabanai

_RoboVAI Solutions - Automating Your Success_"""


def _get_real_stats() -> dict:
    stats = {
        "system": "🟢 Online",
        "last_post": "جاري التحديث",
        "feeds": 40,
        "seen": 0,
    }
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            config = json.load(f)
            stats["feeds"] = len(config.get("feeds", []))
    except Exception:
        pass
    try:
        if LOG_PATH.exists():
            with open(LOG_PATH, encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
                if lines:
                    stats["last_post"] = "منذ دقائق"
    except Exception:
        pass
    return stats


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user:
        return

    user_id = update.effective_user.id

    if user_id == ADMIN_USER_ID:
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("⚡ Fetch Now", callback_data="admin_fetch")],
                [InlineKeyboardButton("📊 Stats", callback_data="admin_stats")],
                [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
                [InlineKeyboardButton("ℹ️ Help", callback_data="admin_help")],
            ]
        )
        await update.message.reply_text(
            "*🤖 Welcome Admin*\n\nاختر أمر من القائمة:",
            reply_markup=keyboard,
            parse_mode="Markdown",
        )
    else:
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🤖 Chatbots", url="https://t.me/nextlevelegypt"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "⚙️ Automation", url="https://t.me/nextlevelegyptt"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "💬 Contact", url="https://t.me/mohamedshabanai"
                    )
                ],
            ]
        )
        await update.message.reply_text(
            WELCOME_LEAD, reply_markup=keyboard, parse_mode="Markdown"
        )


async def handle_dm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return

    user_id = update.effective_user.id

    if user_id == ADMIN_USER_ID:
        await _handle_admin_command(update, context)
    else:
        await _handle_lead(update, context)


async def _handle_admin_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not update.message or not update.message.text:
        return

    text = update.message.text.lower()

    if "fetch" in text:
        context.application.job_queue.run_once(
            _force_fetch_job, when=0, data={"channel_id": CHANNEL_ID}
        )
        await update.message.reply_text(
            "🚀 *Command Executed*\nجاري جلب البيانات الطازة...", parse_mode="Markdown"
        )

    elif "stats" in text or "status" in text:
        stats = _get_real_stats()
        msg = (
            f"📊 *System Status*\n\n"
            f"{stats['system']}\n"
            f"📡 Last Post: {stats['last_post']}\n"
            f"🔄 Feeds: {stats['feeds']}\n"
            f"💾 Processed: ~{stats['seen']}"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")

    elif "broadcast" in text:
        await update.message.reply_text(
            "📝 أرسل الرسالة اللي تبغى تنشرها على القناة:", parse_mode="Markdown"
        )

    else:
        help_msg = (
            "*🤖 Admin Commands:*\n\n"
            "`fetch` - شغّل الجلب الآن\n"
            "`stats` - أعرض صحة النظام\n"
            "`broadcast` - أرسل إعلان"
        )
        await update.message.reply_text(help_msg, parse_mode="Markdown")


async def _handle_lead(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🤖 Chatbots", url="https://t.me/nextlevelegypt")],
            [InlineKeyboardButton("⚙️ Automation", url="https://t.me/nextlevelegyptt")],
            [InlineKeyboardButton("💬 Contact", url="https://t.me/mohamedshabanai")],
        ]
    )
    await update.message.reply_text(
        SALES_COPY, reply_markup=keyboard, parse_mode="Markdown"
    )


async def _force_fetch_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    from feed_manager import fetch_random_new_post
    from ai_processor import rewrite_with_ai

    try:
        post = fetch_random_new_post()
        if not post:
            print("❌ Fetch: No new posts found")
            return

        print(f"✅ Fetched post: {post.get('title', 'Unknown')[:50]}")

        ai_result = rewrite_with_ai(
            post.get("title", ""), post.get("summary", ""), post.get("link", "")
        )
        if not ai_result:
            print("❌ AI rewrite failed")
            return

        caption = ai_result.get("telegram_post", "") or ""
        link = post.get("link", "")
        image_url = post.get("image")
        message = caption.strip()
        if link and link not in message:
            message = f"{message}\n\n🔗 لينك الخبر/الأداة: {link}".strip()

        channel_id = context.job.data.get("channel_id") if context.job else None
        if not channel_id:
            print("❌ No channel ID")
            return

        if image_url:
            await context.bot.send_photo(
                chat_id=channel_id, photo=image_url, caption=message
            )
            print(f"✅ Posted with image: {link}")
        else:
            await context.bot.send_message(chat_id=channel_id, text=message)
            print(f"✅ Posted text: {link}")

    except Exception as exc:  # noqa: BLE001
        print(f"❌ Fetch error: {exc}")


def get_handlers() -> list:
    return [
        CommandHandler("start", handle_start),
        CallbackQueryHandler(handle_button_click),
        MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, handle_dm),
    ]


async def handle_button_click(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """معالج الضغط على الأزرار"""
    query = update.callback_query
    if not query or not query.data:
        return

    await query.answer()  # أغلق ال loading indicator

    user_id = update.effective_user.id if update.effective_user else None
    callback_data = query.data

    # Admin buttons
    if callback_data == "admin_fetch":
        context.application.job_queue.run_once(
            _force_fetch_job, when=0, data={"channel_id": CHANNEL_ID}
        )
        await query.edit_message_text(
            "🚀 *جاري جلب البيانات الطازة...*", parse_mode="Markdown"
        )

    elif callback_data == "admin_stats":
        stats = _get_real_stats()
        msg = (
            f"📊 *System Status*\n\n"
            f"{stats['system']}\n"
            f"📡 Last Post: {stats['last_post']}\n"
            f"🔄 Feeds: {stats['feeds']}\n"
            f"💾 Processed: ~{stats['seen']}"
        )
        await query.edit_message_text(msg, parse_mode="Markdown")

    elif callback_data == "admin_broadcast":
        await query.edit_message_text(
            "📝 *أرسل الرسالة اللي تبغى تنشرها:*", parse_mode="Markdown"
        )

    elif callback_data == "admin_help":
        help_msg = (
            "*🤖 Admin Commands:*\n\n"
            "📌 اضغط على الأزرار لـ:\n"
            "⚡ Fetch Now - شغّل الجلب\n"
            "📊 Stats - اعرض الحالة\n"
            "📢 Broadcast - أرسل إعلان\n\n"
            "أو اكتب: `fetch`, `stats`, `broadcast`"
        )
        await query.edit_message_text(help_msg, parse_mode="Markdown")

    # Lead buttons (external links are handled by Telegram)
    elif callback_data in ["lead_chatbots", "lead_automation", "lead_contact"]:
        await query.answer("✅ تم فتح الرابط")

    else:
        await query.answer("❌ أمر غير معروف")
