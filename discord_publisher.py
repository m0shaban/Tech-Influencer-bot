"""
Discord Publisher Module
Send messages via a Discord webhook (supports text and optional link/image embed)
"""

from typing import Any, Dict, Optional
import os
import requests
from dotenv import load_dotenv

load_dotenv()

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
DISCORD_USERNAME = os.getenv("DISCORD_USERNAME", "RoboBot")
DISCORD_AVATAR_URL = os.getenv("DISCORD_AVATAR_URL")


class DiscordPublisher:
    """Publish content to Discord using an incoming webhook"""

    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or DISCORD_WEBHOOK_URL
        if not self.webhook_url:
            raise ValueError("Discord webhook URL not configured")

    def _build_payload(
        self, caption: str, link: Optional[str] = None, image_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Prepare Discord payload with optional embed"""
        # Keep the raw content short enough for Discord limits
        content = caption if len(caption) <= 1900 else caption[:1897] + "..."
        if link and link not in content:
            content = f"{content}\n{link}"

        payload: Dict[str, Any] = {
            "content": content,
            "username": DISCORD_USERNAME,
        }

        if DISCORD_AVATAR_URL:
            payload["avatar_url"] = DISCORD_AVATAR_URL

        embed: Dict[str, Any] = {"title": caption[:150], "description": caption[:2000]}
        if link:
            embed["url"] = link
        if image_url:
            embed["image"] = {"url": image_url}

        # Only include embed if we have more than plain text
        if link or image_url:
            payload["embeds"] = [embed]

        return payload

    def publish(
        self, caption: str, link: Optional[str] = None, image_url: Optional[str] = None
    ) -> Dict[str, Any]:
        payload = self._build_payload(caption, link, image_url)
        webhook_url = self.webhook_url
        if not webhook_url:
            raise ValueError("Discord webhook URL not configured")

        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()

        return {
            "status": "success",
            "platform": "discord",
            "response": response.json() if response.content else {"ok": True},
        }


def test_discord_connection() -> bool:
    """Verify the webhook is reachable without sending a message"""
    if not DISCORD_WEBHOOK_URL:
        return False
    try:
        # GET returns webhook metadata if valid
        resp = requests.get(DISCORD_WEBHOOK_URL, timeout=5)
        return resp.status_code == 200
    except Exception:
        return False
