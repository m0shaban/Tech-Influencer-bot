"""
Dev.to Publisher Module (Enterprise V2)
---------------------------------------
Publishes SEO-optimized articles to the Dev.to (Forem) ecosystem.
Features:
- Canonical URL support (Cross-Posting SEO).
- Direct Tag Management (from AI keywords).
- Robust Error Handling & Retries.
- Series Support.

Author: RoboVAI
Version: 2.0.0
"""

import os
import logging
import time
import requests
from typing import Dict, Any, Optional, List
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dotenv import load_dotenv

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("DevtoPublisher")

load_dotenv()

class DevtoPublisher:
    """
    Enterprise adapter for Dev.to API.
    Docs: https://developers.forem.com/api/v1
    """

    API_BASE = "https://dev.to/api"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("DEVTO_API_KEY")
        
        # Session Configuration
        self.session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST", "GET"]
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retries))
        
        if self.api_key:
            self.session.headers.update({
                "api-key": self.api_key,
                "Content-Type": "application/json",
                "User-Agent": "RoboVAI-Enterprise-Bot/2.0"
            })
        else:
            logger.warning("⚠️ DEVTO_API_KEY not found. Publisher disabled.")

    def is_configured(self) -> bool:
        """Check if the module is active."""
        return bool(self.api_key)

    def verify_credentials(self) -> Dict[str, Any]:
        """Test API connectivity and return user info."""
        if not self.is_configured():
            return {"success": False, "message": "No API Key"}

        try:
            # Fetch authenticated user
            resp = self.session.get(f"{self.API_BASE}/users/me", timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                logger.info(f"✅ Connected to Dev.to as: {data.get('username')}")
                return {"success": True, "username": data.get("username"), "name": data.get("name")}
            else:
                return {"success": False, "message": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def publish_article(
        self,
        title: str,
        body_markdown: str,
        tags: Optional[List[str]] = None,
        cover_image_url: Optional[str] = None,
        canonical_url: Optional[str] = None,
        series: Optional[str] = None,
        published: bool = True
    ) -> Dict[str, Any]:
        """
        Publishes a new article to Dev.to.

        Args:
            title: Article headline.
            body_markdown: Content in Markdown.
            tags: List of tags (Max 4).
            cover_image_url: URL for the main image.
            canonical_url: Original URL (e.g., Blogger link) for SEO juice.
            series: Name of the series to add this post to.
            published: True to publish immediately, False for draft.
        """
        if not self.is_configured():
            return {"success": False, "message": "Not Configured"}

        endpoint = f"{self.API_BASE}/articles"
        
        # Prepare Tags (Max 4, alphanumeric only)
        final_tags = []
        if tags:
            for t in tags:
                clean_tag = "".join(e for e in t if e.isalnum())
                if clean_tag and clean_tag not in final_tags:
                    final_tags.append(clean_tag)
        
        # Ensure at least one tag
        if not final_tags:
            final_tags = ["tech", "ai", "programming", "news"]
        
        payload = {
            "article": {
                "title": title[:100], # Limit title length
                "body_markdown": body_markdown,
                "published": published,
                "tags": final_tags[:4],
                "main_image": cover_image_url,
                "canonical_url": canonical_url,
                "series": series
            }
        }

        # Remove None values to avoid API errors
        payload["article"] = {k: v for k, v in payload["article"].items() if v is not None}

        try:
            logger.info(f"🚀 Publishing to Dev.to: {title[:30]}...")
            resp = self.session.post(endpoint, json=payload, timeout=30)
            
            if resp.status_code in [200, 201]:
                data = resp.json()
                url = data.get("url")
                logger.info(f"✅ Dev.to Publish Success: {url}")
                return {
                    "success": True, 
                    "url": url, 
                    "id": data.get("id"),
                    "canonical_url": data.get("canonical_url")
                }
            
            # Application Error
            logger.error(f"❌ Dev.to Error {resp.status_code}: {resp.text}")
            return {
                "success": False, 
                "message": f"API Error: {resp.text}",
                "status_code": resp.status_code
            }

        except Exception as e:
            logger.exception(f"❌ Dev.to Exception: {e}")
            return {"success": False, "message": str(e)}

if __name__ == "__main__":
    print("Testing Dev.to Publisher...")
    pub = DevtoPublisher()
    print(pub.verify_credentials())
