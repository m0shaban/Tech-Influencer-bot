"""
Dev.to Publisher
Publishes articles to Dev.to platform using their API
https://developers.forem.com/api/v1
"""

import os
import requests
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()


class DevtoPublisher:
    """Publisher for Dev.to platform"""

    def __init__(self):
        self.api_key = os.getenv("DEVTO_API_KEY")
        self.base_url = "https://dev.to/api"

    def is_configured(self) -> bool:
        """Check if Dev.to credentials are configured"""
        return bool(self.api_key)

    def _prepare_content(
        self,
        caption: str,
        title_override: Optional[str] = None,
        link: Optional[str] = None,
        max_length: int = 25000,
    ) -> Dict[str, Any]:
        """Prepare article content for Dev.to"""

        # Extract title from override / first line / default
        if title_override and title_override.strip():
            title = title_override.strip()[:100]
        else:
            lines = caption.strip().split("\n")
            title = lines[0].replace("#", "").strip()[:100] if lines else ""

        if not title:
            title = "مقال تقني جديد من RoboVAI"

        # Build body_markdown
        body = caption.strip()

        # NOTE: DO NOT add source link here - code handles it programmatically
        # The AI is instructed to NOT write sources in the content

        # Trim if needed
        if len(body) > max_length:
            body = body[: max_length - 20] + "\n\n...(يكمل)"

        # Extract tags (look for hashtags)
        tags = []
        import re

        hashtags = re.findall(r"#(\w+)", caption)
        for tag in hashtags[:4]:  # Max 4 tags on Dev.to
            if tag.lower() not in ["robovai"]:
                tags.append(tag.lower())

        # Add default tags if none found
        if not tags:
            tags = ["ai", "tech", "programming", "news"]

        return {
            "title": title,
            "body_markdown": body,
            "published": True,
            "tags": tags[:4],  # Dev.to allows max 4 tags
        }

    def publish(
        self,
        caption: str,
        title: Optional[str] = None,
        link: Optional[str] = None,
        image_url: Optional[str] = None,
        max_length: int = 25000,
    ) -> Dict[str, Any]:
        """
        Publish article to Dev.to

        Args:
            caption: Article content in markdown
            link: Source URL
            image_url: Cover image URL (optional)
            max_length: Maximum content length

        Returns:
            Dict with status and article URL or error
        """

        if not self.is_configured():
            return {
                "success": False,
                "error": "Dev.to API key not configured. Set DEVTO_API_KEY in .env",
            }

        try:
            # Prepare article data
            article_data = self._prepare_content(caption, title, link, max_length)

            # Add cover image if provided
            if image_url:
                article_data["main_image"] = image_url

            # API request
            headers = {"api-key": self.api_key, "Content-Type": "application/json"}

            response = requests.post(
                f"{self.base_url}/articles",
                headers=headers,
                json={"article": article_data},
                timeout=30,
            )

            if response.status_code in [200, 201]:
                data = response.json()
                article_url = data.get("url", "")
                article_id = data.get("id", "")

                return {
                    "success": True,
                    "url": article_url,
                    "id": article_id,
                    "platform": "devto",
                    "message": f"Published to Dev.to: {article_url}",
                }
            else:
                error_msg = response.text
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", error_msg)
                except:
                    pass

                return {
                    "success": False,
                    "error": f"Dev.to API error ({response.status_code}): {error_msg}",
                }

        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "Dev.to API timeout - request took too long",
            }
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Dev.to network error: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": f"Dev.to publish error: {str(e)}"}

    def get_user_info(self) -> Dict[str, Any]:
        """Get authenticated user info"""
        if not self.is_configured():
            return {"error": "API key not configured"}

        try:
            headers = {"api-key": self.api_key}
            response = requests.get(
                f"{self.base_url}/users/me", headers=headers, timeout=10
            )

            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Failed to get user info: {response.status_code}"}

        except Exception as e:
            return {"error": f"Error: {str(e)}"}


# Test function
if __name__ == "__main__":
    publisher = DevtoPublisher()

    print("🔍 Dev.to Publisher Test\n")
    print(f"✅ Configured: {publisher.is_configured()}")

    if publisher.is_configured():
        print("\n📊 Getting user info...")
        user_info = publisher.get_user_info()
        if "error" not in user_info:
            print(f"✅ Username: {user_info.get('username')}")
            print(f"✅ Name: {user_info.get('name')}")
            print(f"✅ Profile: https://dev.to/{user_info.get('username')}")
        else:
            print(f"❌ {user_info.get('error')}")

        print("\n📝 Test publish (set test=True to actually publish):")
        test_caption = """
# 🤖 اختبار نشر على Dev.to من RoboVAI

هذا مقال اختبار من بوت **RoboVAI** - أول بوت ذكاء اصطناعي مصري للمحتوى التقني!

## المميزات:
- ✅ نشر تلقائي على 8+ منصات
- ✅ AI-powered content generation
- ✅ جدولة ذكية
- ✅ تقارير فورية

#AI #Tech #Programming #RoboVAI
"""
        print(f"Title: {test_caption.split(chr(10))[0]}")
        print(f"Length: {len(test_caption)} chars")
    else:
        print("\n⚠️ Set DEVTO_API_KEY in .env to test")
        print("Get your API key from: https://dev.to/settings/extensions")
