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

# Smart interval settings (in seconds)
MIN_INTERVAL = 20 * 60  # 20 minutes
MAX_INTERVAL = 40 * 60  # 40 minutes

# Daily limits
MAX_POSTS_PER_DAY = 50

# State file
STATUS_FILE = Path(__file__).parent / "autopublisher_status.json"


def _is_multi_brand_mode() -> bool:
    """If config.json has multi-brand setup, per-brand schedule is handled in main.fetch_and_publish."""
    try:
        cfg_path = Path(__file__).parent / "config.json"
        if not cfg_path.exists():
            return False
        data = json.loads(cfg_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return False
        brands = data.get("brands")
        return isinstance(brands, dict) and bool(brands)
    except Exception:
        return False


class AutoPublisher:
    """Automatic content publisher with smart pacing"""

    def __init__(self):
        self.is_running = False
        self.posts_today = 0
        self.last_post_date: Optional[datetime] = None
        self.publish_callback: Optional[Callable] = None
        self.context: Any = None
        self._load_state()

    def _save_state(self, next_run_seconds: Optional[int] = None) -> None:
        """Save current state to file for Dashboard"""
        try:
            now = self._get_cairo_now()
            next_run_time = None
            if next_run_seconds:
                from datetime import timedelta

                next_run_time = (now + timedelta(seconds=next_run_seconds)).isoformat()

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
                "max_posts_per_day": MAX_POSTS_PER_DAY,
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

    def _get_cairo_now(self) -> datetime:
        """Get current time in Cairo timezone"""
        return datetime.now(CAIRO_TZ)

    def _is_business_hours(self) -> bool:
        """Check if current time is within business hours (Cairo time)"""
        if IGNORE_BUSINESS_HOURS or _is_multi_brand_mode():
            return True
        now = self._get_cairo_now()
        current_time = now.time()
        return BUSINESS_START <= current_time <= BUSINESS_END

    def _seconds_until_business_hours(self) -> int:
        """Calculate seconds until next business hours start"""
        if IGNORE_BUSINESS_HOURS or _is_multi_brand_mode():
            return 0
        now = self._get_cairo_now()
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
                self._save_state()
                print(f"✅ Published successfully! (Post #{self.posts_today} today)")
                return True
            elif result.get("status") in {"no_news", "sleeping"}:
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
        if IGNORE_BUSINESS_HOURS:
            print(
                "⏰ Business hours: DISABLED (AUTO_PUBLISH_IGNORE_HOURS=1) — running 24/7"
            )
        else:
            print(
                f"⏰ Business hours: {BUSINESS_START.strftime('%H:%M')} - {BUSINESS_END.strftime('%H:%M')} (Cairo)"
            )
        print(f"📊 Max posts/day: {MAX_POSTS_PER_DAY}")
        print(f"⏱️ Interval: {MIN_INTERVAL//60}-{MAX_INTERVAL//60} minutes")

        while self.is_running:
            try:
                # Check business hours
                if not self._is_business_hours():
                    wait_seconds = self._seconds_until_business_hours()
                    wait_hours = wait_seconds / 3600
                    cairo_now = self._get_cairo_now()
                    print(
                        f"😴 Outside business hours ({cairo_now.strftime('%H:%M')} Cairo)"
                    )
                    print(f"💤 Sleeping for {wait_hours:.1f} hours until 9:00 AM...")
                    self._save_state(next_run_seconds=wait_seconds)
                    await asyncio.sleep(wait_seconds)
                    continue

                # Check daily limit
                if not self._can_post():
                    print(f"🛑 Daily limit reached ({MAX_POSTS_PER_DAY} posts)")
                    # Sleep until next day's business hours
                    wait_seconds = self._seconds_until_business_hours()
                    self._save_state(next_run_seconds=wait_seconds)
                    await asyncio.sleep(wait_seconds)
                    continue

                # Do publish
                cairo_now = self._get_cairo_now()
                print(
                    f"\n🔄 Starting publish cycle at {cairo_now.strftime('%H:%M:%S')} Cairo"
                )

                success = await self._do_publish()

                # Calculate next interval
                interval = self._get_smart_interval()
                interval_minutes = interval / 60

                next_time = self._get_cairo_now()
                from datetime import timedelta

                next_time += timedelta(seconds=interval)

                print(
                    f"⏳ Next publish in {interval_minutes:.0f} minutes (at {next_time.strftime('%H:%M')})"
                )
                self._save_state(next_run_seconds=interval)

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
