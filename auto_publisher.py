"""
Auto Publisher - Multi-Brand Scheduler
======================================
Iterates through all registered brands in BotRegistry.
Checks their schedules and triggers publishing if criteria are met.
"""
import asyncio
import pytz
from datetime import datetime
from typing import Any

from bot_registry import BotRegistry

async def start_scheduler_loop() -> None:
    """Main scheduling loop running in background."""
    print("[SCHEDULER] ⏳ Starting Auto-Publisher Scheduler...")
    await asyncio.sleep(10)  # Warming up

    while True:
        try:
            workers = BotRegistry.get_all_workers()
            if not workers:
                print("[SCHEDULER] Waiting for workers to register...")
                await asyncio.sleep(10)
                continue

            for brand_key, worker in workers.items():
                try:
                    await _check_and_publish(worker)
                except Exception as e:
                    print(f"[SCHEDULER] Error processing {brand_key}: {e}")

            await asyncio.sleep(60)  # Check every minute

        except Exception as e:
            print(f"[SCHEDULER] Critical Loop Error: {e}")
            await asyncio.sleep(60)

async def _check_and_publish(worker: Any) -> None:
    """Check schedule for a specific worker and publish if needed."""
    brand = worker.brand
    schedule = brand.schedule
    
    # 1. Check Timezone & Business Hours
    tz_name = schedule.get("timezone", "UTC")
    try:
        tz = pytz.timezone(tz_name)
    except:
        tz = pytz.UTC
        
    now = datetime.now(tz)
    current_hour = now.hour
    
    wake = schedule.get("wake_hour", 9)
    sleep = schedule.get("sleep_hour", 22)
    
    if not (wake <= current_hour < sleep):
        # Sleeping
        return

    # 2. Check Daily Limit
    limit = schedule.get("posts_per_day", 8)
    if worker.posts_today >= limit:
        return

    # 3. Check Interval
    active_hours = max(1, sleep - wake)
    interval_minutes = (active_hours * 60) / max(1, limit)
    
    should_post = False
    
    if not worker.last_post_time:
        should_post = True
    else:
        # Normalize to system time for delta
        last_post = worker.last_post_time
        if last_post.tzinfo is not None:
             last_post = last_post.replace(tzinfo=None)
             
        delta = datetime.now() - last_post
        if delta.total_seconds() > (interval_minutes * 60):
            should_post = True

    if should_post:
        print(f"[SCHEDULER] 🚀 Triggering post for {brand.display_name}")
        # Call the worker's publishing method
        # Note: We pass None as context because we're not triggered by a Telegram update
        asyncio.create_task(worker._fetch_and_generate_native_content(None))
