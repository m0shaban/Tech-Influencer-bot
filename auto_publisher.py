"""
Auto Publisher - Smart Pacing for Content Publishing
Handles automatic content fetching and publishing with business hours and smart intervals.
"""

import asyncio
import random
from datetime import datetime, time as dt_time
from typing import Optional, Callable, Any
import pytz

# Cairo timezone for business hours
CAIRO_TZ = pytz.timezone("Africa/Cairo")

# Business hours (9 AM to 11 PM Cairo time)
BUSINESS_START = dt_time(9, 0)   # 9:00 AM
BUSINESS_END = dt_time(23, 0)    # 11:00 PM

# Smart interval settings (in seconds)
MIN_INTERVAL = 20 * 60  # 20 minutes
MAX_INTERVAL = 40 * 60  # 40 minutes

# Daily limits
MAX_POSTS_PER_DAY = 50


class AutoPublisher:
    """Automatic content publisher with smart pacing"""
    
    def __init__(self):
        self.is_running = False
        self.posts_today = 0
        self.last_post_date: Optional[datetime] = None
        self.publish_callback: Optional[Callable] = None
        self.context: Any = None
    
    def _get_cairo_now(self) -> datetime:
        """Get current time in Cairo timezone"""
        return datetime.now(CAIRO_TZ)
    
    def _is_business_hours(self) -> bool:
        """Check if current time is within business hours (Cairo time)"""
        now = self._get_cairo_now()
        current_time = now.time()
        return BUSINESS_START <= current_time <= BUSINESS_END
    
    def _seconds_until_business_hours(self) -> int:
        """Calculate seconds until next business hours start"""
        now = self._get_cairo_now()
        current_time = now.time()
        
        if current_time < BUSINESS_START:
            # Same day, wait until 9 AM
            target = now.replace(
                hour=BUSINESS_START.hour,
                minute=BUSINESS_START.minute,
                second=0,
                microsecond=0
            )
        else:
            # Next day 9 AM
            from datetime import timedelta
            tomorrow = now + timedelta(days=1)
            target = tomorrow.replace(
                hour=BUSINESS_START.hour,
                minute=BUSINESS_START.minute,
                second=0,
                microsecond=0
            )
        
        return int((target - now).total_seconds())
    
    def _get_smart_interval(self) -> int:
        """Get random interval between posts (20-40 minutes)"""
        return random.randint(MIN_INTERVAL, MAX_INTERVAL)
    
    def _reset_daily_counter(self) -> None:
        """Reset daily post counter if it's a new day"""
        now = self._get_cairo_now()
        if self.last_post_date is None or self.last_post_date.date() != now.date():
            self.posts_today = 0
            self.last_post_date = now
            print(f"📅 New day started - reset counter ({now.strftime('%Y-%m-%d')})")
    
    def _can_post(self) -> bool:
        """Check if we can post (within limits)"""
        self._reset_daily_counter()
        return self.posts_today < MAX_POSTS_PER_DAY
    
    async def _do_publish(self) -> bool:
        """Execute one publish cycle"""
        if self.publish_callback is None or self.context is None:
            print("❌ Publish callback or context not set")
            return False
        
        try:
            result = await self.publish_callback(self.context, override_status=False)
            
            if result.get("status") == "published":
                self.posts_today += 1
                self.last_post_date = self._get_cairo_now()
                print(f"✅ Published successfully! (Post #{self.posts_today} today)")
                return True
            elif result.get("status") == "no_news":
                print("📭 No new content available")
                return True  # Not an error, just no content
            else:
                error = result.get("error", "Unknown error")
                print(f"⚠️ Publish failed: {error}")
                return False
                
        except Exception as e:
            print(f"❌ Error during publish: {e}")
            return False
    
    async def run(self, publish_callback: Callable, context: Any) -> None:
        """
        Main auto-publisher loop
        
        Args:
            publish_callback: Async function to call for publishing (fetch_and_publish)
            context: Telegram context to pass to the callback
        """
        self.publish_callback = publish_callback
        self.context = context
        self.is_running = True
        
        print("🚀 Auto Publisher started")
        print(f"⏰ Business hours: {BUSINESS_START.strftime('%H:%M')} - {BUSINESS_END.strftime('%H:%M')} (Cairo)")
        print(f"📊 Max posts/day: {MAX_POSTS_PER_DAY}")
        print(f"⏱️ Interval: {MIN_INTERVAL//60}-{MAX_INTERVAL//60} minutes")
        
        while self.is_running:
            try:
                # Check business hours
                if not self._is_business_hours():
                    wait_seconds = self._seconds_until_business_hours()
                    wait_hours = wait_seconds / 3600
                    cairo_now = self._get_cairo_now()
                    print(f"😴 Outside business hours ({cairo_now.strftime('%H:%M')} Cairo)")
                    print(f"💤 Sleeping for {wait_hours:.1f} hours until 9:00 AM...")
                    await asyncio.sleep(wait_seconds)
                    continue
                
                # Check daily limit
                if not self._can_post():
                    print(f"🛑 Daily limit reached ({MAX_POSTS_PER_DAY} posts)")
                    # Sleep until next day's business hours
                    wait_seconds = self._seconds_until_business_hours()
                    await asyncio.sleep(wait_seconds)
                    continue
                
                # Do publish
                cairo_now = self._get_cairo_now()
                print(f"\n🔄 Starting publish cycle at {cairo_now.strftime('%H:%M:%S')} Cairo")
                
                success = await self._do_publish()
                
                # Calculate next interval
                interval = self._get_smart_interval()
                interval_minutes = interval / 60
                
                next_time = self._get_cairo_now()
                from datetime import timedelta
                next_time += timedelta(seconds=interval)
                
                print(f"⏳ Next publish in {interval_minutes:.0f} minutes (at {next_time.strftime('%H:%M')})")
                
                await asyncio.sleep(interval)
                
            except asyncio.CancelledError:
                print("🛑 Auto Publisher cancelled")
                break
            except Exception as e:
                print(f"❌ Error in auto publisher loop: {e}")
                # Wait 5 minutes before retrying on error
                await asyncio.sleep(300)
        
        print("🛑 Auto Publisher stopped")
    
    def stop(self) -> None:
        """Stop the auto publisher"""
        self.is_running = False


# Global instance
_auto_publisher: Optional[AutoPublisher] = None


def get_auto_publisher() -> AutoPublisher:
    """Get or create the global auto publisher instance"""
    global _auto_publisher
    if _auto_publisher is None:
        _auto_publisher = AutoPublisher()
    return _auto_publisher


async def start_auto_publishing(publish_callback: Callable, context: Any) -> None:
    """Start the auto publishing task"""
    publisher = get_auto_publisher()
    await publisher.run(publish_callback, context)


def stop_auto_publishing() -> None:
    """Stop the auto publishing task"""
    if _auto_publisher:
        _auto_publisher.stop()
