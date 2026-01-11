"""
Master Controller - Admin Bot Dashboard
========================================

This is the SUPERVISOR bot in the Hub-and-Spoke architecture.

Responsibilities:
- System monitoring and health checks
- Command dispatch to worker bots
- Analytics dashboard
- Admin UI/UX

THIS BOT NEVER POSTS CONTENT.
It is strictly for management and control.
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from brands_config import (
    MASTER_BOT_TOKEN,
    ADMIN_USER_ID,
    get_brand_configs,
    get_brand_by_key,
    PublishingMode,
)

from bot_registry import BotRegistry


BASE_DIR = Path(__file__).resolve().parent
LOG_PATH = BASE_DIR / "bot.log"
DATA_DIR = BASE_DIR / "data"


def _is_admin(update: Update) -> bool:
    """Check if user is admin."""
    return bool(update.effective_user and update.effective_user.id == ADMIN_USER_ID)


def _log(message: str) -> None:
    """Safe logging."""
    try:
        print(f"[MASTER] {message}")
    except UnicodeEncodeError:
        safe_msg = message.encode("ascii", "replace").decode("ascii")
        print(f"[MASTER] {safe_msg}")


# ============================================================
# DASHBOARD UI
# ============================================================


def get_main_dashboard_keyboard() -> InlineKeyboardMarkup:
    """Main dashboard with brand selection."""
    brands = get_brand_configs()

    buttons = []

    # Brand buttons
    for key, brand in brands.items():
        emoji = "🟢" if True else "🔴"  # TODO: Check actual status
        buttons.append(
            [
                InlineKeyboardButton(
                    f"{emoji} {brand.display_name}", callback_data=f"brand:{key}"
                )
            ]
        )

    # System buttons
    buttons.append(
        [
            InlineKeyboardButton("📊 System Stats", callback_data="stats:system"),
            InlineKeyboardButton("📋 Logs", callback_data="logs:view"),
        ]
    )
    buttons.append(
        [
            InlineKeyboardButton("🔄 Refresh", callback_data="refresh"),
        ]
    )

    return InlineKeyboardMarkup(buttons)


def get_brand_control_keyboard(brand_key: str) -> InlineKeyboardMarkup:
    """Control panel for a specific brand."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "⚡ Force Post", callback_data=f"force:{brand_key}"
                ),
                InlineKeyboardButton("📊 Stats", callback_data=f"stats:{brand_key}"),
            ],
            [
                InlineKeyboardButton("🧪 Test", callback_data=f"test:{brand_key}"),
                InlineKeyboardButton("📡 Feeds", callback_data=f"feeds:{brand_key}"),
            ],
            [
                InlineKeyboardButton("⏸️ Pause", callback_data=f"pause:{brand_key}"),
                InlineKeyboardButton("▶️ Resume", callback_data=f"resume:{brand_key}"),
            ],
            [
                InlineKeyboardButton("« Back to Dashboard", callback_data="dashboard"),
            ],
        ]
    )


# ============================================================
# COMMAND HANDLERS
# ============================================================



WELCOME_LEAD = """🌟 **مرحباً بك في RoboVAI Ecosystem**

نصمم حلولاً ذكية تعمل بالذكاء الاصطناعي 🤖

━━━━━━━━━━━━━━━━━━━

✨ **خدماتنا:**
   🔹 شات بوتات ذكية 24/7
   🔹 أتمتة العمليات التجارية
   🔹 تحليل البيانات الذكي
   🔹 محتوى تقني احترافي

اختر من الخيارات أدناه للبدء 👇"""


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


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Main entry point - show dashboard or lead welcome."""
    if not update.message:
        return

    if not _is_admin(update):
        # Public Facing Logic (Lead Gen)
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
        return

    # Admin Logic
    brands = get_brand_configs()

    dashboard_text = f"""🎛️ **RoboVAI Master Controller**
═══════════════════════════════

👑 Welcome, Admin!

📊 **System Status**
━━━━━━━━━━━━━━━━
• Brands Online: {len(brands)}
• Architecture: Hub-and-Spoke
• Mode: Supervisor

🔧 **Active Brands:**
"""

    for key, brand in brands.items():
        mode_icon = {
            PublishingMode.NATIVE: "🎯",
            PublishingMode.FUNNEL: "🔀",
            PublishingMode.DUAL: "⚡",
        }.get(brand.mode, "📝")
        dashboard_text += f"\n{mode_icon} **{brand.display_name}** ({brand.key})"
        dashboard_text += (
            f"\n   └ Mode: {brand.mode.value} | Channel: {brand.channel_id}"
        )

    dashboard_text += "\n\n👇 Select a brand to control:"

    await update.message.reply_text(
        dashboard_text,
        reply_markup=get_main_dashboard_keyboard(),
        parse_mode="Markdown",
    )


async def cmd_brands(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List all brands with status."""
    if not update.message or not _is_admin(update):
        return

    brands = get_brand_configs()

    text = "📋 **Brand Overview**\n═══════════════════\n\n"

    for key, brand in brands.items():
        text += f"**{brand.display_name}**\n"
        text += f"• Token: `...{brand.token[-8:]}`\n"
        text += f"• Channel: `{brand.channel_id}`\n"
        text += f"• Mode: {brand.mode.value}\n"
        text += f"• Platforms: {', '.join(brand.platforms.keys())}\n\n"

    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_force(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Force post for a specific brand."""
    if not update.message or not _is_admin(update):
        return

    args = context.args
    if not args:
        await update.message.reply_text(
            "Usage: /force <BRAND>\n" "Example: /force BS\n\n" "Available: ARB, BS, ZDS"
        )
        return

    brand_key = args[0].upper()
    brand = get_brand_by_key(brand_key)

    if not brand:
        await update.message.reply_text(f"❌ Unknown brand: {brand_key}")
        return

    await update.message.reply_text(
        f"⚡ Dispatching Force Fetch to **{brand.display_name}**...\n\n"
        f"💡 Tip: Open @{brand_key.lower()}_bot for real-time updates.",
        parse_mode="Markdown",
    )

    # The actual publishing is handled by the worker bot
    # Master just sends the command notification


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show system status."""
    if not update.message or not _is_admin(update):
        return

    brands = get_brand_configs()

    text = """📊 **System Status**
═══════════════════

🏗️ **Architecture:** Hub-and-Spoke
🤖 **Master:** Online
📡 **Workers:** {workers}

**Worker Details:**
""".format(
        workers=len(brands)
    )

    for key, brand in brands.items():
        text += f"\n🔹 {brand.display_name} ({key})"
        text += f"\n   Mode: {brand.mode.value.upper()}"
        text += f"\n   Feeds: {len(brand.feeds)}"

    await update.message.reply_text(text, parse_mode="Markdown")


# ============================================================
# CALLBACK QUERY HANDLERS
# ============================================================


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline button callbacks."""
    query = update.callback_query
    if not query:
        return

    await query.answer()

    data = query.data or ""

    if data == "dashboard":
        await show_dashboard(query)
    elif data == "refresh":
        await show_dashboard(query)
    elif data.startswith("brand:"):
        brand_key = data.split(":")[1]
        await show_brand_panel(query, brand_key)
    elif data.startswith("force:"):
        brand_key = data.split(":")[1]
        await handle_force_dispatch(query, brand_key)
    elif data.startswith("stats:"):
        target = data.split(":")[1]
        if target == "system":
            await show_system_stats(query)
        else:
            await show_brand_stats(query, target)
    elif data == "logs:view":
        await show_recent_logs(query)


async def show_dashboard(query) -> None:
    """Show main dashboard."""
    brands = get_brand_configs()

    text = f"""🎛️ **Master Controller Dashboard**
═══════════════════════════════

📡 **Workers Online:** {len(brands)}

Select a brand to manage:"""

    await query.edit_message_text(
        text,
        reply_markup=get_main_dashboard_keyboard(),
        parse_mode="Markdown",
    )


async def show_brand_panel(query, brand_key: str) -> None:
    """Show control panel for a brand."""
    brand = get_brand_by_key(brand_key)
    if not brand:
        await query.edit_message_text(f"❌ Brand not found: {brand_key}")
        return

    platforms_str = ", ".join(
        [
            f"{p}({'✓' if cfg.get('enabled') else '✗'})"
            for p, cfg in brand.platforms.items()
        ]
    )

    text = f"""🎯 **{brand.display_name}**
═══════════════════════

📋 **Configuration:**
• Key: `{brand.key}`
• Mode: {brand.mode.value.upper()}
• Language: {brand.language}
• Channel: `{brand.channel_id}`

📱 **Platforms:** {platforms_str}

⏰ **Schedule:**
• Active: {brand.schedule.get('wake_hour', 9)}:00 - {brand.schedule.get('sleep_hour', 22)}:00
• Max posts: {brand.schedule.get('posts_per_day', 8)}/day

📚 **Feeds:** {len(brand.feeds)} sources

Select an action:"""

    await query.edit_message_text(
        text,
        reply_markup=get_brand_control_keyboard(brand_key),
        parse_mode="Markdown",
    )


async def handle_force_dispatch(query, brand_key: str) -> None:
    """Dispatch force fetch command to worker."""
    brand = get_brand_by_key(brand_key)
    if not brand:
        await query.edit_message_text(f"❌ Brand not found: {brand_key}")
        return

    # Get running worker instance
    worker = BotRegistry.get_worker(brand_key)
    if not worker:
        await query.edit_message_text(f"⚠️ Worker for {brand.display_name} is not running!")
        return

    # Trigger fetch task
    # We use create_task to not block the UI
    try:
        # Assuming worker has a method that doesn't require Update/Context objects
        # Or we call the internal method used by scheduler
        asyncio.create_task(worker._fetch_and_generate_native_content(None))
        status_msg = "✅ Command sent to worker"
    except Exception as e:
        status_msg = f"❌ Error dispatching: {e}"

    text = f"""⚡ **Force Fetch Dispatched**
═══════════════════════════

🎯 Brand: {brand.display_name}
📺 Channel: {brand.channel_id}
🔄 Status: {status_msg}

💡 The worker bot is now fetching content.
Check the brand's bot for real-time updates.

⏱️ Dispatched at: {datetime.now().strftime('%H:%M:%S')}"""

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("« Back", callback_data=f"brand:{brand_key}")]]
        ),
        parse_mode="Markdown",
    )


async def show_system_stats(query) -> None:
    """Show system-wide statistics."""
    brands = get_brand_configs()

    total_feeds = sum(len(b.feeds) for b in brands.values())
    total_platforms = sum(len(b.platforms) for b in brands.values())

    text = f"""📊 **System Statistics**
═══════════════════════

🏗️ **Architecture**
• Type: Hub-and-Spoke
• Master: Online
• Workers: {len(brands)}

📚 **Content**
• Total RSS Feeds: {total_feeds}
• Total Platforms: {total_platforms}

🎯 **Brands by Mode:**
"""

    mode_counts = {}
    for brand in brands.values():
        mode = brand.mode.value
        mode_counts[mode] = mode_counts.get(mode, 0) + 1

    for mode, count in mode_counts.items():
        text += f"• {mode.upper()}: {count}\n"

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("« Back", callback_data="dashboard")]]
        ),
        parse_mode="Markdown",
    )


async def show_brand_stats(query, brand_key: str) -> None:
    """Show statistics for a specific brand."""
    brand = get_brand_by_key(brand_key)
    if not brand:
        await query.edit_message_text(f"❌ Brand not found: {brand_key}")
        return

    # Get runtime stats from worker
    worker = BotRegistry.get_worker(brand_key)
    posts_today = getattr(worker, "posts_today", 0) if worker else 0
    last_post = getattr(worker, "last_post_time", None) if worker else None
    
    last_post_str = last_post.strftime("%H:%M") if last_post else "Never"
    status_icon = "🟢 Online" if worker and getattr(worker, "is_running", False) else "🔴 Offline"

    text = f"""📊 **{brand.display_name} Stats**
═══════════════════════════

🔌 **Status:** {status_icon}
📈 **Posts Today:** {posts_today}
🕒 **Last Post:** {last_post_str}

📚 **Feeds:** {len(brand.feeds)}
📱 **Platforms:** {len(brand.platforms)}
🌐 **Mode:** {brand.mode.value.upper()}

⏰ **Schedule:**
• Timezone: {brand.schedule.get('timezone', 'UTC')}
• Active hours: {brand.schedule.get('wake_hour', 9)}-{brand.schedule.get('sleep_hour', 22)}
• Max posts: {brand.schedule.get('posts_per_day', 8)}/day

📡 **Platform Status:**"""

    for platform, cfg in brand.platforms.items():
        status = "✅" if cfg.get("enabled") else "❌"
        text += f"\n• {platform}: {status}"

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("« Back", callback_data=f"brand:{brand_key}")]]
        ),
        parse_mode="Markdown",
    )


async def show_recent_logs(query) -> None:
    """Show recent log entries."""
    try:
        if LOG_PATH.exists():
            content = LOG_PATH.read_text(encoding="utf-8", errors="ignore")
            lines = content.strip().split("\n")[-15:]  # Last 15 lines
            log_text = "\n".join(lines)
        else:
            log_text = "No logs available"
    except Exception as e:
        log_text = f"Error reading logs: {e}"

    text = f"""📋 **Recent Logs**
═══════════════════

```
{log_text[:2000]}
```"""

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("🔄 Refresh", callback_data="logs:view"),
                    InlineKeyboardButton("« Back", callback_data="dashboard"),
                ]
            ]
        ),
        parse_mode="Markdown",
    )


# ============================================================
# APPLICATION BUILDER
# ============================================================


def build_master_application() -> Application:
    """Build the master controller application."""
    if not MASTER_BOT_TOKEN:
        raise RuntimeError("MASTER_BOT_TOKEN (TELEGRAM_TOKEN) not configured")

    app = ApplicationBuilder().token(MASTER_BOT_TOKEN).build()

    # Command handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("brands", cmd_brands))
    app.add_handler(CommandHandler("force", cmd_force))
    app.add_handler(CommandHandler("status", cmd_status))

    # Generic Message Handler (for non-admin Chat/leads)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Callback handler for inline buttons
    app.add_handler(CallbackQueryHandler(handle_callback))

    return app


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages (Leads for non-admins)."""
    if not update.message:
        return

    if _is_admin(update):
        # Admins can chat freely or used for debugging
        return

    # Reply with Sales Copy for leads
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


async def run_master_controller() -> None:
    """Run the master controller bot."""
    _log("Starting Master Controller...")

    app = build_master_application()

    _log("Master Controller online. Waiting for commands...")
    # Use the blocking run_polling call
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    asyncio.run(run_master_controller())
