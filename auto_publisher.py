"""
Auto Publisher - Smart Pacing for Content Publishing
Handles automatic content fetching and publishing with business hours and smart intervals.
"""

import asyncio
import json
import os
import random
from datetime import datetime, time as dt_time
from pathlib import Path
from typing import Optional, Callable, Any
import pytz

# Cairo timezone for business hours
CAIRO_TZ = pytz.timezone("Africa/Cairo")

# Business hours (9 AM to 11 PM Cairo time)
# Can be overridden via env:
# - AUTO_PUBLISH_BUSINESS_START=HH:MM
# - AUTO_PUBLISH_BUSINESS_END=HH:MM
# - AUTO_PUBLISH_IGNORE_HOURS=1 (run 24/7)


def _parse_hhmm(value: str, fallback: dt_time) -> dt_time:
    try:
        s = (value or "").strip()
        if not s:
            return fallback
        parts = s.split(":")
        if len(parts) != 2:
            return fallback
        hour = int(parts[0])
        minute = int(parts[1])
        if hour < 0 or hour > 23 or minute < 0 or minute > 59:
            return fallback
        return dt_time(hour, minute)
    except Exception:
        return fallback


BUSINESS_START = _parse_hhmm(
    os.getenv("AUTO_PUBLISH_BUSINESS_START", ""), dt_time(9, 0)
)
BUSINESS_END = _parse_hhmm(os.getenv("AUTO_PUBLISH_BUSINESS_END", ""), dt_time(23, 0))
IGNORE_BUSINESS_HOURS = str(
    os.getenv("AUTO_PUBLISH_IGNORE_HOURS", "") or ""
).strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

# Default interval settings (in seconds) - overridden by brand config
DEFAULT_MIN_INTERVAL = 20 * 60  # 20 minutes
DEFAULT_MAX_INTERVAL = 40 * 60  # 40 minutes

# Default daily limits - overridden by brand config
DEFAULT_MAX_POSTS_PER_DAY = 50

# State file
STATUS_FILE = Path(__file__).parent / "autopublisher_status.json"


def _load_config() -> dict:
    """Load config.json safely."""
    try:
        cfg_path = Path(__file__).parent / "config.json"
        if not cfg_path.exists():
            return {}
        return json.loads(cfg_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _is_multi_brand_mode() -> bool:
    """Check if multi-brand mode is enabled."""
    data = _load_config()
    brands = data.get("brands")
    return isinstance(brands, dict) and bool(brands)


def _get_brand_schedule_settings(brand_key: str = None) -> dict:
    """
    Get schedule settings from brand config.
    
    Returns:
        dict with: min_interval, max_interval, max_posts_per_day, timezone
    """
    cfg = _load_config()
    brands = cfg.get("brands", {})
    
    # If brand_key provided, use that brand's schedule
    if brand_key and brand_key in brands:
        brand_cfg = brands[brand_key]
    else:
        # Use active_brand or first available brand
        active = cfg.get("active_brand", "")
        if active and active in brands:
            brand_cfg = brands[active]
        elif brands:
            brand_cfg = list(brands.values())[0]
        else:
            brand_cfg = {}
    
    schedule = brand_cfg.get("schedule", {})
    
    # Get min_interval_minutes from brand config (default: 60 min)
    min_interval_minutes = schedule.get("min_interval_minutes", 60)
    
    # Calculate interval range: min_interval to min_interval + 20 min variance
    min_interval = min_interval_minutes * 60
    max_interval = (min_interval_minutes + 20) * 60
    
    # Get posts_per_day from brand config (default: 8)
    max_posts = schedule.get("posts_per_day", DEFAULT_MAX_POSTS_PER_DAY)
    
    # Get timezone from brand config
    timezone = schedule.get("timezone", "Africa/Cairo")
    
    return {
        "min_interval": min_interval,
        "max_interval": max_interval,
        "max_posts_per_day": max_posts,
        "timezone": timezone,
        "brand_name": brand_cfg.get("display_name", "Unknown"),
    }


class AutoPublisher:
    """Automatic content publisher with smart pacing using per-brand scheduling"""

    def __init__(self):
        self.is_running = False
        self.posts_today = 0
        self.last_post_date: Optional[datetime] = None
        self.publish_callback: Optional[Callable] = None
        self.context: Any = None
        self.current_brand_settings: dict = {}
        self._load_state()
        self._refresh_brand_settings()

    def _refresh_brand_settings(self) -> None:
        """Refresh brand-specific schedule settings."""
        self.current_brand_settings = _get_brand_schedule_settings()

    def _get_timezone(self) -> Any:
        """Get timezone from current brand settings."""
        tz_name = self.current_brand_settings.get("timezone", "Africa/Cairo")
        return pytz.timezone(tz_name)

    def _save_state(self, next_run_seconds: Optional[int] = None) -> None:
        """Save current state to file for Dashboard"""
        try:
            now = self._get_brand_now()
            next_run_time = None
            if next_run_seconds:
                from datetime import timedelta

                next_run_time = (now + timedelta(seconds=next_run_seconds)).isoformat()

            max_posts = self.current_brand_settings.get("max_posts_per_day", DEFAULT_MAX_POSTS_PER_DAY)
            
            data = {
                "is_running": self.is_running,
                "posts_today": self.posts_today,
                "last_post_date": (
                    self.last_post_date.isoformat() if self.last_post_date else None
                ),
                "updated_at": now.isoformat(),
                "next_run_estimated": next_run_time,
                "business_hours_status": (
                    "OPEN" if self._is_business_hours() else "CLOSED"
                ),
                "max_posts_per_day": max_posts,
                "brand_settings": self.current_brand_settings,
            }
            STATUS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"⚠️ Failed to save state: {e}")

    def _load_state(self) -> None:
        """Load state from file"""
        if not STATUS_FILE.exists():
            return
        try:
            data = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
            self.posts_today = data.get("posts_today", 0)
            if data.get("last_post_date"):
                self.last_post_date = datetime.fromisoformat(data["last_post_date"])
                # Reset if stale (handled in main loop anyway, but good to have)
        except Exception:
            pass

    def _get_brand_now(self) -> datetime:
        """Get current time in brand's timezone"""
        return datetime.now(self._get_timezone())

    def _is_business_hours(self) -> bool:
        """Check if current time is within business hours (brand's timezone)"""
        if IGNORE_BUSINESS_HOURS or _is_multi_brand_mode():
            return True
        now = self._get_brand_now()
        current_time = now.time()
        return BUSINESS_START <= current_time <= BUSINESS_END

    def _seconds_until_business_hours(self) -> int:
        """Calculate seconds until next business hours start"""
        if IGNORE_BUSINESS_HOURS or _is_multi_brand_mode():
            return 0
        now = self._get_brand_now()
        current_time = now.time()

        if current_time < BUSINESS_START:
            # Same day, wait until 9 AM
            target = now.replace(
                hour=BUSINESS_START.hour,
                minute=BUSINESS_START.minute,
                second=0,
                microsecond=0,
            )
        else:
            # Next day 9 AM
            from datetime import timedelta

            tomorrow = now + timedelta(days=1)
            target = tomorrow.replace(
                hour=BUSINESS_START.hour,
                minute=BUSINESS_START.minute,
                second=0,
                microsecond=0,
            )

        return int((target - now).total_seconds())

    def _get_smart_interval(self) -> int:
        """Get random interval between posts using brand's schedule settings"""
        self._refresh_brand_settings()
        min_interval = self.current_brand_settings.get("min_interval", DEFAULT_MIN_INTERVAL)
        max_interval = self.current_brand_settings.get("max_interval", DEFAULT_MAX_INTERVAL)
        return random.randint(int(min_interval), int(max_interval))

    def _reset_daily_counter(self) -> None:
        """Reset daily post counter if it's a new day"""
        now = self._get_brand_now()
        if self.last_post_date is None or self.last_post_date.date() != now.date():
            self.posts_today = 0
            self.last_post_date = now
            print(f"New day started - reset counter ({now.strftime('%Y-%m-%d')})")

    def _can_post(self) -> bool:
        """Check if we can post (within limits using brand's max_posts_per_day)"""
        self._reset_daily_counter()
        self._refresh_brand_settings()
        max_posts = self.current_brand_settings.get("max_posts_per_day", DEFAULT_MAX_POSTS_PER_DAY)
        return self.posts_today < max_posts

    async def _do_publish(self) -> bool:
        """Execute one publish cycle"""
        if self.publish_callback is None or self.context is None:
            print("Publish callback or context not set")
            return False

        try:
            result = await self.publish_callback(self.context, override_status=False)

            if result.get("status") == "published":
                self.posts_today += 1
                self.last_post_date = self._get_brand_now()
                self._save_state()
                print(f"Published successfully! (Post #{self.posts_today} today)")
                return True
            elif result.get("status") in {"no_news", "sleeping"}:
                print("No new content available")
                return True  # Not an error, just no content
            else:
                error = result.get("error", "Unknown error")
                print(f"Publish failed: {error}")
                return False

        except Exception as e:
            print(f"Error during publish: {e}")
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
        self._refresh_brand_settings()

        print("Auto Publisher started")
        print(f"📊 Brand Settings: {self.current_brand_settings.get('brand_name', 'Unknown')}")
        
        if IGNORE_BUSINESS_HOURS:
            try:
                print(
                    "Business hours: DISABLED (AUTO_PUBLISH_IGNORE_HOURS=1) — running 24/7"
                )
            except UnicodeEncodeError:
                print(
                    "Business hours: DISABLED (AUTO_PUBLISH_IGNORE_HOURS=1) -- running 24/7"
                )
        else:
            try:
                print(
                    f"Business hours: {BUSINESS_START.strftime('%H:%M')} - {BUSINESS_END.strftime('%H:%M')} ({self.current_brand_settings.get('timezone', 'Cairo')})"
                )
            except UnicodeEncodeError:
                print(
                    f"Business hours: {BUSINESS_START.strftime('%H:%M')} - {BUSINESS_END.strftime('%H:%M')} ({self.current_brand_settings.get('timezone', 'Cairo')})"
                )
        
        max_posts = self.current_brand_settings.get("max_posts_per_day", DEFAULT_MAX_POSTS_PER_DAY)
        min_interval_min = self.current_brand_settings.get("min_interval", DEFAULT_MIN_INTERVAL) // 60
        max_interval_min = self.current_brand_settings.get("max_interval", DEFAULT_MAX_INTERVAL) // 60
        
        print(f"Max posts/day: {max_posts}")
        print(f"Interval: {min_interval_min}-{max_interval_min} minutes")

        while self.is_running:
            try:
                # Check business hours
                if not self._is_business_hours():
                    wait_seconds = self._seconds_until_business_hours()
                    wait_hours = wait_seconds / 3600
                    brand_now = self._get_brand_now()
                    tz_name = self.current_brand_settings.get("timezone", "Unknown")
                    print(
                        f"Outside business hours ({brand_now.strftime('%H:%M')} {tz_name})"
                    )
                    print(f"Sleeping for {wait_hours:.1f} hours until 9:00 AM...")
                    self._save_state(next_run_seconds=wait_seconds)
                    await asyncio.sleep(wait_seconds)
                    continue

                # Check daily limit
                if not self._can_post():
                    max_posts = self.current_brand_settings.get("max_posts_per_day", DEFAULT_MAX_POSTS_PER_DAY)
                    print(f"Daily limit reached ({max_posts} posts)")
                    # Sleep until next day's business hours
                    wait_seconds = self._seconds_until_business_hours()
                    self._save_state(next_run_seconds=wait_seconds)
                    await asyncio.sleep(wait_seconds)
                    continue

                # Do publish
                brand_now = self._get_brand_now()
                print(
                    f"\nStarting publish cycle at {brand_now.strftime('%H:%M:%S')} ({self.current_brand_settings.get('timezone', 'Unknown')})"
                )

                success = await self._do_publish()

                # Calculate next interval
                interval = self._get_smart_interval()
                interval_minutes = interval / 60

                next_time = self._get_brand_now()
                from datetime import timedelta

                next_time += timedelta(seconds=interval)

                print(
                    f"Next publish in {interval_minutes:.0f} minutes (at {next_time.strftime('%H:%M')})"
                )
                self._save_state(next_run_seconds=interval)

                await asyncio.sleep(interval)

            except asyncio.CancelledError:
                print("Auto Publisher cancelled")
                break
            except Exception as e:
                print(f"Error in auto publisher loop: {e}")
                # Wait 5 minutes before retrying on error
                await asyncio.sleep(300)

        print("Auto Publisher stopped")

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
