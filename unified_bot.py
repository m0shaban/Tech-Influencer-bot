import asyncio
import os
import random
import logging
from datetime import datetime
from typing import Optional

from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from dotenv import load_dotenv

# استيراد الأدوات الموجودة
from unified_config import ALL_FEEDS, SYSTEM_PROMPT
from feed_manager import parse_feed, is_post_seen, mark_post_seen
from ai_processor import rewrite_with_ai
from image_manager import get_best_image
# (اختياري) النشر على منصات أخرى
try:
    from sequential_publisher import SequentialPublisher
except ImportError:
    SequentialPublisher = None

# إعداد اللوج
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# تحميل المتغيرات
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")  # التوكن الأساسي
CHANNEL_ID = os.getenv("CHANNEL_ID") # القناة الأساسية
ADMIN_ID = os.getenv("ADMIN_USER_ID")

class SuperBot:
    def __init__(self):
        self.app = ApplicationBuilder().token(TOKEN).build()
        self.feeds = ALL_FEEDS
        self.publisher = SequentialPublisher() if SequentialPublisher else None
        
    def run(self):
        """تشغيل البوت"""
        print("🚀 Starting SuperBot (Single Mode)...")
        
        # إضافة الأوامر
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("force", self.force_post))
        
        # إعداد الـ JobQueue للنشر التلقائي
        job_queue = self.app.job_queue
        # كل 3600 ثانية (ساعة) يقوم بمحاولة نشر
        job_queue.run_repeating(self.scheduled_post, interval=3600, first=10)
        
        # بدء التشغيل
        self.app.run_polling()

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("👋 أهلاً! أنا RoboVAI النسخة الموحدة.\nأعمل حالياً على جلب الأخبار من كل المصادر.")

    async def force_post(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if str(update.effective_user.id) != str(ADMIN_ID):
            return
        await update.message.reply_text("⏳ جاري البحث عن خبر جديد...")
        await self._process_one_post(context)

    async def scheduled_post(self, context: ContextTypes.DEFAULT_TYPE):
        """وظيفة مجدولة تعمل تلقائياً"""
        logger.info("Checking for new posts...")
        await self._process_one_post(context)

    async def _process_one_post(self, context: ContextTypes.DEFAULT_TYPE):
        """المنطق الرئيسي: جلب - تحليل - نشر"""
        # 1. اختيار مصدر عشوائي لضمان التنوع
        random.shuffle(self.feeds)
        selected_feed = None
        target_entry = None
        
        print("🔍 Scanning feeds...")
        for feed_url in self.feeds:
            entries = parse_feed(feed_url)
            for entry in entries:
                if not is_post_seen(entry['link']):
                    selected_feed = feed_url
                    target_entry = entry
                    break
            if target_entry:
                break
        
        if not target_entry:
            print("💤 No new content found in any feed.")
            return

        print(f"✅ Found news: {target_entry['title']}")
        
        # 2. المعالجة بالذكاء الاصطناعي
        ai_content = rewrite_with_ai(
            title=target_entry['title'],
            summary=target_entry['summary'],
            link=target_entry['link'],
            system_prompt=SYSTEM_PROMPT, # استخدام البرومبت العربي الموحد
            brand_name="RoboVAI"
        )
        
        if not ai_content:
            print("❌ AI Generation failed.")
            return

        # 3. تجهيز الصورة
        image_url = get_best_image(target_entry)
        
        # 4. النشر على تيليجرام
        caption = ai_content.get("telegram_post", "")
        # تنظيف النص وتنسيقه
        final_msg = f"{caption}\n\n🔗 {target_entry['link']}"

        try:
            if image_url:
                await context.bot.send_photo(chat_id=CHANNEL_ID, photo=image_url, caption=final_msg)
            else:
                await context.bot.send_message(chat_id=CHANNEL_ID, text=final_msg)
            
            # تسجيل أن الخبر تم نشره
            mark_post_seen(target_entry['link'])
            print("✅ Posted to Telegram successfully.")

            # 5. النشر على المنصات الأخرى (إذا وجدت)
            if self.publisher:
                # محاكاة كائن النتيجة للنشر المتسلسل
                result_obj = {
                    "content_data": ai_content,
                    "title": target_entry['title'],
                    "link": target_entry['link'],
                    "feed_item": target_entry
                }
                # تشغيل النشر الخارجي في الخلفية (Fire and Forget)
                asyncio.create_task(self.publisher.publish_all(None, result_obj))
                
        except Exception as e:
            print(f"❌ Error during publishing: {e}")

if __name__ == "__main__":
    bot = SuperBot()
    bot.run()
