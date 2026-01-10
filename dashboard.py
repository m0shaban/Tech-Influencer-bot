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
    "channel_id": "",
    "group_id": "",
    "active_brand": "",
    "brands": {},
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


def _rerun() -> None:
    # Streamlit renamed experimental_rerun -> rerun in newer versions.
    rerun_fn = getattr(st, "rerun", None) or getattr(st, "experimental_rerun", None)
    if callable(rerun_fn):
        rerun_fn()


def load_feeds_from_code(*, brand: str | None = None) -> List[str]:
    try:
        from feeds_config import RSS_FEEDS, get_feeds_for_brand

        brand_key = (brand or "").strip()
        if brand_key:
            brand_feeds = get_feeds_for_brand(brand_key)
            if brand_feeds:
                return list(brand_feeds)
        return list(RSS_FEEDS)
    except Exception:
        return []


def write_feeds_to_code(feeds: List[str]) -> None:
    """Deprecated: do not overwrite feeds_config.py from the dashboard.

    The repo now supports brand-aware feeds in feeds_config.py and config.json.
    """
    raise RuntimeError(
        "Dashboard no longer writes feeds_config.py directly; edit brand feeds in config.json."
    )


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


def load_autopublisher_status() -> Dict[str, Any]:
    """Load the live status from auto_publisher.py"""
    try:
        status_path = BASE_DIR / "autopublisher_status.json"
        if status_path.exists():
            return json.loads(status_path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


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
    from streamlit_option_menu import option_menu  # type: ignore[import-not-found]
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
                "🏷️ Brand Manager",
                "🔗 Feed Manager",
                "🌐 Platform Status",
                "� Schedule Settings",
                "📋 Live Terminal",
                "📢 Manual Broadcast",
            ],
            icons=[
                "house",
                "cpu",
                "link",
                "globe",
                "calendar",
                "terminal",
                "megaphone",
            ],
            menu_icon="list",
            default_index=0,
        )
        if option_menu
        else st.radio(
            "Navigation",
            (
                "🏠 The Cockpit",
                "🧠 AI Brain Surgery",
                "🏷️ Brand Manager",
                "🔗 Feed Manager",
                "🌐 Platform Status",
                "📅 Schedule Settings",
                "📋 Live Terminal",
                "📢 Manual Broadcast",
            ),
        )
    )


def _get_brands(cfg: Dict[str, Any]) -> Dict[str, Any]:
    brands = cfg.get("brands")
    return brands if isinstance(brands, dict) else {}


def _sync_active_brand_into_runtime(cfg: Dict[str, Any]) -> None:
    """Keep backward compatibility: main runtime reads top-level keys."""
    active_key = str(cfg.get("active_brand") or "").strip()
    brands = _get_brands(cfg)
    active = brands.get(active_key) if active_key else None
    if not isinstance(active, dict):
        return
    if isinstance(active.get("system_prompt"), str):
        cfg["system_prompt"] = active.get("system_prompt", "")
    if isinstance(active.get("feeds"), list):
        cfg["feeds"] = active.get("feeds", [])
    if isinstance(active.get("channel_id"), str):
        cfg["channel_id"] = active.get("channel_id", "")
    if isinstance(active.get("group_id"), str):
        cfg["group_id"] = active.get("group_id", "")


config = load_config()
_sync_active_brand_into_runtime(config)

# Bootstrap: if active brand has no feeds, load defaults for that brand.
active_brand_key = str(config.get("active_brand") or "").strip()
brands_boot = _get_brands(config)
active_boot = brands_boot.get(active_brand_key) if active_brand_key else None
active_brand_feeds = (
    active_boot.get("feeds")
    if isinstance(active_boot, dict) and isinstance(active_boot.get("feeds"), list)
    else []
)
if active_brand_key and not active_brand_feeds:
    defaults = load_feeds_from_code(brand=active_brand_key)
    if defaults:
        brands_boot.setdefault(active_brand_key, {})
        if isinstance(brands_boot.get(active_brand_key), dict):
            brands_boot[active_brand_key]["feeds"] = defaults
        config["brands"] = brands_boot
        _sync_active_brand_into_runtime(config)

feeds_list = config.get("feeds") or []
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

    # Load fresh status from AutoPublisher
    ap_status = load_autopublisher_status()

    # Row 1: Key Metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Status", f"{status_color} {status_label}")
    c2.metric("Active Feeds", feeds_count)

    posts_today = ap_status.get("posts_today", 0)
    max_posts = ap_status.get("max_posts_per_day", 50)
    c3.metric("Posts Today", f"{posts_today} / {max_posts}")

    biz_status = ap_status.get("business_hours_status", "UNKNOWN")
    biz_icon = "🌞" if biz_status == "OPEN" else "🌙"
    c4.metric("Biz Hours", f"{biz_icon} {biz_status}")

    # Row 2: Timing
    st.markdown("---")
    k1, k2 = st.columns(2)

    # Last Run
    last_run_ts = ap_status.get("last_post_date")
    if last_run_ts:
        try:
            dt = datetime.fromisoformat(last_run_ts)
            last_run_pretty = dt.strftime("%H:%M:%S")
        except Exception:
            last_run_pretty = str(last_run_ts)
    else:
        last_run_pretty = last_run or "No Data"

    k1.metric("Last Publish Time", last_run_pretty)

    # Next Run
    next_run_ts = ap_status.get("next_run_estimated")
    if next_run_ts:
        try:
            ndt = datetime.fromisoformat(next_run_ts)
            next_run_pretty = ndt.strftime("%H:%M:%S")
        except Exception:
            next_run_pretty = str(next_run_ts)
    else:
        next_run_pretty = "Calculating / Sleeping"

    k2.metric("Next Estimated Run", next_run_pretty)

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


# ------------- Brand Manager -------------
elif menu_choice == "🏷️ Brand Manager":
    st.title("🏷️ Brand Manager")
    st.caption("Multiple brands/profiles: feeds + prompts + channel destinations")

    cfg = load_config()
    brands = _get_brands(cfg)
    active_brand = str(cfg.get("active_brand") or "").strip()

    st.markdown("### Active Brand")
    brand_keys = sorted(brands.keys())
    active_index = brand_keys.index(active_brand) if active_brand in brand_keys else 0
    selected = st.selectbox(
        "Choose active brand",
        options=brand_keys if brand_keys else [""],
        index=active_index if brand_keys else 0,
        help="The bot runtime will use this brand's feeds/prompt/channel_id.",
    )

    col_a, col_b = st.columns(2)
    with col_a:
        new_key = st.text_input(
            "New brand key (e.g. robovai_ar / nextstep_en)",
            value="",
        ).strip()
    with col_b:
        new_name = st.text_input("Display name", value="").strip()

    if st.button("➕ Create Brand"):
        if not new_key:
            st.error("Brand key is required")
        elif new_key in brands:
            st.error("Brand key already exists")
        else:
            # Platform defaults from platform_config.json
            platform_defaults: Dict[str, Any] = {}
            try:
                p = Path(__file__).parent / "platform_config.json"
                if p.exists():
                    pdata = json.loads(p.read_text(encoding="utf-8"))
                    if isinstance(pdata, dict) and isinstance(
                        pdata.get("platforms"), dict
                    ):
                        for k, v in pdata["platforms"].items():
                            if isinstance(v, dict):
                                platform_defaults[k] = {
                                    "enabled": bool(v.get("enabled", True))
                                }
            except Exception:
                platform_defaults = {}

            brands[new_key] = {
                "display_name": new_name or new_key,
                "language": "ar",
                "system_prompt": "",
                "feeds": [],
                "channel_id": "",
                "group_id": "",
                "platforms": platform_defaults,
                "facebook_page_url": "",
                "accounts": {
                    "facebook": "",
                    "devto": "",
                    "blogger": "",
                    "discord": "",
                    "telegram": "",
                },
            }
            cfg["brands"] = brands
            if not cfg.get("active_brand"):
                cfg["active_brand"] = new_key
            _sync_active_brand_into_runtime(cfg)
            save_config(cfg)
            st.success("Brand created")

    if selected and selected in brands and isinstance(brands[selected], dict):
        st.markdown("---")
        st.markdown(f"### Edit: `{selected}`")
        b = dict(brands[selected])

        b["display_name"] = st.text_input(
            "Display name",
            value=str(b.get("display_name") or selected),
        )
        b["language"] = st.selectbox(
            "Language",
            options=["ar", "en"],
            index=0 if str(b.get("language") or "ar") == "ar" else 1,
        )
        b["channel_id"] = st.text_input(
            "Telegram channel_id (e.g. -100123...)",
            value=str(b.get("channel_id") or cfg.get("channel_id") or CHANNEL_ID or ""),
        )
        b["group_id"] = st.text_input(
            "Telegram group_id (optional)",
            value=str(b.get("group_id") or cfg.get("group_id") or GROUP_ID or ""),
        )
        b["system_prompt"] = st.text_area(
            "System prompt",
            value=str(b.get("system_prompt") or ""),
            height=220,
        )

        b["facebook_page_url"] = st.text_input(
            "Facebook Page URL for CTA (optional)",
            value=str(b.get("facebook_page_url") or ""),
            help="If empty, the global platform_config.json facebook.page_url will be used.",
        ).strip()

        st.markdown("#### Platforms for this brand")
        try:
            p = Path(__file__).parent / "platform_config.json"
            pdata = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
            available_platforms = (
                list(pdata.get("platforms", {}).keys())
                if isinstance(pdata, dict)
                else []
            )
        except Exception:
            available_platforms = []

        platform_state_raw = b.get("platforms")
        platform_state: Dict[str, Any] = (
            platform_state_raw if isinstance(platform_state_raw, dict) else {}
        )
        updated_platforms: Dict[str, Any] = dict(platform_state)
        cols = st.columns(4)
        for idx, key in enumerate(available_platforms):
            current_enabled = True
            entry = platform_state.get(key)
            if isinstance(entry, dict) and "enabled" in entry:
                current_enabled = bool(entry.get("enabled"))
            with cols[idx % 4]:
                checked = st.checkbox(
                    key, value=current_enabled, key=f"brand_{selected}_plat_{key}"
                )
            updated_platforms[key] = {"enabled": bool(checked)}
        b["platforms"] = updated_platforms

        st.markdown("#### Accounts (multi-accounts per platform)")
        st.caption(
            "اكتب suffix للحساب (مثال: RBV). ساعتها هنستخدم متغيرات Render بالشكل: FACEBOOK_PAGE_ID_RBV, DEVTO_API_KEY_RBV ..."
        )
        accounts_raw = b.get("accounts")
        accounts = accounts_raw if isinstance(accounts_raw, dict) else {}
        a_fb = st.text_input(
            "Facebook account suffix", value=str(accounts.get("facebook") or "")
        ).strip()
        a_dev = st.text_input(
            "Dev.to account suffix", value=str(accounts.get("devto") or "")
        ).strip()
        a_blog = st.text_input(
            "Blogger account suffix", value=str(accounts.get("blogger") or "")
        ).strip()
        a_dis = st.text_input(
            "Discord account suffix", value=str(accounts.get("discord") or "")
        ).strip()
        a_tg = st.text_input(
            "Telegram bot token suffix (optional)",
            value=str(accounts.get("telegram") or ""),
        ).strip()
        b["accounts"] = {
            "facebook": a_fb,
            "devto": a_dev,
            "blogger": a_blog,
            "discord": a_dis,
            "telegram": a_tg,
        }
        feeds_text = "\n".join(
            [str(x) for x in (b.get("feeds") or []) if isinstance(x, str)]
        )
        feeds_text = st.text_area("Feeds (one per line)", value=feeds_text, height=220)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Save Brand"):
                b["feeds"] = [
                    ln.strip() for ln in feeds_text.splitlines() if ln.strip()
                ]
                brands[selected] = b
                cfg["brands"] = brands
                save_config(cfg)
                st.success("Saved")
        with col2:
            if st.button("✅ Set as Active"):
                cfg["active_brand"] = selected
                cfg["brands"] = brands
                _sync_active_brand_into_runtime(cfg)
                save_config(cfg)
                st.success("Active brand updated")

    st.info(
        "ملاحظة: حالياً بنزامن بيانات البراند النشط إلى المفاتيح الأساسية (feeds/system_prompt/channel_id). "
        "ده يخلي البوت يشتغل بدون تعديل كبير. بعد كده نقدر نفصل Tokens/Accounts لكل براند لو محتاج."
    )


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

    brands = _get_brands(config)
    brand_keys = sorted(list(brands.keys()))
    active_brand = str(config.get("active_brand") or "").strip()
    default_brand = (
        active_brand
        if active_brand in brand_keys
        else (brand_keys[0] if brand_keys else "")
    )

    colb1, colb2 = st.columns([2, 1])
    with colb1:
        selected_brand = st.selectbox(
            "Brand",
            brand_keys,
            index=(
                (brand_keys.index(default_brand) if default_brand in brand_keys else 0)
                if brand_keys
                else 0
            ),
            disabled=not bool(brand_keys),
        )
    with colb2:
        st.caption(f"Active: {active_brand or '(none)'}")

    brand_cfg = brands.get(selected_brand) if selected_brand else {}
    feeds = brand_cfg.get("feeds", []) if isinstance(brand_cfg, dict) else []
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
        if selected_brand:
            brands = _get_brands(config)
            brands.setdefault(selected_brand, {})
            if isinstance(brands.get(selected_brand), dict):
                brands[selected_brand]["feeds"] = cleaned
            config["brands"] = brands
            if selected_brand == str(config.get("active_brand") or "").strip():
                _sync_active_brand_into_runtime(config)
            save_config(config)
            st.success(f"Saved {len(cleaned)} feeds for brand '{selected_brand}'")
        else:
            st.error("No brand selected")

    st.markdown("---")
    if st.button("Load defaults from feeds_config.py", use_container_width=True):
        if not selected_brand:
            st.error("No brand selected")
        else:
            feeds_from_code = load_feeds_from_code(brand=selected_brand)
            brands = _get_brands(config)
            brands.setdefault(selected_brand, {})
            if isinstance(brands.get(selected_brand), dict):
                brands[selected_brand]["feeds"] = feeds_from_code
            config["brands"] = brands
            if selected_brand == str(config.get("active_brand") or "").strip():
                _sync_active_brand_into_runtime(config)
            save_config(config)
            st.success(
                f"Loaded {len(feeds_from_code)} default feeds for '{selected_brand}'"
            )
            _rerun()


# ------------- Platform Status -------------
elif menu_choice == "🌐 Platform Status":
    st.title("🌐 Platform Status")
    st.caption("Monitor all connected social media platforms")

    try:
        from multi_platform_publisher import MultiPlatformPublisher

        publisher = MultiPlatformPublisher()
        status = publisher.get_platform_status()

        # Platform configurations
        platforms_info = {
            "telegram": {
                "name": "📱 Telegram",
                "color": "blue",
                "config": ["TELEGRAM_TOKEN", "CHANNEL_ID"],
            },
            "discord": {
                "name": "💬 Discord",
                "color": "purple",
                "config": ["DISCORD_WEBHOOK_URL"],
            },
            "blogger": {
                "name": "📝 Blogger",
                "color": "orange",
                "config": ["BLOGGER_BLOG_ID", "BLOGGER_ACCESS_TOKEN"],
            },
            "facebook": {
                "name": "👥 Facebook",
                "color": "blue",
                "config": ["FACEBOOK_PAGE_ACCESS_TOKEN", "FACEBOOK_PAGE_ID"],
            },
            "linkedin": {
                "name": "💼 LinkedIn",
                "color": "blue",
                "config": ["LINKEDIN_ACCESS_TOKEN"],
            },
            "twitter": {
                "name": "🐦 Twitter/X",
                "color": "blue",
                "config": [
                    "TWITTER_API_KEY",
                    "TWITTER_API_SECRET",
                    "TWITTER_ACCESS_TOKEN",
                ],
            },
            "reddit": {
                "name": "🔴 Reddit",
                "color": "orange",
                "config": [
                    "REDDIT_CLIENT_ID",
                    "REDDIT_CLIENT_SECRET",
                    "REDDIT_USERNAME",
                ],
            },
            "medium": {
                "name": "📖 Medium",
                "color": "green",
                "config": ["MEDIUM_INTEGRATION_TOKEN", "MEDIUM_USER_ID"],
            },
        }

        # Summary metrics
        active_count = sum(1 for v in status.values() if v)
        total_count = len(status)

        col1, col2, col3 = st.columns(3)
        col1.metric("✅ Active Platforms", active_count)
        col2.metric("🔴 Inactive Platforms", total_count - active_count)
        col3.metric("📊 Success Rate", f"{(active_count/total_count*100):.0f}%")

        st.markdown("---")

        # Platform cards
        for platform_key, platform_info in platforms_info.items():
            if platform_key in status:
                is_active = status[platform_key]
                status_emoji = "✅" if is_active else "❌"
                status_text = "Connected" if is_active else "Not Configured"

                with st.expander(
                    f"{status_emoji} {platform_info['name']} - {status_text}",
                    expanded=False,
                ):
                    if is_active:
                        st.success(f"✅ {platform_info['name']} is ready to publish")
                    else:
                        st.warning(f"⚠️ {platform_info['name']} is not configured")
                        st.caption("Required environment variables:")
                        for var in platform_info["config"]:
                            st.code(var, language="bash")

        st.markdown("---")

        # Test button
        if st.button("🧪 Test All Platforms", type="primary", use_container_width=True):
            st.info("🔄 Testing platforms... (check bot logs for results)")
            st.caption("Use Telegram bot command '🧪 Test Platforms' for full testing")

    except Exception as exc:
        st.error(f"❌ Error loading platform status: {exc}")


# ------------- Schedule Settings -------------
elif menu_choice == "📅 Schedule Settings":
    st.title("📅 Schedule Settings")
    st.caption("Configure publishing schedule and platform-specific settings")

    try:
        import json
        from pathlib import Path

        config_path = Path(__file__).parent / "platform_config.json"

        # Load platform config
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                platform_config = json.load(f)
        else:
            st.error("❌ platform_config.json not found")
            st.stop()

        # Global settings
        st.subheader("⚙️ Global Settings")

        global_settings = platform_config.get("global_settings", {})

        col1, col2 = st.columns(2)
        with col1:
            enable_reports = st.checkbox(
                "Enable Admin Reports",
                value=global_settings.get("enable_reports", True),
                help="Send real-time reports to admin via Telegram",
            )

        with col2:
            distribution_mode = st.selectbox(
                "Distribution Mode",
                options=["shared", "unique"],
                index=0 if global_settings.get("distribution_mode") == "shared" else 1,
                help="shared: same content to all platforms | unique: different content per platform",
            )

        global_settings["enable_reports"] = enable_reports
        global_settings["distribution_mode"] = distribution_mode

        st.markdown("---")

        # Platform-specific settings
        st.subheader("📱 Platform Settings")

        platforms_data = platform_config.get("platforms", {})

        for platform_key in [
            "telegram",
            "discord",
            "blogger",
            "facebook",
            "linkedin",
            "twitter",
            "reddit",
            "medium",
            "devto",
        ]:
            if platform_key not in platforms_data:
                continue

            platform_info = platforms_data[platform_key]

            with st.expander(
                f"{'✅' if platform_info.get('enabled') else '❌'} {platform_key.upper()}",
                expanded=False,
            ):
                col1, col2, col3 = st.columns([1, 1, 1])

                with col1:
                    enabled = st.checkbox(
                        "Enabled",
                        value=platform_info.get("enabled", False),
                        key=f"{platform_key}_enabled",
                    )

                with col2:
                    publish_mode = st.selectbox(
                        "Publish Mode",
                        options=["immediate", "delayed"],
                        index=(
                            0 if platform_info.get("publish_mode") == "immediate" else 1
                        ),
                        key=f"{platform_key}_mode",
                    )

                with col3:
                    delay_minutes = st.number_input(
                        "Delay (minutes)",
                        min_value=0,
                        max_value=120,
                        value=platform_info.get("delay_minutes", 0),
                        step=5,
                        key=f"{platform_key}_delay",
                        disabled=(publish_mode == "immediate"),
                    )

                custom_prompt = st.text_area(
                    "Custom AI Prompt",
                    value=platform_info.get("custom_prompt", ""),
                    height=100,
                    key=f"{platform_key}_prompt",
                    help="Platform-specific instructions for AI content generation",
                )

                # Update values
                platform_info["enabled"] = enabled
                platform_info["publish_mode"] = publish_mode
                platform_info["delay_minutes"] = (
                    delay_minutes if publish_mode == "delayed" else 0
                )
                platform_info["custom_prompt"] = custom_prompt

        st.markdown("---")

        # Save button
        if st.button(
            "💾 Save Schedule Settings", type="primary", use_container_width=True
        ):
            platform_config["global_settings"] = global_settings
            platform_config["platforms"] = platforms_data

            try:
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(platform_config, f, ensure_ascii=False, indent=2)
                st.success("✅ Settings saved successfully!")
                st.balloons()
            except Exception as e:
                st.error(f"❌ Failed to save: {e}")

        # Quick presets
        st.markdown("---")
        st.subheader("⚡ Quick Presets")

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("🚀 Instant All", use_container_width=True):
                for platform_key in platforms_data:
                    platforms_data[platform_key]["publish_mode"] = "immediate"
                    platforms_data[platform_key]["delay_minutes"] = 0
                st.success("Set all platforms to immediate mode")
                _rerun()

        with col2:
            if st.button("⏱️ Staggered 5min", use_container_width=True):
                delays = [0, 5, 10, 15, 20, 25, 30, 35]
                for i, platform_key in enumerate(platforms_data):
                    if i < len(delays):
                        platforms_data[platform_key]["publish_mode"] = "delayed"
                        platforms_data[platform_key]["delay_minutes"] = delays[i]
                st.success("Set staggered 5-minute delays")
                _rerun()

        with col3:
            if st.button("🕐 Staggered 10min", use_container_width=True):
                delays = [0, 10, 20, 30, 40, 50, 60, 70]
                for i, platform_key in enumerate(platforms_data):
                    if i < len(delays):
                        platforms_data[platform_key]["publish_mode"] = "delayed"
                        platforms_data[platform_key]["delay_minutes"] = delays[i]
                st.success("Set staggered 10-minute delays")
                _rerun()

    except Exception as exc:
        st.error(f"❌ Error: {exc}")


# ------------- Live Terminal -------------
elif menu_choice == "📋 Live Terminal":
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
