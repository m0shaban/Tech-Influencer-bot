import json
import random
import re
from html import unescape
from pathlib import Path
from typing import Any, Dict, Optional

import feedparser
import requests
from bs4 import BeautifulSoup

from feeds_config import RSS_FEEDS

BASE_DIR = Path(__file__).resolve().parent
SEEN_POSTS_PATH = BASE_DIR / "data" / "seen_posts.json"
CONFIG_PATH = BASE_DIR / "config.json"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
HTTP_HEADERS = {"User-Agent": USER_AGENT}
REQUEST_TIMEOUT_SECONDS = 5


def extract_image_from_html(html_content: str | None) -> Optional[str]:
    if not html_content:
        return None
    try:
        soup = BeautifulSoup(unescape(str(html_content)), "html.parser")
        img = soup.find("img")
        if img and img.get("src"):
            return str(img.get("src")).strip()
        return None
    except Exception:
        return None


def _extract_image(entry: Dict[str, Any]) -> Optional[str]:
    # Priority 1: media_content URL
    media_content = entry.get("media_content") or []
    if media_content:
        url = media_content[0].get("url")
        if url:
            return url

    # Priority 2: links with image type
    links = entry.get("links") or []
    for link in links:
        link_type = (link.get("type") or "").lower()
        if "image" in link_type:
            url = link.get("href") or link.get("url")
            if url:
                return url

    # Optional: common RSS image containers
    enclosure = entry.get("enclosures") or entry.get("enclosure")
    if enclosure:
        if isinstance(enclosure, list):
            for item in enclosure:
                url = item.get("href") or item.get("url")
                if url:
                    return url
        elif isinstance(enclosure, dict):
            url = enclosure.get("href") or enclosure.get("url")
            if url:
                return url

    thumb = entry.get("media_thumbnail") or []
    if thumb:
        url = thumb[0].get("url")
        if url:
            return url

    # Priority 3: parse HTML from content
    content_list = entry.get("content") or []
    if isinstance(content_list, list) and content_list:
        content_html = content_list[0].get("value")
        img = extract_image_from_html(content_html)
        if img:
            return img

    # Priority 4: parse HTML from summary
    summary_html = entry.get("summary")
    img = extract_image_from_html(summary_html)
    if img:
        return img

    return None


def _ensure_seen_posts_file() -> None:
    SEEN_POSTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not SEEN_POSTS_PATH.exists():
        SEEN_POSTS_PATH.write_text("[]", encoding="utf-8")


def _read_seen_posts() -> set[str]:
    _ensure_seen_posts_file()
    try:
        data = json.loads(SEEN_POSTS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        data = []
    if not isinstance(data, list):
        data = []
    return {str(item) for item in data}


def _write_seen_posts(seen: set[str]) -> None:
    SEEN_POSTS_PATH.write_text(json.dumps(sorted(seen)), encoding="utf-8")


def _load_feeds_from_config() -> list[str]:
    try:
        if not CONFIG_PATH.exists():
            return []
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return []
        feeds = data.get("feeds")
        if not isinstance(feeds, list):
            return []
        cleaned: list[str] = []
        for item in feeds:
            if not isinstance(item, str):
                continue
            url = item.strip()
            if url:
                cleaned.append(url)
        return cleaned
    except Exception:
        return []


def fetch_random_new_post() -> Optional[Dict[str, Any]]:
    feeds = _load_feeds_from_config() or list(RSS_FEEDS)
    random.shuffle(feeds)
    seen = _read_seen_posts()

    for feed_url in feeds:
        try:
            response = requests.get(
                feed_url, headers=HTTP_HEADERS, timeout=REQUEST_TIMEOUT_SECONDS
            )
            response.raise_for_status()
            parsed = feedparser.parse(response.content)
            entries = parsed.entries or []
            if not entries:
                continue

            latest = entries[0]
            link = latest.get("link")
            if not isinstance(link, str):
                continue
            link = link.strip()
            if not link:
                continue
            if link in seen:
                continue

            seen.add(link)
            _write_seen_posts(seen)

            title = latest.get("title", "")
            image_url = _extract_image(latest)
            
            # Use advanced image strategy if no image found
            image_local_path = None
            if not image_url:
                try:
                    from image_generator import get_article_image
                    image_result = get_article_image(title, link)
                    if image_result:
                        # Prefer public URL for cross-platform compatibility
                        image_url = image_result.get("public_url") or image_result.get("local_path")
                        image_local_path = image_result.get("local_path")
                except Exception as e:
                    print(f"⚠️ Image generation failed: {e}")

            return {
                "title": title,
                "link": link,
                "summary": latest.get("summary", ""),
                "published": latest.get("published", ""),
                "source": feed_url,
                "image": image_url,
                "image_local_path": image_local_path,  # For Telegram
            }
        except Exception:
            continue

    return None
