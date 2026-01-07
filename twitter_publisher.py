"""
Twitter/X Publisher Module
Post tweets with text, links, and images using Twitter API v2
"""

from typing import Any, Dict, Optional
import os
import requests
from requests_oauthlib import OAuth1
from dotenv import load_dotenv

load_dotenv()

TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_SECRET = os.getenv("TWITTER_ACCESS_SECRET")


class TwitterPublisher:
    """Publish tweets to X/Twitter using API v2"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        access_token: Optional[str] = None,
        access_secret: Optional[str] = None,
    ):
        self.api_key = api_key or TWITTER_API_KEY
        self.api_secret = api_secret or TWITTER_API_SECRET
        self.access_token = access_token or TWITTER_ACCESS_TOKEN
        self.access_secret = access_secret or TWITTER_ACCESS_SECRET

        if not all(
            [self.api_key, self.api_secret, self.access_token, self.access_secret]
        ):
            raise ValueError("Twitter OAuth 1.0a credentials not fully configured")

        self.auth = OAuth1(
            self.api_key,
            client_secret=self.api_secret,
            resource_owner_key=self.access_token,
            resource_owner_secret=self.access_secret,
        )

    def _upload_media(self, image_url: str) -> Optional[str]:
        """Upload image to Twitter and return media_id"""
        try:
            # Download image
            img_response = requests.get(image_url, timeout=10)
            img_response.raise_for_status()

            # Upload to Twitter (v1.1 media endpoint)
            upload_url = "https://upload.twitter.com/1.1/media/upload.json"
            files = {"media": img_response.content}

            response = requests.post(
                upload_url, files=files, auth=self.auth, timeout=30
            )
            response.raise_for_status()

            data = response.json()
            return data.get("media_id_string")
        except Exception as e:
            print(f"[!] Twitter media upload failed: {e}")
            return None

    def publish_tweet(
        self,
        text: str,
        image_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Post a tweet with optional image

        Args:
            text: Tweet text (max 280 chars, will be truncated if longer)
            image_url: Optional image URL to attach

        Returns:
            API response with tweet ID
        """
        # Truncate text if needed (Twitter limit is 280 chars)
        if len(text) > 280:
            text = text[:277] + "..."

        # Build tweet payload
        payload: Dict[str, Any] = {"text": text}

        # Upload media if provided
        if image_url:
            media_id = self._upload_media(image_url)
            if media_id:
                payload["media"] = {"media_ids": [media_id]}

        # Post tweet (API v2)
        url = "https://api.twitter.com/2/tweets"
        response = requests.post(url, json=payload, auth=self.auth, timeout=10)

        if response.status_code >= 400:
            print(f"[DEBUG] Twitter API error: {response.status_code}")
            print(f"[DEBUG] Response: {response.text}")

        response.raise_for_status()

        result = response.json()
        tweet_data = result.get("data", {})

        return {
            "status": "success",
            "platform": "twitter",
            "tweet_id": tweet_data.get("id"),
            "response": result,
        }


def test_twitter_connection() -> bool:
    """Test Twitter API credentials"""
    if not all(
        [
            TWITTER_API_KEY,
            TWITTER_API_SECRET,
            TWITTER_ACCESS_TOKEN,
            TWITTER_ACCESS_SECRET,
        ]
    ):
        print("[!] Twitter: Credentials not fully configured")
        return False

    try:
        publisher = TwitterPublisher()
        # Verify credentials by fetching user info (API v2)
        url = "https://api.twitter.com/2/users/me"
        response = requests.get(url, auth=publisher.auth, timeout=10)

        if response.status_code == 200:
            data = response.json()
            username = data.get("data", {}).get("username", "Unknown")
            print(f"[OK] Twitter: Connected as @{username}")
            return True
        else:
            print(f"[!] Twitter: Auth failed ({response.status_code})")
            return False
    except Exception as e:
        print(f"[!] Twitter: Connection test failed: {e}")
        return False


if __name__ == "__main__":
    # Quick test
    test_twitter_connection()
