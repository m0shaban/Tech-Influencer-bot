"""
Facebook Publisher Module
Handles publishing posts to Facebook Pages using Graph API
"""

import os
import requests
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()


class FacebookPublisher:
    """Publisher for posting to Facebook Pages"""

    def __init__(self):
        """Initialize Facebook Graph API client"""
        self.access_token = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
        self.page_id = os.getenv("FACEBOOK_PAGE_ID")

        if not self.access_token:
            raise ValueError("FACEBOOK_PAGE_ACCESS_TOKEN is required")
        if not self.page_id:
            raise ValueError("FACEBOOK_PAGE_ID is required")

        self.api_base = "https://graph.facebook.com/v18.0"

    def _get_params(self) -> Dict[str, str]:
        """Get common parameters for API requests"""
        return {"access_token": self.access_token}

    def publish_link(self, message: str, link: str) -> Dict[str, Any]:
        """
        Publish a link post to Facebook Page

        Args:
            message: Post text content
            link: URL to share

        Returns:
            dict: Result with success status and post ID/URL
        """
        try:
            url = f"{self.api_base}/{self.page_id}/feed"

            data = {"message": message, "link": link, "access_token": self.access_token}

            response = requests.post(url, data=data, timeout=30)

            if response.status_code == 200:
                result = response.json()
                post_id = result.get("id", "")

                # Construct post URL
                post_url = f"https://www.facebook.com/{post_id.replace('_', '/posts/')}"

                return {
                    "success": True,
                    "message": "Posted to Facebook successfully",
                    "post_id": post_id,
                    "url": post_url,
                }
            else:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", response.text)

                return {
                    "success": False,
                    "message": f"Failed to post to Facebook: {error_msg}",
                    "status_code": response.status_code,
                }

        except requests.RequestException as e:
            return {
                "success": False,
                "message": f"Network error posting to Facebook: {str(e)}",
            }
        except Exception as e:
            return {"success": False, "message": f"Error posting to Facebook: {str(e)}"}

    def publish_text(self, message: str) -> Dict[str, Any]:
        """
        Publish a text-only post to Facebook Page

        Args:
            message: Post text content

        Returns:
            dict: Result with success status and post ID/URL
        """
        try:
            url = f"{self.api_base}/{self.page_id}/feed"

            data = {"message": message, "access_token": self.access_token}

            response = requests.post(url, data=data, timeout=30)

            if response.status_code == 200:
                result = response.json()
                post_id = result.get("id", "")

                post_url = f"https://www.facebook.com/{post_id.replace('_', '/posts/')}"

                return {
                    "success": True,
                    "message": "Posted to Facebook successfully",
                    "post_id": post_id,
                    "url": post_url,
                }
            else:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", response.text)

                return {
                    "success": False,
                    "message": f"Failed to post to Facebook: {error_msg}",
                    "status_code": response.status_code,
                }

        except requests.RequestException as e:
            return {
                "success": False,
                "message": f"Network error posting to Facebook: {str(e)}",
            }
        except Exception as e:
            return {"success": False, "message": f"Error posting to Facebook: {str(e)}"}

    def publish_photo(
        self,
        message: str,
        image_url: Optional[str] = None,
        image_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Publish a photo post to Facebook Page

        Args:
            message: Post caption/text
            image_url: URL of the image to post
            image_path: Local filesystem path to image

        Returns:
            dict: Result with success status and post ID
        """
        try:
            url = f"{self.api_base}/{self.page_id}/photos"

            data = {
                "caption": message,
                "access_token": self.access_token,
            }
            files = {}

            response = None
            local_attempted = False

            # Prefer local file upload if available (more reliable)
            if image_path and os.path.exists(image_path):
                local_attempted = True
                with open(image_path, "rb") as img_file:
                    files = {"source": img_file}
                    response = requests.post(url, data=data, files=files, timeout=60)

                # If local upload fails and we have a URL, try URL upload as fallback
                if response is not None and response.status_code != 200 and image_url:
                    data2 = dict(data)
                    data2["url"] = image_url
                    response = requests.post(url, data=data2, timeout=60)

            elif image_url:
                data["url"] = image_url
                response = requests.post(url, data=data, timeout=60)
            else:
                return {
                    "success": False,
                    "message": "No image provided (url or path required)",
                }

            if response is None:
                return {
                    "success": False,
                    "message": "Failed to prepare Facebook photo request",
                }

            if response.status_code == 200:
                result = response.json()
                post_id = result.get("post_id", "")
                photo_id = result.get("id", "")

                # Construct post URL
                post_url = (
                    f"https://www.facebook.com/{post_id.replace('_', '/posts/')}"
                    if post_id
                    else ""
                )

                return {
                    "success": True,
                    "message": "Posted photo to Facebook successfully",
                    "post_id": post_id,
                    "photo_id": photo_id,
                    "url": post_url,
                }
            else:
                try:
                    error_data = response.json()
                except Exception:
                    error_data = {}
                err = error_data.get("error", {}) if isinstance(error_data, dict) else {}
                error_msg = err.get("message") or response.text
                extra = {
                    "fb_code": err.get("code"),
                    "fb_subcode": err.get("error_subcode"),
                    "fb_type": err.get("type"),
                    "fb_trace_id": err.get("fbtrace_id"),
                    "local_upload_attempted": local_attempted,
                }

                return {
                    "success": False,
                    "message": f"Failed to post photo to Facebook: {error_msg}",
                    "status_code": response.status_code,
                    "details": extra,
                }

        except requests.RequestException as e:
            return {
                "success": False,
                "message": f"Network error posting photo to Facebook: {str(e)}",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error posting photo to Facebook: {str(e)}",
            }

    def test_connection(self) -> Dict[str, Any]:
        """Test Facebook API connection by fetching page info"""
        try:
            url = f"{self.api_base}/{self.page_id}"
            params = {
                "fields": "name,username,followers_count",
                "access_token": self.access_token,
            }

            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                page_data = response.json()
                page_name = page_data.get("name", "Unknown")
                username = page_data.get("username", "")
                followers = page_data.get("followers_count", 0)

                return {
                    "success": True,
                    "message": f"Connected to Facebook Page: {page_name}",
                    "page_name": page_name,
                    "username": username,
                    "followers": followers,
                }
            else:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", response.text)

                return {"success": False, "message": f"Connection failed: {error_msg}"}

        except Exception as e:
            return {"success": False, "message": f"Connection test failed: {str(e)}"}


def main():
    """Test Facebook publisher"""
    try:
        publisher = FacebookPublisher()
        print("Testing Facebook connection...")

        result = publisher.test_connection()
        print(f"Status: {'✓' if result['success'] else '✗'}")
        print(f"Message: {result['message']}")

        if result["success"]:
            print(f"Page: {result.get('page_name')}")
            if result.get("username"):
                print(f"Username: @{result.get('username')}")
            print(f"Followers: {result.get('followers', 0):,}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
