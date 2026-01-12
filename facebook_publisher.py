"""
Facebook Publisher Module (Enterprise V2)
-----------------------------------------
Advanced Facebook Page management utilizing Graph API v19.0.
Features:
- Robust Session Management with Automatic Retries
- Photo, Video, and Link Publishing
- "Link in First Comment" Strategy Support
- Post Analytics and Insights
- Comprehensive Error Handling

Author: RoboVAI
Version: 2.0.0
"""

import os
import logging
import json
import time
from typing import Optional, Dict, Any, Union, BinaryIO
from pathlib import Path
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dotenv import load_dotenv

# Setup Professional Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("facebook_pub.log"), logging.StreamHandler()]
)
logger = logging.getLogger("FacebookPublisher")

load_dotenv()

class FacebookPublisherError(Exception):
    """Custom exception for Facebook Publishing errors."""
    pass

class FacebookPublisher:
    """
    Enterprise-grade Facebook Page Publisher.
    Handles long-lived tokens, media uploads, and post management.
    """

    API_VERSION = "v19.0"
    BASE_URL = f"https://graph.facebook.com/{API_VERSION}"

    def __init__(self, page_id: Optional[str] = None, access_token: Optional[str] = None):
        """
        Initialize the publisher.
        
        Args:
            page_id: Facebook Page ID (numeric). Defaults to env FACEBOOK_PAGE_ID.
            access_token: Page Access Token. Defaults to env FACEBOOK_PAGE_ACCESS_TOKEN.
        """
        self.page_id = page_id or os.getenv("FACEBOOK_PAGE_ID")
        self.access_token = access_token or os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")

        if not self.page_id or not self.access_token:
            logger.critical("Missing Facebook credentials.")
            raise FacebookPublisherError("FACEBOOK_PAGE_ID and FACEBOOK_PAGE_ACCESS_TOKEN are required.")

        # Configure High-Performance Session
        self.session = requests.Session()
        retries = Retry(
            total=5,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST", "GET"]
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retries))
        self.session.params = {"access_token": self.access_token}

        # Verify credentials on init
        self._validate_connection()

    def _validate_connection(self):
        """Validates token and page access on startup."""
        try:
            response = self.session.get(f"{self.BASE_URL}/{self.page_id}")
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Connected to Facebook Page: {data.get('name')} (ID: {data.get('id')})")
            else:
                logger.error(f"❌ Failed to connect to Facebook: {response.text}")
                raise FacebookPublisherError(f"Connection failed: {response.text}")
        except Exception as e:
            logger.error(f"Network error during validation: {e}")
            raise

    def publish_text_post(self, message: str) -> Dict[str, Any]:
        """
        Publish a simple text status update.
        """
        endpoint = f"{self.BASE_URL}/{self.page_id}/feed"
        payload = {"message": message}
        
        return self._make_request("POST", endpoint, data=payload)

    def publish_link_post(self, message: str, link: str) -> Dict[str, Any]:
        """
        Publish a link with a message.
        """
        endpoint = f"{self.BASE_URL}/{self.page_id}/feed"
        payload = {
            "message": message,
            "link": link
        }
        return self._make_request("POST", endpoint, data=payload)

    def publish_photo(self, message: str, image_path: str, alt_text: str = "Robot Generated Image") -> Dict[str, Any]:
        """
        Uploads and publishes a photo from local disk.
        
        Args:
            message: Caption for the photo.
            image_path: Absolute path to the image file.
            alt_text: Accessibility text for screen readers.
        """
        if not os.path.exists(image_path):
            logger.error(f"Image not found at {image_path}")
            raise FileNotFoundError(f"Image file not found: {image_path}")

        endpoint = f"{self.BASE_URL}/{self.page_id}/photos"
        payload = {
            "message": message,
            "alt_text_custom": alt_text
        }
        
        # Open file safely
        try:
            with open(image_path, "rb") as img_file:
                files = {"source": img_file}
                # Note: 'params' in session handles access_token, but we pass payload in data
                # We need to construct the request carefully to mix multipart and data
                # requests lib handles data keys as form fields when files is present
                return self._make_request("POST", endpoint, data=payload, files=files)
        except Exception as e:
            logger.error(f"Error reading image file: {e}")
            raise FacebookPublisherError(f"File Error: {e}")

    def publish_video(self, message: str, video_path: str, title: str = "New Video") -> Dict[str, Any]:
        """
        Uploads a video to Facebook (Non-resumable, good for files < 1GB).
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        endpoint = f"{self.BASE_URL}/{self.page_id}/videos"
        payload = {
            "description": message,
            "title": title
        }

        try:
            with open(video_path, "rb") as vid_file:
                files = {"source": vid_file}
                return self._make_request("POST", endpoint, data=payload, files=files)
        except Exception as e:
            logger.error(f"Error publishing video: {e}")
            raise

    def post_comment(self, post_id: str, comment_text: str) -> Dict[str, Any]:
        """
        Posts a comment on a specific post.
        Useful for "Link in verify comments" strategy to boost reach.
        """
        endpoint = f"{self.BASE_URL}/{post_id}/comments"
        payload = {"message": comment_text}
        
        logger.info(f"Adding comment to post {post_id}...")
        return self._make_request("POST", endpoint, data=payload)

    def get_post_metrics(self, post_id: str) -> Dict[str, Any]:
        """
        Retrieves insights for a specific post (Likes, Shares, Comments).
        """
        endpoint = f"{self.BASE_URL}/{post_id}"
        params = {
            "fields": "shares,comments.summary(true),likes.summary(true),impressions"
        }
        # Merge session params (token) with specific params
        merged_params = {**self.session.params, **params}
        
        try:
            response = self.session.get(endpoint, params=merged_params)
            response.raise_for_status()
            data = response.json()
            
            stats = {
                "likes": data.get("likes", {}).get("summary", {}).get("total_count", 0),
                "comments": data.get("comments", {}).get("summary", {}).get("total_count", 0),
                "shares": data.get("shares", {}).get("count", 0),
                "id": data.get("id")
            }
            logger.info(f"📊 Stats for {post_id}: {stats}")
            return stats
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch metrics: {e}")
            return {}

    def _make_request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """
        Internal wrapper for HTTP requests with logging and error handling.
        """
        try:
            response = self.session.request(method, url, timeout=60, **kwargs)
            
            # Check for API-level errors even if 200 OK (Graph API sometimes does this, though usually 400)
            if response.status_code >= 400:
                error_data = response.json().get("error", {})
                error_msg = error_data.get("message", response.text)
                logger.error(f"Facebook API Error ({response.status_code}): {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "code": response.status_code
                }
            
            data = response.json()
            post_id = data.get("id") or data.get("post_id")  # Videos return 'id', Photos need parsing
            
            logger.info(f"✅ Success! Resource ID: {post_id}")
            return {
                "success": True,
                "id": post_id,
                "response": data,
                "url": f"https://facebook.com/{post_id}" if post_id else None
            }
            
        except requests.exceptions.Timeout:
            logger.error("Request timed out.")
            return {"success": False, "error": "Timeout"}
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            return {"success": False, "error": str(e)}

if __name__ == "__main__":
    # Test Suite
    print("🤖 Testing Facebook Enterprise Publisher...")
    try:
        fb = FacebookPublisher()
        
        # 1. Test Status
        print("✅ Connection Verified.")
        
        # Uncomment to test actions (Careful: This posts to the live page)
        # res = fb.publish_text_post("🤖 System Upgrade: V2 Online. #Robobot")
        # print(f"Post Result: {res}")
        
    except Exception as e:
        print(f"❌ Initialization Failed: {e}")
