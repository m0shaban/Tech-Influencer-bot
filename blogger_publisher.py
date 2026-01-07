"""
Blogger Publisher Module
Handles publishing posts to Blogger using Google Blogger API v3
"""

import os
import requests
from typing import Optional, Dict, Any
from dotenv import load_dotenv
import json

load_dotenv()


class BloggerPublisher:
    """Publisher for posting to Blogger blogs"""

    def __init__(self):
        """Initialize Blogger API client with OAuth credentials"""
        self.api_key = os.getenv("BLOGGER_API_KEY")
        self.blog_id = os.getenv("BLOGGER_BLOG_ID")
        self.access_token = os.getenv("BLOGGER_ACCESS_TOKEN")
        self.refresh_token = os.getenv("BLOGGER_REFRESH_TOKEN")
        self.client_id = os.getenv("BLOGGER_CLIENT_ID")
        self.client_secret = os.getenv("BLOGGER_CLIENT_SECRET")

        self.api_base = "https://www.googleapis.com/blogger/v3"

        if not self.blog_id:
            raise ValueError("BLOGGER_BLOG_ID is required")

        # Use OAuth if available, otherwise fall back to API key
        self.use_oauth = bool(self.access_token or self.refresh_token)

        if not self.use_oauth and not self.api_key:
            raise ValueError("Either OAuth credentials or BLOGGER_API_KEY is required")

    def _refresh_access_token(self) -> bool:
        """Refresh the OAuth access token using refresh token"""
        if not self.refresh_token or not self.client_id or not self.client_secret:
            return False

        try:
            response = requests.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": self.refresh_token,
                    "grant_type": "refresh_token",
                },
            )

            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access_token")
                return True

            return False
        except Exception as e:
            print(f"Failed to refresh access token: {e}")
            return False

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests"""
        headers = {"Content-Type": "application/json"}

        if self.use_oauth and self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"

        return headers

    def _build_html_content(
        self, caption: str, link: Optional[str] = None, image_url: Optional[str] = None
    ) -> str:
        """Build HTML content for blog post"""
        html_parts = []

        # Add image if provided
        if image_url:
            html_parts.append(
                f'<div class="post-image" style="text-align: center; margin: 20px 0;">'
                f'<img src="{image_url}" alt="Post image" style="max-width: 100%; height: auto;" />'
                f"</div>"
            )

        # Add caption as paragraphs
        paragraphs = caption.split("\n")
        for para in paragraphs:
            if para.strip():
                html_parts.append(f"<p>{para.strip()}</p>")

        # Add link if provided and not in caption
        if link and link not in caption:
            html_parts.append(
                f'<p><a href="{link}" target="_blank" rel="noopener">Read more</a></p>'
            )

        return "\n".join(html_parts)

    def publish_post(
        self,
        title: str,
        caption: str,
        link: Optional[str] = None,
        image_url: Optional[str] = None,
        labels: Optional[list] = None,
    ) -> Dict[str, Any]:
        """
        Publish a new post to Blogger

        Args:
            title: Post title
            caption: Post content (will be converted to HTML)
            link: Optional link to include
            image_url: Optional image URL to embed
            labels: Optional list of labels/tags

        Returns:
            dict: Result with success status and message/url
        """
        try:
            # Build HTML content
            html_content = self._build_html_content(caption, link, image_url)

            # Prepare post data
            post_data = {
                "kind": "blogger#post",
                "title": title[:200],  # Blogger title limit
                "content": html_content,
            }

            if labels:
                post_data["labels"] = labels[:20]  # Blogger allows up to 20 labels

            # Build URL with authentication
            url = f"{self.api_base}/blogs/{self.blog_id}/posts"
            params = {}

            if not self.use_oauth and self.api_key:
                params["key"] = self.api_key

            # Attempt to publish
            response = requests.post(
                url,
                params=params,
                headers=self._get_headers(),
                json=post_data,
                timeout=30,
            )

            # If token expired, try refreshing
            if response.status_code == 401 and self.use_oauth:
                if self._refresh_access_token():
                    response = requests.post(
                        url,
                        params=params,
                        headers=self._get_headers(),
                        json=post_data,
                        timeout=30,
                    )

            if response.status_code in [200, 201]:
                post_data = response.json()
                post_url = post_data.get("url", "")

                return {
                    "success": True,
                    "message": "Post published to Blogger successfully",
                    "url": post_url,
                    "post_id": post_data.get("id"),
                }
            else:
                error_msg = response.text
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", error_msg)
                except:
                    pass

                return {
                    "success": False,
                    "message": f"Failed to publish to Blogger: {error_msg}",
                    "status_code": response.status_code,
                }

        except requests.RequestException as e:
            return {
                "success": False,
                "message": f"Network error publishing to Blogger: {str(e)}",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error publishing to Blogger: {str(e)}",
            }

    def test_connection(self) -> Dict[str, Any]:
        """Test Blogger API connection by fetching blog info"""
        try:
            url = f"{self.api_base}/blogs/{self.blog_id}"
            params = {}

            if not self.use_oauth and self.api_key:
                params["key"] = self.api_key

            response = requests.get(
                url, params=params, headers=self._get_headers(), timeout=10
            )

            # Try refreshing token if expired
            if response.status_code == 401 and self.use_oauth:
                if self._refresh_access_token():
                    response = requests.get(
                        url, params=params, headers=self._get_headers(), timeout=10
                    )

            if response.status_code == 200:
                blog_data = response.json()
                blog_name = blog_data.get("name", "Unknown")
                blog_url = blog_data.get("url", "")

                return {
                    "success": True,
                    "message": f"Connected to Blogger: {blog_name}",
                    "blog_url": blog_url,
                }
            else:
                return {
                    "success": False,
                    "message": f"Failed to connect: HTTP {response.status_code}",
                }

        except Exception as e:
            return {"success": False, "message": f"Connection test failed: {str(e)}"}


def main():
    """Test Blogger publisher"""
    try:
        publisher = BloggerPublisher()
        print("Testing Blogger connection...")

        result = publisher.test_connection()
        print(f"Status: {'✓' if result['success'] else '✗'}")
        print(f"Message: {result['message']}")

        if result["success"] and result.get("blog_url"):
            print(f"Blog URL: {result['blog_url']}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
