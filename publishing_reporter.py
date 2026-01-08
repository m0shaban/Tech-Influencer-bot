"""
Publishing Report Manager
Send real-time reports to admin about publishing activities
"""

import os
from datetime import datetime
from typing import Any, Dict, Optional
from telegram import Bot
from dotenv import load_dotenv

load_dotenv()


class PublishingReporter:
    """Send publishing reports to admin via Telegram"""

    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_TOKEN")
        self.admin_user_id = int(os.getenv("ADMIN_USER_ID", "0") or "0")
        self.bot = None

        if self.bot_token and self.admin_user_id:
            try:
                self.bot = Bot(token=self.bot_token)
            except Exception as e:
                print(f"Failed to initialize reporter bot: {e}")

    async def send_report(self, message: str) -> bool:
        """Send a report message to admin"""
        if not self.bot or not self.admin_user_id:
            print(f"[Report] {message}")
            return False

        try:
            await self.bot.send_message(
                chat_id=self.admin_user_id,
                text=message,
                parse_mode="Markdown",
            )
            return True
        except Exception as e:
            print(f"Failed to send report: {e}")
            return False

    async def report_post_start(
        self,
        total_platforms: int,
        caption_preview: str,
    ) -> None:
        """Report when publishing starts"""
        preview = (
            caption_preview[:100] + "..."
            if len(caption_preview) > 100
            else caption_preview
        )

        message = (
            f"🚀 **بدء النشر**\n\n"
            f"📊 **عدد المنصات:** {total_platforms}\n"
            f"⏰ **الوقت:** {datetime.now().strftime('%H:%M:%S')}\n\n"
            f"📝 **المحتوى:**\n{preview}"
        )

        await self.send_report(message)

    async def report_platform_success(
        self,
        platform: str,
        post_url: Optional[str] = None,
    ) -> None:
        """Report successful publishing to a platform"""
        message = f"✅ **{platform.upper()}**\n"

        if post_url:
            message += f"🔗 [عرض المنشور]({post_url})\n"

        message += f"⏰ {datetime.now().strftime('%H:%M:%S')}"

        await self.send_report(message)

    async def report_platform_failure(
        self,
        platform: str,
        error: str,
    ) -> None:
        """Report failed publishing to a platform"""
        message = (
            f"❌ **{platform.upper()} - فشل**\n\n"
            f"⚠️ **الخطأ:**\n`{error[:200]}`\n\n"
            f"⏰ {datetime.now().strftime('%H:%M:%S')}"
        )

        await self.send_report(message)

    async def report_post_complete(
        self,
        successful: int,
        failed: int,
        total: int,
        duration_seconds: float,
    ) -> None:
        """Report when all publishing is complete"""
        success_rate = (successful / total * 100) if total > 0 else 0

        status_emoji = "✅" if failed == 0 else "⚠️"

        message = (
            f"{status_emoji} **اكتمل النشر**\n\n"
            f"📊 **النتائج:**\n"
            f"✅ نجح: {successful}\n"
            f"❌ فشل: {failed}\n"
            f"📈 نسبة النجاح: {success_rate:.0f}%\n\n"
            f"⏱️ **المدة:** {duration_seconds:.1f} ثانية\n"
            f"🕐 **انتهى:** {datetime.now().strftime('%H:%M:%S')}"
        )

        await self.send_report(message)

    async def report_scheduled_post(
        self,
        platform: str,
        scheduled_time: datetime,
    ) -> None:
        """Report a scheduled post"""
        time_str = scheduled_time.strftime("%H:%M:%S")
        delay = (scheduled_time - datetime.now()).total_seconds() / 60

        message = (
            f"📅 **منشور مجدول**\n\n"
            f"📱 **المنصة:** {platform.upper()}\n"
            f"⏰ **موعد النشر:** {time_str}\n"
            f"⏳ **بعد:** {delay:.0f} دقيقة"
        )

        await self.send_report(message)

    async def report_schedule_summary(
        self,
        platforms_count: Dict[str, int],
    ) -> None:
        """Report summary of scheduled posts"""
        total = sum(platforms_count.values())

        message = f"📅 **ملخص الجدولة**\n\n📊 **إجمالي المنشورات:** {total}\n\n"

        for platform, count in sorted(platforms_count.items()):
            message += f"• {platform.upper()}: {count}\n"

        await self.send_report(message)

    async def report_error(self, error_message: str) -> None:
        """Report a general error"""
        message = f"🚨 **خطأ في النظام**\n\n`{error_message[:300]}`"
        await self.send_report(message)


# Global instance
_reporter = None


def get_reporter() -> PublishingReporter:
    """Get global reporter instance"""
    global _reporter
    if _reporter is None:
        _reporter = PublishingReporter()
    return _reporter
