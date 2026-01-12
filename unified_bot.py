import asyncio
import os
import random
import logging
from datetime import datetime
from typing import Optional, Dict, Any

from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from dotenv import load_dotenv

# Config & Tools
from unified_config import ALL_FEEDS
from feed_manager import fetch_random_new_post
from ai_processor import rewrite_with_ai
from keep_alive import keep_alive  # For Render deployment

# Publishers
from blogger_publisher import BloggerPublisher
from devto_publisher import DevtoPublisher
from facebook_publisher import FacebookPublisher

# Logging Setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load Environment Variables
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
ADMIN_ID = os.getenv("ADMIN_USER_ID")


class SuperBot:
    """
    RoboVAI SuperBot v4.0 - The Spider Web Architecture
    Flow: RSS -> AI -> [Blogger/Dev.to] (Assets) -> [Facebook/Telegram] (Distribution)
    """

    def __init__(self):
        self.app = ApplicationBuilder().token(TOKEN).build()
        self.feeds = ALL_FEEDS

        # Initialize Publishers
        self.blogger = BloggerPublisher()
        self.devto = DevtoPublisher()
        self.facebook = FacebookPublisher()

        logger.info("🕷️ Spider Web Publishers Initialized")

    def run(self):
        """Start the bot polling"""
        print("🚀 Starting RoboVAI SuperBot (Spider Web v4.0)...")

        # Start Keep-Alive Server (For Render)
        try:
            keep_alive()
        except Exception as e:
            logger.warning(f"Keep-alive failed to start: {e}")

        # Add Handlers
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("force", self.force_post))

        # Schedule Posts (Every ~1 hour)
        job_queue = self.app.job_queue
        job_queue.run_repeating(self.scheduled_post, interval=3600, first=30)

        # Start Polling
        self.app.run_polling()

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "👋 أهلاً! أنا RoboVAI (نسخة شبكة العنكبوت v4.0).\n"
            "أقوم بإنشاء الأصول الرقمية (مقالات) ثم توزيعها على الشبكات الاجتماعية."
        )

    async def force_post(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manually trigger the publication cycle"""
        if str(update.effective_user.id) != str(ADMIN_ID):
            return

        status_msg = await update.message.reply_text(
            "⏳ جاري بدء دورة النشر (Spider Web Cycle)..."
        )

        try:
            result = await self._process_spider_web_cycle(context)
            if result:
                await status_msg.edit_text(
                    f"✅ تمت عملية النشر بنجاح!\n📝 المقال: {result}"
                )
            else:
                await status_msg.edit_text("❌ فشلت عملية النشر (راجع السجلات).")
        except Exception as e:
            logger.error(f"Force post error: {e}")
            await status_msg.edit_text(f"❌ حدث خطأ: {str(e)}")

    async def scheduled_post(self, context: ContextTypes.DEFAULT_TYPE):
        """Automated scheduled task"""
        logger.info("Checking for new content to spin the web...")
        await self._process_spider_web_cycle(context)

    async def _process_spider_web_cycle(
        self, context: ContextTypes.DEFAULT_TYPE
    ) -> Optional[str]:
        """
        The Core 'Spider Web' Logic:
        1. Fetch News (RSS)
        2. Generate Assets (AI -> Blogger/Dev.to)
        3. Distribute (Facebook/Telegram linking to Blogger/Dev.to)
        """
        print("🔍 Scanning feeds...")

        # 1. Fetch
        post = fetch_random_new_post(forced_feeds=self.feeds)
        if not post:
            print("💤 No new content found in any feed.")
            return None

        print(f"✅ Found news: {post['title']}")

        # 2. AI Processing (Generate ALL content at once)
        # We pass None for system_prompt so it uses the robust default one in ai_processor
        ai_content = rewrite_with_ai(
            title=post["title"],
            summary=post["summary"],
            link=post["link"],
            system_prompt=None,
            brand_name="RoboVAI",
            brand_language="ar",
        )

        if not ai_content:
            print("❌ AI Generation failed.")
            return None

        # Extract structured data
        # Fallbacks are handled if AI returns unstructured text (though specific prompt forbids it)
        if isinstance(ai_content, str):
            # If for some reason we got a string, try to parse or fail gracefully
            print("⚠️ AI returned string instead of JSON. Skipping complex flow.")
            return None

        title = ai_content.get("blog_title") or post["title"]
        # Make sure title is string
        if isinstance(title, list):
            title = title[0]

        content_md = ai_content.get("blog_content_md", "")
        telegram_post = ai_content.get("telegram_post", "")
        facebook_post = ai_content.get("facebook_post", "")

        generated_links = []
        primary_link = post["link"]  # Fallback to original source

        # ---------------------------------------------------------
        # Step 3: Create Assets (The Web)
        # ---------------------------------------------------------

        # A. Publish to Blogger
        print("📝 Publishing to Blogger...")
        try:
            blog_res = self.blogger.publish_post(
                title=title, caption=content_md, labels=["RoboVAI", "Tech", "News"]
            )
            if blog_res["success"]:
                blogger_url = blog_res["url"]
                generated_links.append(blogger_url)
                primary_link = blogger_url  # Priority 1
                print(f"✅ Blogger Published: {blogger_url}")
            else:
                print(f"⚠️ Blogger Failed: {blog_res.get('message')}")
        except Exception as e:
            print(f"⚠️ Blogger Exception: {e}")

        # B. Publish to Dev.to (Optional/Secondary)
        # Only if we have the key
        if self.devto.is_configured():
            print("📝 Publishing to Dev.to...")
            try:
                devto_res = self.devto.publish(
                    caption=content_md, title=title, image_url=post.get("image")
                )
                if devto_res["success"]:
                    devto_url = devto_res["url"]
                    generated_links.append(devto_url)
                    # primary_link = devto_url # Keep Blogger as primary for Arabic audience
                    print(f"✅ Dev.to Published: {devto_url}")
                else:
                    print(f"⚠️ Dev.to Failed: {devto_res.get('error')}")
            except Exception as e:
                print(f"⚠️ Dev.to Exception: {e}")

        # ---------------------------------------------------------
        # Step 4: Distribute (The Spiders)
        # ---------------------------------------------------------

        # C. Facebook (Hook + Link)
        print("📘 Publishing to Facebook...")
        try:
            # Facebook post = Hook + Link
            fb_message = facebook_post
            # The publish_link method takes the message and the link provided separately
            fb_res = self.facebook.publish_link(message=fb_message, link=primary_link)
            if fb_res["success"]:
                print("✅ Facebook Published")
            else:
                print(f"⚠️ Facebook Failed: {fb_res.get('message')}")
        except Exception as e:
            print(f"⚠️ Facebook Exception: {e}")

        # D. Telegram (Summary + Link)
        print("✈️ Publishing to Telegram...")
        try:
            # Construct message
            tg_msg = f"{telegram_post}\n\n🔗 *اقرأ التفاصيل*:\n{primary_link}"

            # Send (Image or Text)
            image_url = post.get("image") or post.get("image_local_path")

            if image_url:
                await context.bot.send_photo(
                    chat_id=CHANNEL_ID, photo=image_url, caption=tg_msg
                )
            else:
                await context.bot.send_message(chat_id=CHANNEL_ID, text=tg_msg)
            print("✅ Telegram Published")
        except Exception as e:
            print(f"⚠️ Telegram Exception: {e}")

        return primary_link


if __name__ == "__main__":
    bot = SuperBot()
    bot.run()
