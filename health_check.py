import json
import os
import random
import time
from pathlib import Path
from typing import List, Tuple

import feedparser
import requests
from colorama import Fore, Style, init
from dotenv import dotenv_values
from openai import OpenAI

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
SEEN_POSTS_PATH = BASE_DIR / "data" / "seen_posts.json"
LOG_PATH = BASE_DIR / "bot.log"

REQUIRED_ENV_KEYS = ["TELEGRAM_TOKEN", "GROQ_API_KEY", "CHANNEL_ID", "GROUP_ID"]
CRITICAL_FILES = [
    BASE_DIR / "feeds_config.py",
    SEEN_POSTS_PATH,
    BASE_DIR / "dashboard.py",
]

init(autoreset=True)


def _load_feeds_from_config() -> list[str]:
    config_path = BASE_DIR / "config.json"
    try:
        if not config_path.exists():
            return []
        data = json.loads(config_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return []
        feeds = data.get("feeds")
        if not isinstance(feeds, list):
            return []
        cleaned: list[str] = []
        for item in feeds:
            if isinstance(item, str) and item.strip():
                cleaned.append(item.strip())
        return cleaned
    except Exception:
        return []


def status_line(ok: bool, msg: str) -> str:
    return (
        f"{Fore.GREEN}PASS{Style.RESET_ALL} {msg}"
        if ok
        else f"{Fore.RED}FAIL{Style.RESET_ALL} {msg}"
    )


def check_env() -> Tuple[bool, List[str]]:
    errors: List[str] = []
    if not ENV_PATH.exists():
        errors.append(".env file is missing")
        return False, errors
    data = dotenv_values(str(ENV_PATH))
    for key in REQUIRED_ENV_KEYS:
        if not data.get(key):
            errors.append(f"Missing {key} in .env")
    return len(errors) == 0, errors


def check_files() -> Tuple[bool, List[str]]:
    errors: List[str] = []
    for path in CRITICAL_FILES:
        if path == SEEN_POSTS_PATH and not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("[]", encoding="utf-8")
        if not path.exists():
            errors.append(f"Missing {path.name}")
    return len(errors) == 0, errors


def check_telegram(token: str) -> Tuple[bool, str]:
    url = f"https://api.telegram.org/bot{token}/getMe"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("ok"):
            return False, "Telegram API returned not ok"
        name = data.get("result", {}).get("first_name") or "Unknown"
        return True, f"Bot name: {name}"
    except Exception as exc:  # noqa: BLE001
        return False, f"Telegram check failed: {exc}"


def check_groq(api_key: str) -> Tuple[bool, str]:
    try:
        client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=api_key)
    except Exception as exc:  # noqa: BLE001
        return False, f"Groq client init failed: {exc}"
    try:
        start = time.monotonic()
        raw_models = (os.getenv("GROQ_MODELS") or "").strip()
        env_models: list[str] = []
        if raw_models:
            env_models = [m.strip() for m in raw_models.split(",") if m.strip()]
        else:
            single = (os.getenv("GROQ_MODEL") or "").strip()
            if single:
                env_models = [single]

        model_candidates = [
            *env_models,
            "llama-3.1-70b-versatile",
            "llama-3.1-8b-instant",
        ]
        # De-dup while preserving order
        seen_models: set[str] = set()
        model_candidates = [
            m for m in model_candidates if not (m in seen_models or seen_models.add(m))
        ]
        last_exc: Exception | None = None
        resp = None
        for model_name in model_candidates:
            try:
                resp = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {
                            "role": "system",
                            "content": 'Respond with JSON: {"status": "ready"}',
                        },
                        {"role": "user", "content": "Say 'Ready'"},
                    ],
                    max_tokens=10,
                    temperature=0,
                    response_format={"type": "json_object"},
                )
                break
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                text = str(exc).lower()
                if (
                    "decommissioned" in text
                    or "no longer supported" in text
                    or "not found" in text
                ):
                    continue
                raise
        if resp is None:
            raise last_exc or RuntimeError("Groq request failed")
        elapsed = time.monotonic() - start
        content = resp.choices[0].message.content if resp and resp.choices else ""
        return True, f"Groq responded in {elapsed:.2f}s with: {content}"
    except Exception as exc:  # noqa: BLE001
        return False, f"Groq check failed: {exc}"


def check_rss() -> Tuple[bool, List[str]]:
    errors: List[str] = []
    feeds = _load_feeds_from_config()
    if not feeds:
        try:
            from feeds_config import RSS_FEEDS
        except Exception as exc:  # noqa: BLE001
            return False, [f"Cannot import feeds: {exc}"]
        feeds = list(RSS_FEEDS)

    sample = random.sample(feeds, min(3, len(feeds))) if feeds else []
    if not sample:
        return False, ["No feeds to test"]

    for url in sample:
        try:
            parsed = feedparser.parse(url)
            status = getattr(parsed, "status", None)
            if status and status >= 400:
                errors.append(f"Feed {url} returned status {status}")
                continue
            if parsed.bozo:
                errors.append(f"Feed {url} parse error: {parsed.bozo_exception}")
                continue
            if not parsed.entries:
                errors.append(f"Feed {url} has no entries")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Feed {url} failed: {exc}")
    return len(errors) == 0, errors


def main() -> None:
    print("Running RoboVAI Health Check...\n")

    all_ok = True

    env_ok, env_errors = check_env()
    if env_ok:
        print(status_line(True, "Environment variables present."))
    else:
        all_ok = False
        for err in env_errors:
            print(status_line(False, err))

    files_ok, file_errors = check_files()
    if files_ok:
        print(status_line(True, "Critical files present."))
    else:
        all_ok = False
        for err in file_errors:
            print(status_line(False, err))

    env_data = dotenv_values(str(ENV_PATH)) if env_ok else {}
    token = env_data.get("TELEGRAM_TOKEN") or ""
    groq_key = env_data.get("GROQ_API_KEY") or ""

    if token:
        tg_ok, tg_msg = check_telegram(token)
        all_ok = all_ok and tg_ok
        print(status_line(tg_ok, tg_msg))
    else:
        all_ok = False
        print(status_line(False, "TELEGRAM_TOKEN not set; skipping Telegram check."))

    if groq_key:
        g_ok, g_msg = check_groq(groq_key)
        all_ok = all_ok and g_ok
        print(status_line(g_ok, g_msg))
    else:
        all_ok = False
        print(status_line(False, "GROQ_API_KEY not set; skipping Groq check."))

    rss_ok, rss_errors = check_rss()
    all_ok = all_ok and rss_ok
    if rss_ok:
        print(status_line(True, "RSS feeds reachable (sample)."))
    else:
        for err in rss_errors:
            print(status_line(False, err))

    print()
    if all_ok:
        print(f"{Fore.GREEN}✅ System Ready to Launch{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}❌ Fix Errors Above{Style.RESET_ALL}")


if __name__ == "__main__":
    main()
