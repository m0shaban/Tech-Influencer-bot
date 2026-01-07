"""
Multi-Platform Publisher
Unified interface for publishing to multiple platforms
"""
from typing import Any, Dict, Optional, Literal
import os
from dotenv import load_dotenv

load_dotenv()

PlatformType = Literal["telegram", "linkedin"]


class MultiPlatformPublisher:
    """Publish content to multiple platforms from a single interface"""
    
    def __init__(self):
        self.enabled_platforms = self._get_enabled_platforms()
    
    def _get_enabled_platforms(self) -> list[PlatformType]:
        """Detect which platforms are configured"""
        platforms: list[PlatformType] = []
        
        # Telegram is always enabled (base platform)
        if os.getenv("TELEGRAM_TOKEN"):
            platforms.append("telegram")
        
        # LinkedIn is optional
        if os.getenv("LINKEDIN_ACCESS_TOKEN"):
            platforms.append("linkedin")
        
        return platforms
    
    async def publish(
        self,
        caption: str,
        link: Optional[str] = None,
        image_url: Optional[str] = None,
        platforms: Optional[list[PlatformType]] = None,
        telegram_context: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Publish content to multiple platforms
        
        Args:
            caption: Post text content
            link: Optional source URL
            image_url: Optional image URL
            platforms: List of platforms to publish to (None = all enabled)
            telegram_context: Telegram bot context (required for Telegram)
        
        Returns:
            Dict with results per platform
        """
        target_platforms = platforms or self.enabled_platforms
        results = {}
        
        for platform in target_platforms:
            try:
                if platform == "telegram":
                    result = await self._publish_telegram(
                        caption, link, image_url, telegram_context
                    )
                    results["telegram"] = result
                
                elif platform == "linkedin":
                    result = self._publish_linkedin(caption, link, image_url)
                    results["linkedin"] = result
                
            except Exception as e:
                results[platform] = {
                    "status": "error",
                    "error": str(e)
                }
        
        return results
    
    async def _publish_telegram(
        self,
        caption: str,
        link: Optional[str],
        image_url: Optional[str],
        context: Any
    ) -> Dict[str, Any]:
        """Publish to Telegram (existing logic)"""
        from main import CHANNEL_ID
        
        def _compose_text(c: str, l: Optional[str], has_photo: bool) -> str:
            base = (
                c
                if (l and l in c)
                else (c + (f"\n\n🔗 لينك الخبر/الأداة: {l}" if l else ""))
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
        
        if image_url:
            try:
                await context.bot.send_photo(
                    chat_id=CHANNEL_ID, 
                    photo=image_url, 
                    caption=text
                )
            except Exception:
                await context.bot.send_message(chat_id=CHANNEL_ID, text=text)
        else:
            await context.bot.send_message(chat_id=CHANNEL_ID, text=text)
        
        return {"status": "success", "platform": "telegram"}
    
    def _publish_linkedin(
        self,
        caption: str,
        link: Optional[str],
        image_url: Optional[str]
    ) -> Dict[str, Any]:
        """Publish to LinkedIn"""
        from linkedin_publisher import LinkedInPublisher
        
        publisher = LinkedInPublisher()
        
        # Choose best LinkedIn format based on content
        if image_url:
            # Post with image
            return publisher.publish_image_post(caption, image_url, link)
        elif link:
            # Article share with preview
            return publisher.publish_article(caption, link)
        else:
            # Text-only post
            return publisher.publish_text_post(caption, link)
    
    def get_platform_status(self) -> Dict[str, bool]:
        """Check which platforms are configured and ready"""
        status = {}
        
        # Telegram
        status["telegram"] = bool(os.getenv("TELEGRAM_TOKEN"))
        
        # LinkedIn
        if os.getenv("LINKEDIN_ACCESS_TOKEN"):
            try:
                from linkedin_publisher import test_linkedin_connection
                status["linkedin"] = test_linkedin_connection()
            except Exception:
                status["linkedin"] = False
        else:
            status["linkedin"] = False
        
        return status
