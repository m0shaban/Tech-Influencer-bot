"""
Scheduled Publisher Background Task
Runs in background to publish scheduled posts at their designated times
"""

import asyncio
import time
from datetime import datetime
from typing import Optional
import os

from dotenv import load_dotenv
from publishing_scheduler import PublishingScheduler
from publishing_reporter import get_reporter

load_dotenv()


class ScheduledPublisherTask:
    """Background task to process scheduled posts"""

    def __init__(self, check_interval: int = 30):
        """
        Initialize the scheduler task

        Args:
            check_interval: How often to check for ready posts (seconds)
        """
        self.scheduler = PublishingScheduler()
        self.reporter = get_reporter()
        self.check_interval = check_interval
        self.is_running = False

    async def _publish_post(self, post):
        """Publish a single scheduled post"""
        try:
            # Import here to avoid circular imports
            from multi_platform_publisher import MultiPlatformPublisher

            # Create publisher for single platform
            publisher = MultiPlatformPublisher(use_scheduler=False)

            # Publish based on platform
            if post.platform == "telegram":
                # Skip - telegram was already published immediately
                return

            elif post.platform == "discord":
                from discord_publisher import DiscordPublisher

                pub = DiscordPublisher()
                result = pub.publish(
                    caption=post.caption, link=post.link, image_url=post.image_url
                )

            elif post.platform == "blogger":
                from blogger_publisher import BloggerPublisher

                pub = BloggerPublisher()
                # Extract title from caption
                lines = post.caption.split("\n")
                title = lines[0][:100] if lines else post.caption[:100]
                result = pub.publish_post(
                    title=title,
                    caption=post.caption,
                    link=post.link,
                    image_url=post.image_url,
                    labels=["AI", "Technology"],
                )

            elif post.platform == "facebook":
                from facebook_publisher import FacebookPublisher

                pub = FacebookPublisher()
                if post.image_url:
                    result = pub.publish_photo(
                        message=post.caption, image_url=post.image_url
                    )
                elif post.link:
                    result = pub.publish_link(message=post.caption, link=post.link)
                else:
                    result = pub.publish_text(message=post.caption)

            elif post.platform == "linkedin":
                from linkedin_publisher import LinkedInPublisher

                pub = LinkedInPublisher()
                if post.image_url:
                    result = pub.publish_image_post(
                        post.caption, post.image_url, post.link
                    )
                elif post.link:
                    result = pub.publish_article(post.caption, post.link)
                else:
                    result = pub.publish_text_post(post.caption, post.link)

            elif post.platform == "twitter":
                from twitter_publisher import TwitterPublisher

                pub = TwitterPublisher()
                tweet_text = (
                    post.caption
                    if (post.link and post.link in post.caption)
                    else f"{post.caption}\n\n{post.link}" if post.link else post.caption
                )
                result = pub.publish_tweet(text=tweet_text, image_url=post.image_url)

            elif post.platform == "reddit":
                from reddit_publisher import RedditPublisher

                pub = RedditPublisher()
                subreddit = os.getenv("REDDIT_SUBREDDIT", "technology")
                lines = post.caption.split("\n")
                title = lines[0][:250] if lines else post.caption[:250]

                if post.link:
                    result = pub.submit_link(
                        subreddit=subreddit, title=title, url=post.link
                    )
                else:
                    result = pub.submit_text(
                        subreddit=subreddit, title=title, text=post.caption
                    )

            elif post.platform == "medium":
                from medium_publisher import MediumPublisher

                pub = MediumPublisher()
                result = pub.publish_article(
                    title=post.caption[:80],
                    content=post.caption,
                    canonical_url=post.link,
                    image_url=post.image_url,
                )

            elif post.platform == "devto":
                from devto_publisher import DevtoPublisher

                pub = DevtoPublisher()
                result = pub.publish(
                    caption=post.caption,
                    link=post.link,
                    image_url=post.image_url,
                )

            else:
                result = {
                    "success": False,
                    "message": f"Unknown platform: {post.platform}",
                }

            # Check result
            if result.get("success") or result.get("status") == "success":
                self.scheduler.mark_published(post)

                # Send success report
                post_url = result.get("url")
                await self.reporter.report_platform_success(
                    platform=post.platform, post_url=post_url
                )

                print(f"✅ Published to {post.platform} at {datetime.now()}")
            else:
                self.scheduler.mark_failed(post)

                # Check if should retry
                if self.scheduler.should_retry(post):
                    self.scheduler.reschedule_failed_post(post)
                    print(f"🔄 Rescheduled {post.platform} (retry {post.retry_count})")
                else:
                    error_msg = result.get("message") or result.get(
                        "error", "Unknown error"
                    )
                    await self.reporter.report_platform_failure(
                        platform=post.platform, error=error_msg
                    )
                    print(f"❌ Failed to publish to {post.platform}: {error_msg}")

        except Exception as e:
            self.scheduler.mark_failed(post)
            await self.reporter.report_platform_failure(
                platform=post.platform, error=str(e)
            )
            print(f"❌ Error publishing to {post.platform}: {e}")

    async def run(self):
        """Run the background task"""
        self.is_running = True
        print("📅 Scheduled Publisher Task started")

        while self.is_running:
            try:
                # Get posts ready to publish
                ready_posts = self.scheduler.get_ready_posts()

                if ready_posts:
                    print(f"📬 Found {len(ready_posts)} posts ready to publish")

                    # Publish each post
                    for post in ready_posts:
                        await self._publish_post(post)

                        # Small delay between posts
                        await asyncio.sleep(2)

                # Clean up old posts
                cleared = self.scheduler.clear_old_posts(hours=24)
                if cleared > 0:
                    print(f"🧹 Cleared {cleared} old posts")

                # Wait before next check
                await asyncio.sleep(self.check_interval)

            except Exception as e:
                print(f"❌ Error in scheduler task: {e}")
                await self.reporter.report_error(str(e))
                await asyncio.sleep(self.check_interval)

    def stop(self):
        """Stop the background task"""
        self.is_running = False
        print("📅 Scheduled Publisher Task stopped")


# Global task instance
_task = None


def start_scheduler_task(check_interval: int = 30):
    """Start the global scheduler task"""
    global _task
    if _task is None:
        _task = ScheduledPublisherTask(check_interval=check_interval)
    return _task


async def main():
    """Test the scheduler task"""
    task = start_scheduler_task(check_interval=10)

    try:
        await task.run()
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
        task.stop()


if __name__ == "__main__":
    asyncio.run(main())
