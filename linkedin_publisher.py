"""
LinkedIn Publisher Module
Handles content publishing to LinkedIn personal profiles and company pages
"""

import os
from typing import Any, Dict, Optional
import requests
from dotenv import load_dotenv

load_dotenv()

LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN")
LINKEDIN_PERSON_URN = os.getenv("LINKEDIN_PERSON_URN")  # e.g., urn:li:person:ABC123
LINKEDIN_COMPANY_URN = os.getenv("LINKEDIN_COMPANY_URN")  # Optional: for company pages


class LinkedInPublisher:
    """Publish content to LinkedIn using the LinkedIn API v2"""

    def __init__(self, access_token: Optional[str] = None):
        self.access_token = access_token or LINKEDIN_ACCESS_TOKEN
        self.base_url = "https://api.linkedin.com/v2"
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        }

    def _get_person_urn(self) -> str:
        """Get the authenticated user's URN in member format (required by LinkedIn API)"""
        if LINKEDIN_PERSON_URN:
            # LinkedIn UGC API requires urn:li:member: format, not urn:li:person:
            if "urn:li:person:" in LINKEDIN_PERSON_URN:
                person_id = LINKEDIN_PERSON_URN.split(":")[-1]
                return f"urn:li:member:{person_id}"
            elif "urn:li:member:" in LINKEDIN_PERSON_URN:
                return LINKEDIN_PERSON_URN
            else:
                # Assume it's just the ID
                return f"urn:li:member:{LINKEDIN_PERSON_URN}"

        raise ValueError("LINKEDIN_PERSON_URN not configured in environment")

    def _format_content(self, caption: str, link: Optional[str] = None) -> str:
        """Format content for LinkedIn"""
        # LinkedIn prefers professional formatting
        content = caption

        # Ensure link is at the end if present
        if link and link not in content:
            content += f"\n\n🔗 {link}"

        # LinkedIn has 3000 char limit for posts
        if len(content) > 3000:
            content = content[:2997] + "..."

        return content

    def publish_text_post(
        self, caption: str, link: Optional[str] = None, visibility: str = "PUBLIC"
    ) -> Dict[str, Any]:
        """
        Publish a text post to LinkedIn using UGC Posts API

        Args:
            caption: Post text content
            link: Optional URL to include
            visibility: PUBLIC or CONNECTIONS

        Returns:
            API response with post ID
        """
        if not self.access_token:
            raise ValueError("LinkedIn access token not configured")

        # For w_member_social scope, use person URN (not company)
        author_urn = self._get_person_urn()
        content = self._format_content(caption, link)

        # Use UGC Posts API
        url = f"{self.base_url}/ugcPosts"

        payload = {
            "author": author_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": content},
                    "shareMediaCategory": "NONE",
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": visibility},
        }

        headers = self.headers.copy()
        headers["LinkedIn-Version"] = "202401"

        response = requests.post(url, json=payload, headers=headers, timeout=10)

        # Debug: print response if error
        if response.status_code >= 400:
            print(f"DEBUG: Status {response.status_code}")
            print(f"DEBUG: Response: {response.text}")
            print(f"DEBUG: Payload: {payload}")

        response.raise_for_status()

        return {
            "status": "success",
            "platform": "linkedin",
            "post_id": response.headers.get("X-RestLi-Id"),
            "response": response.json() if response.content else {},
        }

    def publish_image_post(
        self,
        caption: str,
        image_url: str,
        link: Optional[str] = None,
        visibility: str = "PUBLIC",
    ) -> Dict[str, Any]:
        """
        Publish a post with an image to LinkedIn

        Args:
            caption: Post text content
            image_url: URL of the image to share
            link: Optional article/source URL
            visibility: PUBLIC or CONNECTIONS

        Returns:
            API response with post ID
        """
        if not self.access_token:
            raise ValueError("LinkedIn access token not configured")

        person_urn = self._get_person_urn()
        content = self._format_content(caption, link)

        # Step 1: Register upload
        register_url = f"{self.base_url}/assets?action=registerUpload"
        register_payload = {
            "registerUploadRequest": {
                "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                "owner": person_urn,
                "serviceRelationships": [
                    {
                        "relationshipType": "OWNER",
                        "identifier": "urn:li:userGeneratedContent",
                    }
                ],
            }
        }

        register_response = requests.post(
            register_url, json=register_payload, headers=self.headers, timeout=10
        )
        register_response.raise_for_status()
        register_data = register_response.json()

        asset_id = register_data["value"]["asset"]
        upload_url = register_data["value"]["uploadMechanism"][
            "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"
        ]["uploadUrl"]

        # Step 2: Upload image
        image_response = requests.get(image_url, timeout=10)
        image_response.raise_for_status()

        upload_headers = {"Authorization": f"Bearer {self.access_token}"}
        upload_response = requests.put(
            upload_url, data=image_response.content, headers=upload_headers, timeout=30
        )
        upload_response.raise_for_status()

        # Step 3: Create post with image
        post_url = f"{self.base_url}/ugcPosts"
        post_payload = {
            "author": person_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": content},
                    "shareMediaCategory": "IMAGE",
                    "media": [{"status": "READY", "media": asset_id}],
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": visibility},
        }

        post_response = requests.post(
            post_url, json=post_payload, headers=self.headers, timeout=10
        )
        post_response.raise_for_status()

        return {
            "status": "success",
            "platform": "linkedin",
            "post_id": post_response.headers.get("X-RestLi-Id"),
            "asset_id": asset_id,
            "response": post_response.json(),
        }

    def publish_article(
        self, caption: str, article_url: str, visibility: str = "PUBLIC"
    ) -> Dict[str, Any]:
        """
        Share an article link with preview on LinkedIn

        Args:
            caption: Commentary about the article
            article_url: URL of the article to share
            visibility: PUBLIC or CONNECTIONS

        Returns:
            API response with post ID
        """
        if not self.access_token:
            raise ValueError("LinkedIn access token not configured")

        person_urn = self._get_person_urn()

        # LinkedIn automatically fetches article preview from URL
        url = f"{self.base_url}/ugcPosts"

        payload = {
            "author": person_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": caption},
                    "shareMediaCategory": "ARTICLE",
                    "media": [{"status": "READY", "originalUrl": article_url}],
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": visibility},
        }

        response = requests.post(url, json=payload, headers=self.headers, timeout=10)
        response.raise_for_status()

        return {
            "status": "success",
            "platform": "linkedin",
            "post_id": response.headers.get("X-RestLi-Id"),
            "response": response.json(),
        }


def test_linkedin_connection() -> bool:
    """Test LinkedIn API connection by verifying token validity"""
    try:
        publisher = LinkedInPublisher()
        # Check if we have required credentials (tokens can't be tested without publishing)
        if not publisher.access_token:
            print("[!] LinkedIn: No access token configured")
            return False

        # Verify the token format (should start with AQW or similar)
        if not publisher.access_token.startswith(("AQW", "AQ")):
            print("[!] LinkedIn: Invalid token format")
            return False

        print("[OK] LinkedIn: Token configured and valid format")
        return True
    except Exception as e:
        print(f"[ERROR] LinkedIn connection check failed: {e}")
        return False


if __name__ == "__main__":
    # Quick test
    test_linkedin_connection()
