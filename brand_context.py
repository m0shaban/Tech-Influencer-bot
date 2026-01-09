"""Brand context helpers.

Supports multi-accounts per platform by allowing the active brand to specify an
account suffix per platform. Secrets remain in environment variables.

Convention:
- If brand.accounts["facebook"] == "RBV" then env vars like
  FACEBOOK_PAGE_ID_RBV / FACEBOOK_PAGE_ACCESS_TOKEN_RBV will be used.
- Fallback is the base env var without suffix.

This module is intentionally dependency-free.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional


_BASE_DIR = Path(__file__).parent


def load_runtime_config() -> Dict[str, Any]:
    cfg_path = _BASE_DIR / "config.json"
    if not cfg_path.exists():
        return {}
    try:
        data = json.loads(cfg_path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def get_active_brand(cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    cfg = cfg if isinstance(cfg, dict) else load_runtime_config()
    active_key = str(cfg.get("active_brand") or "").strip()
    brands = cfg.get("brands") if isinstance(cfg.get("brands"), dict) else {}
    brand = brands.get(active_key) if active_key and isinstance(brands, dict) else None
    return brand if isinstance(brand, dict) else {}


def get_brand_accounts(brand: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    brand = brand if isinstance(brand, dict) else get_active_brand()
    raw = brand.get("accounts")
    if not isinstance(raw, dict):
        return {}
    out: Dict[str, str] = {}
    for k, v in raw.items():
        if not isinstance(k, str):
            continue
        if v is None:
            continue
        s = str(v).strip()
        if s:
            out[k.strip().lower()] = s
    return out


def normalize_suffix(s: str) -> str:
    s = (s or "").strip().upper()
    s = re.sub(r"[^A-Z0-9]+", "_", s)
    s = s.strip("_")
    return s


def env_get(
    base_name: str,
    *,
    platform: Optional[str] = None,
    brand: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """Get env var with optional per-platform suffix from active brand.

    Priority:
    1) {base_name}_{SUFFIX} if suffix configured for the given platform
    2) {base_name}
    """

    if platform:
        accounts = get_brand_accounts(brand)
        suffix = normalize_suffix(accounts.get(platform.lower(), ""))
        if suffix:
            v = os.getenv(f"{base_name}_{suffix}")
            if v is not None and str(v).strip() != "":
                return v

    v2 = os.getenv(base_name)
    return v2


def has_env(
    base_name: str,
    *,
    platform: Optional[str] = None,
    brand: Optional[Dict[str, Any]] = None,
) -> bool:
    v = env_get(base_name, platform=platform, brand=brand)
    return bool(v and str(v).strip())
