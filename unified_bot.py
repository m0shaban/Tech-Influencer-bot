import asyncio
import os
import random
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
)
from dotenv import load_dotenv

# Config & Tools
from unified_config import ALL_FEEDS
from feed_manager import fetch_random_new_post
from ai_processor import rewrite_with_ai
from keep_alive import keep_alive  # For Render deployment

# Publishers (Enterprise Editions)
from blogger_publisher import BloggerPublisher
from devto_publisher import DevtoPublisher
from facebook_publisher import FacebookPublisher

# Logging Setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger("UnifiedBot")

# Load Environment Variables
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
ADMIN_ID = os.getenv("ADMIN_USER_ID")

class SuperBot:
    """
    RoboVAI SuperBot v5.0 (Enterprise Core)
    The Maestro that orchestrates the entire 'Spider Web' content lifecycle.
    """

    def __init__(self):
        self.app = ApplicationBuilder().token(TOKEN).build()
        self.feeds = ALL_FEEDS

        # Initialize Enterprise Publishers
        self.blogger = BloggerPublisher()
        self.devto = DevtoPublisher()
        self.facebook = FacebookPublisher()

        logger.info("🕷️ Spider Web System v5.0 Initialized")

    def run(self):
        """Start the bot polling"""
        print("🚀 Starting RoboVAI Enterprise Bot...")

        # Start Keep-Alive Server (For Render)
        try:
            keep_alive()
        except Exception as e:
            logger.warning(f"Keep-alive failed to start: {e}")

        # Add Handlers
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("force", self.force_post))
        self.app.add_handler(CallbackQueryHandler(self.button_handler))

        # Schedule Posts (Every 60 minutes)
        job_queue = self.app.job_queue
        if job_queue:
            job_queue.run_repeating(self.scheduled_post, interval=3600, first=30)
            logger.info("⏰ Job Queue scheduled.")

        # Start Polling
        self.app.run_polling()

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)

        # Check if Admin matching .env ID
        is_admin = (user_id == str(ADMIN_ID))

        if is_admin:
            keyboard = [
                [
                    InlineKeyboardButton("🚀 نشر يدوي (Force)", callback_data="force_publish"),
                    InlineKeyboardButton("🏥 فحص النظام", callback_data="check_health"),
                ],
                [
                    InlineKeyboardButton("📊 إحصائيات", callback_data="stats"),
                ],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                f"👑 **لوحة تحكم الأدمن (Enterprise v5.0)**\n\n"
                f"🕷️ **النظام:** RoboVAI Core\n"
                f"📡 **المصادر:** {len(self.feeds)} مصدر نشط\n"
                f"✅ **الحالة:** متصل\n"
                f"📅 **Server Time:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                reply_markup=reply_markup,
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text(
                "👋 أهلاً! أنا RoboVAI.\n"
                "روبوت ذكي يقوم بصناعة وتوزيع المحتوى التقني.\n"
                "تابع قناتنا لمعرفة المزيد."
            )

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle dashboard button clicks"""
        query = update.callback_query
        if not query:
            return
        await query.answer()

        if query.data == "force_publish":
            await query.edit_message_text("⏳ جاري بدء دورة النشر اليدوية (Deep Thinking Mode)...")
            try:
                result = await self._process_spider_web_cycle(context)
                if result:
                    await context.bot.send_message(
                        chat_id=query.from_user.id,
                        text=f"✅ تمت عملية النشر بنجاح!\n🔗 {result}",
                    )
                    # Show menu again
                    await context.bot.send_message(
                        chat_id=query.from_user.id,
                        text="🔙 اضغط /start للعودة للقائمة الرئيسية",
                    )
                else:
                    await context.bot.send_message(
                        chat_id=query.from_user.id,
                        text="❌ لم يتم العثور على محتوى مناسب أو فشل التوليد.",
                    )
            except Exception as e:
                logger.exception("Force Publish Error")
                await context.bot.send_message(
                    chat_id=query.from_user.id, text=f"❌ خطأ فادح: {e}"
                )

        elif query.data == "check_health":
            status_text = "🏥 **تقرير الحالة الشامل**:\n\n"

            # Check Blogger
            b_res = self.blogger.test_connection()
            status_text += f"📝 **Blogger:** {'✅ OK' if b_res['success'] else '❌ Fail'}\n"

            # Check Facebook
            try:
                self.facebook._validate_connection()
                fb_status = "✅ OK"
            except:
                fb_status = "❌ Fail"
            status_text += f"📘 **Facebook:** {fb_status}\n"

            # Check Dev.to
            dev_res = self.devto.verify_credentials()
            status_text += f"💻 **Dev.to:** {'✅ OK' if dev_res['success'] else '⚠️ Disabled/Error'}\n"

            await context.bot.send_message(
                chat_id=query.from_user.id, text=status_text, parse_mode="Markdown"
            )

        elif query.data == "stats":
            await context.bot.send_message(
                chat_id=query.from_user.id, text="📊 جاري سحب الإحصائيات من فيسبوك..."
            )
            # Future: Call facebook.get_post_metrics here
            await context.bot.send_message(
                chat_id=query.from_user.id, text="ℹ️ هذه الميزة قادمة في التحديث القادم."
            )

    async def force_post(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manually trigger via command"""
        if str(update.effective_user.id) != str(ADMIN_ID):
            return

        status_msg = await update.message.reply_text("⏳ جاري التشغيل...")
        try:
            result = await self._process_spider_web_cycle(context)
            if result:
                await status_msg.edit_text(f"✅ تم النشر: {result}")
            else:
                await status_msg.edit_text("❌ لم يتم النشر.")
        except Exception as e:
            await status_msg.edit_text(f"❌ خطأ: {e}")

    async def scheduled_post(self, context: ContextTypes.DEFAULT_TYPE):
        """Automated scheduled task"""
        logger.info("⏰ Triggering scheduled spider cycle...")
        try:
            await self._process_spider_web_cycle(context)
        except Exception as e:
            logger.error(f"Scheduled task failed: {e}")

    async def _process_spider_web_cycle(
        self, context: ContextTypes.DEFAULT_TYPE
    ) -> Optional[str]:
        """
        The Enterprise 'Spider Web' Logic.
        Flow: RSS -> AI V3 -> Blogger V2 -> (Dev.to V2 + Facebook V2 + Telegram)
        """
        print("🔍 Scanning global feeds...")

        # ---------------------------------------------------------
        # 1. Fetch High-Quality Content
        # ---------------------------------------------------------
        post = fetch_random_new_post(forced_feeds=self.feeds)
        if not post:
            logger.info("💤 No new content found in feeds.")
            return None

        logger.info(f"✅ Selected Article: {post['title']}")

        # ---------------------------------------------------------
        # 2. AI Brain Processing (Chain-of-Thought)
        # ---------------------------------------------------------
        ai_content = rewrite_with_ai(
            title=post["title"],
            summary=post["summary"],
            link=post["link"],
            brand_name="RoboVAI"
        )

        if not ai_content or not isinstance(ai_content, dict):
            logger.warning("❌ AI Brain failed to produce valid JSON structure.")
            return None

        # Extract Fields Safely
        blog_title = ai_content.get("blog_title", post["title"])
        content_md = ai_content.get("blog_content_md", "")
        meta_desc = ai_content.get("blog_meta_description", "")
        keywords = ai_content.get("keywords", [])
        fb_msg = ai_content.get("facebook_post", "")
        tg_msg = ai_content.get("telegram_post", "")

        primary_link = post["link"] # Default if publishing fails
        
        # ---------------------------------------------------------
        # 3. Create Assets (The Web)
        # ---------------------------------------------------------
        
        # A. Publish to Blogger (The Hub)
        logger.info("📝 Publishing to Blogger...")
        blogger_link = None
        try:
            res = self.blogger.publish_post(
                title=blog_title,
                content_markdown=content_md,
                labels=keywords,
                image_url=post.get("image"),
                search_description=meta_desc
            )
            
            if res["success"]:
                blogger_link = res["url"]
                primary_link = blogger_link # Override primary link
                logger.info(f"✅ Blogger Success: {blogger_link}")
            else:
                logger.error(f"Blogger Error: {res.get('message')}")
        except Exception as e:
            logger.error(f"Blogger Exception: {e}")

        # B. Publish to Dev.to (SEO Booster)
        # We set canonical_url to the Blogger link to credit it as the original source
        if self.devto.is_configured():
            logger.info("📝 Publishing to Dev.to...")
            try:
                self.devto.publish_article(
                    title=blog_title,
                    body_markdown=content_md,
                    tags=keywords,
                    cover_image_url=post.get("image"),
                    canonical_url=blogger_link # Crucial for SEO
                )
            except Exception as e:
                logger.error(f"Dev.to Exception: {e}")

        # ---------------------------------------------------------
        # 4. Distribute (The Spiders)
        # ---------------------------------------------------------

        # C. Facebook (Strategy: Link Post)
        logger.info("📘 Distributing to Facebook...")
        try:
            # We prefer using the Blogger link. If failed, use original source.
            target_link = blogger_link if blogger_link else post["link"]
            
            self.facebook.publish_link_post(
                message=fb_msg,
                link=target_link
            )
            # Alternative: Publish Photo then Comment Link?
            # For now, Link Post is safest for click-through rate in News Feed.
            
        except Exception as e:
            logger.error(f"Facebook Exception: {e}")

        # D. Telegram (Direct Notification)
        logger.info("✈️ Distributing to Telegram...")
        try:
            if not CHANNEL_ID:
                logger.warning("Telegram CHANNEL_ID not set.")
            else:
                # Format: Hook + Link
                final_tg_msg = f"{tg_msg}\n\n🤖 *اقرأ المقال كاملاً*:\n{primary_link}"
                
                # Try sending with image
                img = post.get("image")
                if img:
                    try:
                        await context.bot.send_photo(
                            chat_id=CHANNEL_ID, 
                            photo=img, 
                            caption=final_tg_msg[:1000] # Cap length for captions
                        )
                    except:
                        # Fallback to text if image fails
                        await context.bot.send_message(chat_id=CHANNEL_ID, text=final_tg_msg)
                else:
                    await context.bot.send_message(chat_id=CHANNEL_ID, text=final_tg_msg)
                    
        except Exception as e:
            logger.error(f"Telegram Exception: {e}")

        return primary_link

if __name__ == "__main__":
    bot = SuperBot()
    bot.run()
