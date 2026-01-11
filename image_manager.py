"""image_manager.py

Centralized image selection + ImgBB upload.

Goal:
- Always return a stable, Telegram-friendly image URL.
- Prefer og:image from the source URL.
- Fall back to project image generator.
- Upload everything to ImgBB when configured to avoid hotlinking issues.

Public API:
- get_best_image(query, source_url, brand_key=None) -> dict

Returned dict keys:
- url: str | None
- source: str (og|generator|fallback|none)
- uploaded_to_imgbb: bool
- error: str | None
"""

from __future__ import annotations

import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import urljoin

from dotenv import load_dotenv


# Load env early so IMGBB_API_KEY is available in all entrypoints
_BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=_BASE_DIR / ".env")


_DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def _safe_print(msg: str) -> None:
    try:
        print(msg)
    except Exception:
        pass


def _is_url(value: str) -> bool:
    v = (value or "").strip().lower()
    return v.startswith("http://") or v.startswith("https://")


def _guess_ext_from_url(url: str) -> str:
    u = (url or "").split("?")[0].split("#")[0]
    m = re.search(r"\.(png|jpg|jpeg|webp|gif)$", u, re.IGNORECASE)
    if m:
        ext = m.group(1).lower()
        return ".jpg" if ext == "jpeg" else f".{ext}"
    return ".jpg"


def _guess_ext_from_content_type(ct: str) -> str:
    c = (ct or "").lower()
    if "png" in c:
        return ".png"
    if "webp" in c:
        return ".webp"
    if "gif" in c:
        return ".gif"
    if "jpeg" in c or "jpg" in c:
        return ".jpg"
    return ".jpg"


def _extract_og_image(source_url: str) -> Optional[str]:
    if not _is_url(source_url):
        return None

    try:
        import requests

        resp = requests.get(
            source_url,
            headers={"User-Agent": _DEFAULT_UA},
            timeout=10,
        )
        resp.raise_for_status()
        html = resp.text or ""

        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "html.parser")
            meta = soup.find("meta", attrs={"property": "og:image"})
            if not meta:
                meta = soup.find("meta", attrs={"name": "og:image"})
            if meta and meta.get("content"):
                img = str(meta.get("content") or "").strip()
                if img:
                    return urljoin(source_url, img)
        except Exception:
            # If bs4 isn't available or parsing fails, fall back to regex
            m = re.search(
                r"<meta[^>]+property=['\"]og:image['\"][^>]+content=['\"]([^'\"]+)['\"]",
                html,
                flags=re.IGNORECASE,
            )
            if m:
                img = (m.group(1) or "").strip()
                if img:
                    return urljoin(source_url, img)

    except Exception:
        return None

    return None


def _download_to_temp(url: str) -> Optional[Path]:
    if not _is_url(url):
        return None

    try:
        import requests

        resp = requests.get(url, headers={"User-Agent": _DEFAULT_UA}, timeout=20)
        resp.raise_for_status()

        ext = _guess_ext_from_content_type(resp.headers.get("content-type", ""))
        if ext == ".jpg":
            ext = _guess_ext_from_url(url) or ".jpg"

        fd, tmp_path = tempfile.mkstemp(prefix="robovai_img_", suffix=ext)
        os.close(fd)
        p = Path(tmp_path)
        p.write_bytes(resp.content)
        return p
    except Exception:
        return None


def _upload_local_to_imgbb(local_path: Path) -> Optional[str]:
    try:
        from r2_uploader import imgbb_is_configured, upload_file_to_imgbb

        if not imgbb_is_configured():
            return None
        return upload_file_to_imgbb(str(local_path))
    except Exception:
        return None


def _ensure_public_imgbb_url(candidate: str) -> tuple[Optional[str], bool]:
    """Return (url, uploaded). Always tries to return ImgBB URL when possible."""
    c = (candidate or "").strip()
    if not c:
        return None, False

    # Already ImgBB
    if "imgbb.com" in c or "ibb.co" in c:
        return c, False

    # Local file
    try:
        p = Path(c)
        if p.exists() and p.is_file():
            url = _upload_local_to_imgbb(p)
            return (url or c), bool(url)
    except Exception:
        pass

    # Remote URL
    if _is_url(c):
        tmp = _download_to_temp(c)
        if tmp:
            try:
                url = _upload_local_to_imgbb(tmp)
                return (url or c), bool(url)
            finally:
                try:
                    tmp.unlink(missing_ok=True)
                except Exception:
                    pass

    return c, False


def _fallback_per_brand(brand_key: Optional[str]) -> Optional[str]:
    """Optional: You can pin a per-brand fallback image via env vars."""
    key = (brand_key or "").strip().upper()
    if not key:
        return None

    env_name = f"FALLBACK_IMAGE_URL_{key}"
    url = (os.getenv(env_name, "") or "").strip()
    return url if _is_url(url) else None


def get_best_image(
    query: str,
    source_url: str | None = None,
    *,
    brand_key: str | None = None,
) -> Dict[str, Any]:
    """Best-effort image resolver.

    Priority:
    1) og:image from source_url
    2) project image generator strategy (image_generator.get_article_image)
    3) optional per-brand fallback env

    Always tries to upload to ImgBB when configured.
    """

    q = (query or "").strip()
    src = (source_url or "").strip()

    # 1) OG image
    og = _extract_og_image(src) if src else None
    if og:
        url, uploaded = _ensure_public_imgbb_url(og)
        return {
            "url": url,
            "source": "og",
            "uploaded_to_imgbb": uploaded,
            "error": None,
        }

    # 2) Generator strategy
    try:
        from image_generator import get_article_image

        gen = get_article_image(q or "RoboVAI", src or None)
        if isinstance(gen, dict):
            cand = (gen.get("public_url") or gen.get("local_path") or "").strip()
            if cand:
                url, uploaded = _ensure_public_imgbb_url(cand)
                return {
                    "url": url,
                    "source": "generator",
                    "uploaded_to_imgbb": uploaded,
                    "error": None,
                }
    except Exception as e:
        _safe_print(f"[image_manager] generator failed: {e}")

    # 3) Per-brand fallback
    fb = _fallback_per_brand(brand_key)
    if fb:
        url, uploaded = _ensure_public_imgbb_url(fb)
        return {
            "url": url,
            "source": "fallback",
            "uploaded_to_imgbb": uploaded,
            "error": None,
        }

    # 4) Last-resort: generate OG with no source
    try:
        from image_generator import get_article_image

        gen2 = get_article_image(q or "RoboVAI", None)
        if isinstance(gen2, dict):
            cand2 = (gen2.get("public_url") or gen2.get("local_path") or "").strip()
            if cand2:
                url, uploaded = _ensure_public_imgbb_url(cand2)
                return {
                    "url": url,
                    "source": "generator",
                    "uploaded_to_imgbb": uploaded,
                    "error": None,
                }
    except Exception as e:
        _safe_print(f"[image_manager] last-resort generator failed: {e}")

    # 5) Ultimate fallback: generate a simple placeholder image (requires PIL)
    try:
        from PIL import Image

        fd, tmp_path = tempfile.mkstemp(prefix="robovai_placeholder_", suffix=".png")
        os.close(fd)
        p = Path(tmp_path)

        img = Image.new("RGB", (1200, 630), color=(18, 24, 38))
        img.save(p, format="PNG")

        url = _upload_local_to_imgbb(p)
        try:
            p.unlink(missing_ok=True)
        except Exception:
            pass

        if url:
            return {
                "url": url,
                "source": "fallback",
                "uploaded_to_imgbb": True,
                "error": None,
            }
    except Exception as e:
        _safe_print(f"[image_manager] placeholder fallback failed: {e}")

    return {
        "url": None,
        "source": "none",
        "uploaded_to_imgbb": False,
        "error": "no_image",
    }
