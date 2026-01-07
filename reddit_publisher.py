"""
Reddit Publisher Module
Handles publishing posts to Reddit using Reddit API (PRAW-style OAuth)
"""

import os
import requests
from typing import Optional, Dict, Any
from dotenv import load_dotenv
import base64

load_dotenv()


class RedditPublisher:
    """Publisher for posting to Reddit subreddits"""

    def __init__(self):
        """Initialize Reddit API client with OAuth credentials"""
        self.client_id = os.getenv("REDDIT_CLIENT_ID")
        self.client_secret = os.getenv("REDDIT_CLIENT_SECRET")
        self.username = os.getenv("REDDIT_USERNAME")
        self.password = os.getenv("REDDIT_PASSWORD")
        self.user_agent = os.getenv("REDDIT_USER_AGENT", "TechInfluencerBot/1.0")

        if not all([self.client_id, self.client_secret, self.username, self.password]):
            raise ValueError("Reddit credentials are incomplete")

        self.access_token = None
        self.token_type = None
        self._authenticate()

    def _authenticate(self) -> bool:
        """Authenticate with Reddit API and get access token"""
        try:
            # Reddit uses HTTP Basic Auth with client_id:client_secret
            auth_string = f"{self.client_id}:{self.client_secret}"
            auth_bytes = auth_string.encode("utf-8")
            auth_b64 = base64.b64encode(auth_bytes).decode("utf-8")

            headers = {
                "Authorization": f"Basic {auth_b64}",
                "User-Agent": self.user_agent,
            }

            data = {
                "grant_type": "password",
                "username": self.username,
                "password": self.password,
            }

            response = requests.post(
                "https://www.reddit.com/api/v1/access_token",
                headers=headers,
                data=data,
                timeout=10,
            )

            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get("access_token")
                self.token_type = token_data.get("token_type", "bearer")
                return True
            else:
                print(
                    f"Authentication failed: {response.status_code} - {response.text}"
                )
                return False

        except Exception as e:
            print(f"Authentication error: {e}")
            return False

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests"""
        if not self.access_token:
            self._authenticate()

        return {
            "Authorization": f"{self.token_type} {self.access_token}",
            "User-Agent": self.user_agent,
        }

    def submit_link(
        self, subreddit: str, title: str, url: str, send_replies: bool = False
    ) -> Dict[str, Any]:
        """
        Submit a link post to a subreddit

        Args:
            subreddit: Subreddit name (without r/)
            title: Post title (max 300 chars)
            url: Link URL to share
            send_replies: Whether to send reply notifications

        Returns:
            dict: Result with success status and post URL
        """
        try:
            # Prepare submission data
            data = {
                "sr": subreddit,
                "kind": "link",
                "title": title[:300],  # Reddit title limit
                "url": url,
                "sendreplies": send_replies,
                "resubmit": True,  # Allow resubmitting same link
            }

            response = requests.post(
                "https://oauth.reddit.com/api/submit",
                headers=self._get_headers(),
                data=data,
                timeout=30,
            )

            if response.status_code == 200:
                result = response.json()

                # Check for errors in response
                if result.get("json", {}).get("errors"):
                    errors = result["json"]["errors"]
                    return {"success": False, "message": f"Reddit API errors: {errors}"}

                # Extract post URL
                post_data = result.get("json", {}).get("data", {})
                post_url = post_data.get("url", "")
                post_id = post_data.get("id", "")

                return {
                    "success": True,
                    "message": f"Posted to r/{subreddit} successfully",
                    "url": post_url,
                    "post_id": post_id,
                }
            else:
                return {
                    "success": False,
                    "message": f"Failed to post: HTTP {response.status_code}",
                    "details": response.text,
                }

        except requests.RequestException as e:
            return {
                "success": False,
                "message": f"Network error posting to Reddit: {str(e)}",
            }
        except Exception as e:
            return {"success": False, "message": f"Error posting to Reddit: {str(e)}"}

    def submit_text(
        self, subreddit: str, title: str, text: str, send_replies: bool = False
    ) -> Dict[str, Any]:
        """
        Submit a text/self post to a subreddit

        Args:
            subreddit: Subreddit name (without r/)
            title: Post title (max 300 chars)
            text: Post text content (Markdown supported)
            send_replies: Whether to send reply notifications

        Returns:
            dict: Result with success status and post URL
        """
        try:
            data = {
                "sr": subreddit,
                "kind": "self",
                "title": title[:300],
                "text": text,
                "sendreplies": send_replies,
            }

            response = requests.post(
                "https://oauth.reddit.com/api/submit",
                headers=self._get_headers(),
                data=data,
                timeout=30,
            )

            if response.status_code == 200:
                result = response.json()

                if result.get("json", {}).get("errors"):
                    errors = result["json"]["errors"]
                    return {"success": False, "message": f"Reddit API errors: {errors}"}

                post_data = result.get("json", {}).get("data", {})
                post_url = post_data.get("url", "")
                post_id = post_data.get("id", "")

                return {
                    "success": True,
                    "message": f"Posted to r/{subreddit} successfully",
                    "url": post_url,
                    "post_id": post_id,
                }
            else:
                return {
                    "success": False,
                    "message": f"Failed to post: HTTP {response.status_code}",
                    "details": response.text,
                }

        except requests.RequestException as e:
            return {
                "success": False,
                "message": f"Network error posting to Reddit: {str(e)}",
            }
        except Exception as e:
            return {"success": False, "message": f"Error posting to Reddit: {str(e)}"}

    def test_connection(self) -> Dict[str, Any]:
        """Test Reddit API connection by fetching user info"""
        try:
            response = requests.get(
                "https://oauth.reddit.com/api/v1/me",
                headers=self._get_headers(),
                timeout=10,
            )

            if response.status_code == 200:
                user_data = response.json()
                username = user_data.get("name", "Unknown")
                karma = user_data.get("total_karma", 0)

                return {
                    "success": True,
                    "message": f"Connected to Reddit as u/{username}",
                    "username": username,
                    "karma": karma,
                }
            else:
                return {
                    "success": False,
                    "message": f"Connection failed: HTTP {response.status_code}",
                }

        except Exception as e:
            return {"success": False, "message": f"Connection test failed: {str(e)}"}


def main():
    """Test Reddit publisher"""
    try:
        publisher = RedditPublisher()
        print("Testing Reddit connection...")

        result = publisher.test_connection()
        print(f"Status: {'✓' if result['success'] else '✗'}")
        print(f"Message: {result['message']}")

        if result["success"]:
            print(f"Username: u/{result.get('username')}")
            print(f"Karma: {result.get('karma')}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
