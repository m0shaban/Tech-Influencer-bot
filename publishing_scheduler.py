"""
Publishing Scheduler
Smart scheduling system for multi-platform publishing with delays and custom prompts
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "platform_config.json"


@dataclass
class PlatformConfig:
    """Configuration for a single platform"""
    enabled: bool
    publish_mode: str  # "immediate" or "delayed"
    delay_minutes: int
    custom_prompt: str
    max_length: int
    priority: int


@dataclass
class ScheduledPost:
    """A post scheduled for publishing"""
    platform: str
    caption: str
    link: Optional[str]
    image_url: Optional[str]
    scheduled_time: datetime
    status: str = "pending"  # pending, published, failed
    retry_count: int = 0


class PublishingScheduler:
    """Manage scheduled publishing across platforms"""
    
    def __init__(self):
        self.config = self.load_config()
        self.pending_posts: List[ScheduledPost] = []
        self.admin_user_id = int(os.getenv("ADMIN_USER_ID", "0") or "0")
    
    def load_config(self) -> Dict[str, Any]:
        """Load platform configuration"""
        try:
            if CONFIG_PATH.exists():
                with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return self._get_default_config()
        except Exception as e:
            print(f"Error loading config: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "platforms": {},
            "global_settings": {
                "distribution_mode": "shared",
                "enable_reports": True,
                "report_to_admin": True,
                "min_interval_between_posts": 60,
                "max_posts_per_hour": 5,
            }
        }
    
    def save_config(self, config: Dict[str, Any]) -> None:
        """Save configuration to file"""
        try:
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def get_platform_config(self, platform: str) -> Optional[PlatformConfig]:
        """Get configuration for specific platform"""
        platform_data = self.config.get("platforms", {}).get(platform)
        if not platform_data:
            return None
        
        return PlatformConfig(
            enabled=platform_data.get("enabled", False),
            publish_mode=platform_data.get("publish_mode", "immediate"),
            delay_minutes=platform_data.get("delay_minutes", 0),
            custom_prompt=platform_data.get("custom_prompt", ""),
            max_length=platform_data.get("max_length", 1000),
            priority=platform_data.get("priority", 999),
        )
    
    def merge_custom_prompt(self, base_prompt: str, platform: str) -> str:
        """Merge platform custom prompt with base system prompt"""
        config = self.get_platform_config(platform)
        if not config or not config.custom_prompt:
            return base_prompt
        
        # Add platform-specific instructions after base prompt
        merged = base_prompt.strip()
        merged += "\n\n---\n\n"
        merged += f"### 🎯 PLATFORM-SPECIFIC INSTRUCTIONS FOR {platform.upper()}:\n"
        merged += config.custom_prompt.strip()
        return merged
    
    def get_enabled_platforms(self) -> List[str]:
        """Get list of enabled platforms sorted by priority"""
        platforms = []
        for platform, config in self.config.get("platforms", {}).items():
            if config.get("enabled", False):
                platforms.append((platform, config.get("priority", 999)))
        
        # Sort by priority
        platforms.sort(key=lambda x: x[1])
        return [p[0] for p in platforms]
    
    def calculate_publish_time(self, platform: str, base_time: Optional[datetime] = None) -> datetime:
        """Calculate when to publish to this platform"""
        if base_time is None:
            base_time = datetime.now()
        
        config = self.get_platform_config(platform)
        if not config:
            return base_time
        
        if config.publish_mode == "immediate":
            return base_time
        else:
            return base_time + timedelta(minutes=config.delay_minutes)
    
    def schedule_post(
        self,
        platform: str,
        caption: str,
        link: Optional[str] = None,
        image_url: Optional[str] = None,
        base_time: Optional[datetime] = None,
    ) -> ScheduledPost:
        """Schedule a post for a platform"""
        publish_time = self.calculate_publish_time(platform, base_time)
        
        post = ScheduledPost(
            platform=platform,
            caption=caption,
            link=link,
            image_url=image_url,
            scheduled_time=publish_time,
        )
        
        self.pending_posts.append(post)
        return post
    
    def schedule_multi_platform(
        self,
        caption: str,
        link: Optional[str] = None,
        image_url: Optional[str] = None,
        platforms: Optional[List[str]] = None,
    ) -> List[ScheduledPost]:
        """Schedule posts across multiple platforms"""
        if platforms is None:
            platforms = self.get_enabled_platforms()
        
        base_time = datetime.now()
        scheduled_posts = []
        
        for platform in platforms:
            post = self.schedule_post(
                platform=platform,
                caption=caption,
                link=link,
                image_url=image_url,
                base_time=base_time,
            )
            scheduled_posts.append(post)
        
        return scheduled_posts
    
    def get_pending_posts(self, platform: Optional[str] = None) -> List[ScheduledPost]:
        """Get pending posts, optionally filtered by platform"""
        now = datetime.now()
        pending = [p for p in self.pending_posts if p.status == "pending"]
        
        if platform:
            pending = [p for p in pending if p.platform == platform]
        
        return pending
    
    def get_ready_posts(self) -> List[ScheduledPost]:
        """Get posts that are ready to be published"""
        now = datetime.now()
        ready = [
            p for p in self.pending_posts
            if p.status == "pending" and p.scheduled_time <= now
        ]
        
        # Sort by scheduled time
        ready.sort(key=lambda x: x.scheduled_time)
        return ready
    
    def mark_published(self, post: ScheduledPost) -> None:
        """Mark a post as published"""
        post.status = "published"
    
    def mark_failed(self, post: ScheduledPost) -> None:
        """Mark a post as failed"""
        post.status = "failed"
        post.retry_count += 1
    
    def should_retry(self, post: ScheduledPost) -> bool:
        """Check if a failed post should be retried"""
        global_settings = self.config.get("global_settings", {})
        max_retries = global_settings.get("retry_attempts", 3)
        return post.retry_count < max_retries
    
    def reschedule_failed_post(self, post: ScheduledPost) -> None:
        """Reschedule a failed post for retry"""
        global_settings = self.config.get("global_settings", {})
        retry_delay = global_settings.get("retry_delay_minutes", 5)
        
        post.status = "pending"
        post.scheduled_time = datetime.now() + timedelta(minutes=retry_delay)
    
    def get_custom_prompt(self, platform: str, base_prompt: str) -> str:
        """Get custom prompt for platform, merged with base prompt"""
        config = self.get_platform_config(platform)
        if not config or not config.custom_prompt:
            return base_prompt
        
        # Merge prompts
        return f"{base_prompt}\n\nخصائص المنصة ({platform}):\n{config.custom_prompt}"
    
    def generate_schedule_report(self) -> str:
        """Generate a report of scheduled posts"""
        pending = self.get_pending_posts()
        
        if not pending:
            return "📭 لا توجد منشورات مجدولة حالياً"
        
        report = "📅 **جدول النشر**\n\n"
        
        # Group by platform
        by_platform: Dict[str, List[ScheduledPost]] = {}
        for post in pending:
            if post.platform not in by_platform:
                by_platform[post.platform] = []
            by_platform[post.platform].append(post)
        
        for platform, posts in sorted(by_platform.items()):
            report += f"**{platform.upper()}:** {len(posts)} منشور\n"
            for post in sorted(posts, key=lambda x: x.scheduled_time):
                time_str = post.scheduled_time.strftime("%H:%M:%S")
                report += f"  • {time_str}\n"
            report += "\n"
        
        return report
    
    def clear_old_posts(self, hours: int = 24) -> int:
        """Clear posts older than specified hours"""
        cutoff = datetime.now() - timedelta(hours=hours)
        
        before_count = len(self.pending_posts)
        self.pending_posts = [
            p for p in self.pending_posts
            if p.scheduled_time > cutoff or p.status == "pending"
        ]
        after_count = len(self.pending_posts)
        
        return before_count - after_count


def main():
    """Test the scheduler"""
    scheduler = PublishingScheduler()
    
    print("=" * 60)
    print("📅 Publishing Scheduler Test")
    print("=" * 60)
    
    # Show enabled platforms
    enabled = scheduler.get_enabled_platforms()
    print(f"\n✅ Enabled platforms ({len(enabled)}):")
    for platform in enabled:
        config = scheduler.get_platform_config(platform)
        if config:
            print(f"  • {platform}: {config.publish_mode} (+{config.delay_minutes}min)")
    
    # Schedule test post
    print("\n📝 Scheduling test post...")
    posts = scheduler.schedule_multi_platform(
        caption="Test post from Publishing Scheduler",
        link="https://github.com/m0shaban/Tech-Influencer-bot",
    )
    
    print(f"\n✅ Scheduled {len(posts)} posts:")
    for post in posts:
        time_str = post.scheduled_time.strftime("%H:%M:%S")
        print(f"  • {post.platform}: {time_str}")
    
    # Show schedule report
    print("\n" + scheduler.generate_schedule_report())
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
