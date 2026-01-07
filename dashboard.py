import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import streamlit as st
from dotenv import load_dotenv
from filelock import FileLock
from telegram import Bot

load_dotenv()

# Paths
BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"
CONFIG_LOCK_PATH = CONFIG_PATH.with_suffix(".lock")
FEEDS_CONFIG_PATH = BASE_DIR / "feeds_config.py"
LOG_PATH = BASE_DIR / "bot.log"

# Env
DEFAULT_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "")
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
GROUP_ID = os.getenv("GROUP_ID")

# Defaults
DEFAULT_CONFIG: Dict[str, Any] = {
    "status": "active",
    "force_fetch": False,
    "system_prompt": "",
    "model": "llama-3.3-70b-versatile",
    "feeds": [],
    "last_run": None,
}

# ------------- Helpers -------------


def _ensure_config() -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    lock = FileLock(str(CONFIG_LOCK_PATH), timeout=5)
    with lock:
        if not CONFIG_PATH.exists():
            CONFIG_PATH.write_text(
                json.dumps(DEFAULT_CONFIG, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )


def load_config() -> Dict[str, Any]:
    _ensure_config()
    lock = FileLock(str(CONFIG_LOCK_PATH), timeout=5)
    with lock:
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = DEFAULT_CONFIG.copy()
    for k, v in DEFAULT_CONFIG.items():
        data.setdefault(k, v)
    return data


def save_config(data: Dict[str, Any]) -> None:
    lock = FileLock(str(CONFIG_LOCK_PATH), timeout=5)
    with lock:
        CONFIG_PATH.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )


def load_feeds_from_code() -> List[str]:
    try:
        from feeds_config import RSS_FEEDS

        return list(RSS_FEEDS)
    except Exception:
        return []


def write_feeds_to_code(feeds: List[str]) -> None:
    FEEDS_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    content = "RSS_FEEDS = [\n" + "\n".join(f"    '{f}'," for f in feeds) + "\n]\n"
    FEEDS_CONFIG_PATH.write_text(content, encoding="utf-8")


def tail_log(path: Path, lines: int = 50) -> List[str]:
    if not path.exists():
        return ["No logs yet."]
    buffer: List[str] = []
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                buffer.append(line.rstrip())
        return buffer[-lines:] if buffer else ["Log empty."]
    except OSError:
        return ["Could not read log file."]


def extract_last_run() -> Optional[str]:
    if not LOG_PATH.exists():
        return None
    try:
        lines = tail_log(LOG_PATH, 200)
        for line in reversed(lines):
            if "Published" in line:
                try:
                    ts = line.split("|")[0].strip()
                    return ts
                except Exception:
                    return line
    except Exception:
        return None
    return None


def send_text(chat_id: str, text: str) -> str:
    if not BOT_TOKEN:
        return "Missing TELEGRAM_TOKEN"
    try:
        asyncio.run(Bot(token=BOT_TOKEN).send_message(chat_id=chat_id, text=text))
        return "Sent"
    except Exception as exc:  # noqa: BLE001
        return f"{exc}"


def send_photo(chat_id: str, photo: bytes, caption: str) -> str:
    if not BOT_TOKEN:
        return "Missing TELEGRAM_TOKEN"
    try:
        asyncio.run(
            Bot(token=BOT_TOKEN).send_photo(
                chat_id=chat_id, photo=photo, caption=caption
            )
        )
        return "Sent"
    except Exception as exc:  # noqa: BLE001
        return f"{exc}"


# ------------- UI Setup -------------
st.set_page_config(page_title="RoboVAI CEO Dashboard", page_icon="💼", layout="wide")

# Password gate
if DEFAULT_PASSWORD:
    pwd = st.sidebar.text_input("🔐 Enter Dashboard Password", type="password")
    if pwd != DEFAULT_PASSWORD:
        st.error("❌ Access denied")
        st.stop()

# Sidebar menu
try:
    from streamlit_option_menu import option_menu
except Exception:
    option_menu = None

with st.sidebar:
    st.title("💼 RoboVAI CEO")
    st.caption("Command Center")
    menu_choice = (
        option_menu(
            "Navigation",
            [
                "🏠 The Cockpit",
                "🧠 AI Brain Surgery",
                "🔗 Feed Manager",
                "📜 Live Terminal",
                "📢 Manual Broadcast",
            ],
            icons=["house", "cpu", "link", "terminal", "megaphone"],
            menu_icon="list",
            default_index=0,
        )
        if option_menu
        else st.radio(
            "Navigation",
            (
                "🏠 The Cockpit",
                "🧠 AI Brain Surgery",
                "🔗 Feed Manager",
                "📜 Live Terminal",
                "📢 Manual Broadcast",
            ),
        )
    )

config = load_config()
feeds_list = config.get("feeds") or load_feeds_from_code()
config["feeds"] = feeds_list
save_config(config)

# Shared metrics
is_active = config.get("status", "paused") == "active"
feeds_count = len(feeds_list)
last_run = extract_last_run() or "(n/a)"
status_label = "Online" if is_active else "Offline"
status_color = "🟢" if is_active else "🔴"


# ------------- Cockpit -------------
if menu_choice == "🏠 The Cockpit":
    st.title("The Cockpit")
    st.caption("High-level overview and master controls")

    c1, c2, c3 = st.columns(3)
    c1.metric("Status", f"{status_color} {status_label}")
    c2.metric("Active Feeds", feeds_count)
    c3.metric("Last Run", last_run)

    st.markdown("---")
    colA, colB = st.columns([2, 1])
    with colA:
        toggle_val = st.toggle(
            "Bot Active",
            value=is_active,
            help="Toggle active/paused status in config.json",
        )
        config["status"] = "active" if toggle_val else "paused"
        save_config(config)
    with colB:
        if st.button("Trigger Force Fetch", use_container_width=True):
            config["force_fetch"] = True
            save_config(config)
            st.success("Flag set. Bot will fetch next cycle.")

    st.markdown("---")
    st.subheader("Latest Logs (50 lines)")
    log_placeholder = st.empty()
    logs = tail_log(LOG_PATH, 50)
    log_placeholder.code("\n".join(logs), language="")
    if st.button("Refresh Logs", use_container_width=True):
        logs = tail_log(LOG_PATH, 50)
        log_placeholder.code("\n".join(logs), language="")


# ------------- AI Brain -------------
elif menu_choice == "🧠 AI Brain Surgery":
    st.title("AI Brain Surgery")
    st.caption("Edit the AI persona and model")

    system_prompt = st.text_area(
        "System Prompt",
        value=config.get("system_prompt", ""),
        height=320,
    )

    model_choice = st.selectbox(
        "Model",
        [
            "llama-3.3-70b-versatile",
            "llama-3.1-70b-versatile",
            "llama-3.1-8b-instant",
            "meta-llama/llama-4-scout-17b-16e-instruct",
        ],
        index=0,
    )

    if st.button("Save Configuration", type="primary"):
        config["system_prompt"] = system_prompt
        config["model"] = model_choice
        save_config(config)
        st.success("Saved persona & model")


# ------------- Feed Manager -------------
elif menu_choice == "🔗 Feed Manager":
    st.title("Feed Manager")
    st.caption("Edit RSS feeds")

    feeds = config.get("feeds", [])
    editable_rows = [{"url": f} for f in feeds]
    edited = st.data_editor(
        editable_rows,
        key="feeds-editor",
        num_rows="dynamic",
        column_config={"url": st.column_config.TextColumn("Feed URL", width="large")},
    )

    if st.button("Save Feeds", type="primary", use_container_width=True):
        new_feeds = [row.get("url", "").strip() for row in edited if row.get("url")]
        # de-dup while preserving order
        seen = set()
        cleaned = []
        for f in new_feeds:
            if f not in seen:
                cleaned.append(f)
                seen.add(f)
        config["feeds"] = cleaned
        save_config(config)
        try:
            write_feeds_to_code(cleaned)
        except Exception as exc:  # noqa: BLE001
            st.error(f"Saved config, but failed to write feeds_config.py: {exc}")
        else:
            st.success(f"Saved {len(cleaned)} feeds and updated feeds_config.py")

    st.markdown("---")
    if st.button("Reload from feeds_config.py", use_container_width=True):
        feeds_from_code = load_feeds_from_code()
        config["feeds"] = feeds_from_code
        save_config(config)
        st.success(f"Loaded {len(feeds_from_code)} feeds from code")
        st.experimental_rerun()


# ------------- Live Terminal -------------
elif menu_choice == "📜 Live Terminal":
    st.title("Live Terminal")
    st.caption("Tail 50 lines from bot.log")

    log_placeholder = st.empty()
    logs = tail_log(LOG_PATH, 50)
    log_placeholder.code("\n".join(logs), language="")
    if st.button("Refresh", use_container_width=True):
        logs = tail_log(LOG_PATH, 50)
        log_placeholder.code("\n".join(logs), language="")


# ------------- Manual Broadcast -------------
elif menu_choice == "📢 Manual Broadcast":
    st.title("Manual Broadcast")
    st.caption("Send an urgent channel/group blast")

    target = st.radio("Destination", ["Channel", "Group", "Both"], horizontal=True)
    text_msg = st.text_area("Message", height=200)
    uploaded = st.file_uploader("Optional Image", type=["png", "jpg", "jpeg", "webp"])

    def _send_to(chat_id: Optional[str]) -> str:
        if not chat_id:
            return "Missing chat_id"
        if uploaded:
            return send_photo(chat_id, uploaded.read(), text_msg or "")
        return send_text(chat_id, text_msg or "")

    if st.button("Send", type="primary", use_container_width=True):
        results: List[str] = []
        if target in ("Channel", "Both"):
            results.append(_send_to(CHANNEL_ID))
        if target in ("Group", "Both"):
            results.append(_send_to(GROUP_ID))
        st.info(" | ".join(results))


# Footer
st.sidebar.markdown("---")
st.sidebar.caption("RoboVAI CEO Dashboard")
