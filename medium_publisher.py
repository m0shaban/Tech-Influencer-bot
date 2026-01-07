"""
Medium Publisher Module
Create posts on Medium using the v1 API
"""

from typing import Any, Dict, List, Optional
import os
import requests
from dotenv import load_dotenv

load_dotenv()

MEDIUM_INTEGRATION_TOKEN = os.getenv("MEDIUM_INTEGRATION_TOKEN")
MEDIUM_USER_ID = os.getenv("MEDIUM_USER_ID")


class MediumPublisher:
    """Publish articles to Medium"""

    def __init__(self, token: Optional[str] = None, user_id: Optional[str] = None):
        self.token = token or MEDIUM_INTEGRATION_TOKEN
        self.user_id = user_id or MEDIUM_USER_ID
        if not self.token or not self.user_id:
            raise ValueError("Medium token or user ID not configured")

        self.base_url = "https://api.medium.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _build_html(
        self, caption: str, link: Optional[str], image_url: Optional[str]
    ) -> str:
        """Construct simple HTML content for Medium"""
        parts: List[str] = []

        if image_url:
            parts.append(f'<p><img src="{image_url}" alt="image"/></p>')

        parts.append(f"<p>{caption}</p>")

        if link:
            parts.append(f'<p>Source: <a href="{link}">{link}</a></p>')

        return "\n".join(parts)

    def publish_article(
        self,
        title: str,
        content: str,
        canonical_url: Optional[str] = None,
        image_url: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create a new post on Medium"""
        if not title:
            raise ValueError("Title is required for Medium posts")

        html_content = self._build_html(content, canonical_url, image_url)

        payload = {
            "title": title,
            "contentFormat": "html",
            "content": html_content,
            "publishStatus": "public",
        }

        if canonical_url:
            payload["canonicalUrl"] = canonical_url
        if tags:
            payload["tags"] = tags[:5]  # Medium accepts up to 5 tags

        url = f"{self.base_url}/users/{self.user_id}/posts"
        response = requests.post(url, json=payload, headers=self.headers, timeout=15)
        response.raise_for_status()

        return {"status": "success", "platform": "medium", "response": response.json()}

    def check_profile(self) -> bool:
        """Validate token by fetching the authenticated user"""
        url = f"{self.base_url}/me"
        response = requests.get(url, headers=self.headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        return bool(data.get("data", {}).get("id"))


def test_medium_connection() -> bool:
    """Verify Medium credentials quickly"""
    if not MEDIUM_INTEGRATION_TOKEN or not MEDIUM_USER_ID:
        return False
    try:
        publisher = MediumPublisher()
        return publisher.check_profile()
    except Exception:
        return False
