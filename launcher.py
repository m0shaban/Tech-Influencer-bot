"""
RoboVAI Multi-Bot Launcher
==========================

Entry point for the Hub-and-Spoke architecture.
Uses asyncio.gather for TRUE concurrent execution of all bots.

Usage:
    python launcher.py                  # Run full system (master + workers)
    python launcher.py --master-only    # Run only master controller
    python launcher.py --workers-only   # Run only brand workers
    python launcher.py --brand BS       # Run only one brand worker
"""

import argparse
import asyncio
import os
import sys
import threading
import signal
import traceback
from pathlib import Path
from typing import Optional, List

from telegram import Bot
from dotenv import load_dotenv

# Ensure base directory is in path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# Load environment variables early (before check_environment)
load_dotenv(dotenv_path=BASE_DIR / ".env")

# Start keep-alive HTTP server (for Render web service)
try:
    from keep_alive import keep_alive

    keep_alive()
except ImportError:
    print("[LAUNCHER] Warning: keep_alive not available (OK for local dev)")


def _log(message: str) -> None:
    """Safe logging for Windows console."""
    try:
        print(f"[LAUNCHER] {message}")
    except UnicodeEncodeError:
        safe_msg = message.encode("ascii", "replace").decode("ascii")
        print(f"[LAUNCHER] {safe_msg}")


def check_environment() -> bool:
    """Verify that all required environment variables are set."""
    required_vars = [
        "TELEGRAM_TOKEN",  # Master bot
        "GROQ_API_KEY",  # AI processing
    ]

    missing = [var for var in required_vars if not os.getenv(var)]

    if missing:
        _log("ERROR: Missing environment variables:")
        for var in missing:
            _log(f"  - {var}")
        return False

    _log("Environment check passed")
    return True


# ============================================================
# ASYNCIO-BASED CONCURRENT LAUNCHER
# ============================================================


async def run_master_async():
    """Run Master Controller asynchronously."""
    from master_controller import build_master_application

    _log("Starting Master Controller (async)...")
    app = build_master_application()

    try:
        await app.initialize()
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)

        # Keep running forever
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        _log("Master Controller shutting down...")
    except Exception as e:
        _log(f"Master Controller error: {e}")
        await alert_admin_startup_error("MASTER", str(e), traceback.format_exc())
    finally:
        await app.stop()


async def run_worker_async(brand_key: str):
    """Run a single Worker Bot asynchronously."""
    from brands_config import get_brand_by_key
    from worker_bot import BrandWorker, send_alert_to_admin

    brand = get_brand_by_key(brand_key)
    if not brand:
        _log(f"ERROR: Unknown brand: {brand_key}")
        return

    if not brand.token:
        _log(f"ERROR: No token for brand {brand_key}")
        return

    _log(f"Starting worker for {brand.display_name} (async)...")
    worker = BrandWorker(brand)

    try:
        await worker.start()
    except asyncio.CancelledError:
        _log(f"Worker {brand_key} shutting down...")
    except Exception as e:
        _log(f"Worker {brand_key} crashed: {e}")
        tb = traceback.format_exc()
        await send_alert_to_admin(brand_key, str(e), tb)
    finally:
        await worker.stop()


async def alert_admin_startup_error(component: str, error: str, tb: str):
    """Alert admin if a component fails to start."""
    from brands_config import MASTER_BOT_TOKEN, ADMIN_USER_ID

    if not MASTER_BOT_TOKEN or not ADMIN_USER_ID:
        return

    try:
        bot = Bot(token=MASTER_BOT_TOKEN)
        await bot.send_message(
            chat_id=ADMIN_USER_ID,
            text=f"🚨 **STARTUP FAILURE** 🚨\n\nComponent: {component}\nError: {error[:500]}\n\n```\n{tb[:800]}\n```",
            parse_mode="Markdown",
        )
    except:
        pass


async def run_full_system_async():
    """Run Master + all Workers concurrently using asyncio.gather."""
    from brands_config import get_brand_configs

    tasks = []

    # Task 1: Master Controller
    tasks.append(asyncio.create_task(run_master_async(), name="Master"))

    # Give master a moment to initialize
    await asyncio.sleep(1)

    # Tasks 2-N: Brand Workers
    brands = get_brand_configs()
    for brand_key, brand in brands.items():
        if not brand.token:
            _log(f"Skipping {brand_key}: No token configured")
            continue

        task = asyncio.create_task(
            run_worker_async(brand_key), name=f"Worker-{brand_key}"
        )
        tasks.append(task)
        await asyncio.sleep(0.5)  # Stagger starts slightly

    _log(f"All {len(tasks)} bots launched with asyncio.gather. Press Ctrl+C to stop.")

    try:
        # Run all tasks concurrently
        await asyncio.gather(*tasks, return_exceptions=True)
    except asyncio.CancelledError:
        _log("Shutting down all tasks...")
        for task in tasks:
            task.cancel()


async def run_workers_only_async():
    """Run only brand workers with asyncio.gather."""
    from brands_config import get_brand_configs

    tasks = []
    brands = get_brand_configs()

    for brand_key, brand in brands.items():
        if not brand.token:
            _log(f"Skipping {brand_key}: No token configured")
            continue

        task = asyncio.create_task(
            run_worker_async(brand_key), name=f"Worker-{brand_key}"
        )
        tasks.append(task)
        _log(f"Worker task created for {brand.display_name}")
        await asyncio.sleep(0.5)

    _log(f"All {len(tasks)} workers launched. Press Ctrl+C to stop.")

    try:
        await asyncio.gather(*tasks, return_exceptions=True)
    except asyncio.CancelledError:
        for task in tasks:
            task.cancel()


# ============================================================
# THREADING FALLBACK (for run_polling compatibility)
# ============================================================


def run_master_controller_thread():
    """Run master controller in a separate thread (fallback)."""
    from master_controller import build_master_application

    try:
        _log("Starting Master Controller...")
        app = build_master_application()
        app.run_polling(drop_pending_updates=True, stop_signals=None)
    except Exception as e:
        _log(f"Master Controller error: {e}")


def run_worker_thread(brand_key: str):
    """Run a single worker bot in a separate thread (fallback)."""
    from brands_config import get_brand_by_key
    from worker_bot import BrandWorker, send_alert_sync

    brand = get_brand_by_key(brand_key)
    if not brand:
        _log(f"ERROR: Unknown brand: {brand_key}")
        return

    if not brand.token:
        _log(f"ERROR: No token for brand {brand_key}")
        return

    try:
        _log(f"Starting worker for {brand.display_name}...")
        worker = BrandWorker(brand)
        worker.start_polling()
    except Exception as e:
        _log(f"Worker {brand_key} error: {e}")
        tb = traceback.format_exc()
        send_alert_sync(brand_key, str(e), tb)


def run_full_system():
    """Launch both master controller and all brand workers using threads."""
    from brands_config import get_brand_configs
    import time

    threads = []

    # Start master controller
    master_thread = threading.Thread(
        target=run_master_controller_thread,
        name="Master-Controller",
        daemon=True,
    )
    master_thread.start()
    threads.append(master_thread)
    _log("Master Controller thread started")

    time.sleep(2)

    # Start all brand workers
    brands = get_brand_configs()
    for brand_key, brand in brands.items():
        if not brand.token:
            _log(f"Skipping {brand_key}: No token configured")
            continue

        worker_thread = threading.Thread(
            target=run_worker_thread,
            args=(brand_key,),
            name=f"Worker-{brand_key}",
            daemon=True,
        )
        worker_thread.start()
        threads.append(worker_thread)
        _log(f"Worker thread started for {brand.display_name}")
        time.sleep(1)

    _log("All bots launched. Press Ctrl+C to stop.")

    try:
        for thread in threads:
            thread.join()
    except KeyboardInterrupt:
        _log("Shutting down...")
        sys.exit(0)


def run_master_only():
    """Run only the master controller."""
    _log("Starting Master Controller only...")
    from master_controller import build_master_application

    app = build_master_application()
    app.run_polling(drop_pending_updates=True)


def run_workers_only():
    """Run only the brand worker bots (no master)."""
    _log("Starting workers only with asyncio...")
    asyncio.run(run_workers_only_async())


def run_single_brand(brand_key: str):
    """Run only a specific brand worker."""
    from brands_config import get_brand_by_key

    brand = get_brand_by_key(brand_key)
    if not brand:
        _log(f"ERROR: Unknown brand: {brand_key}")
        _log("Available brands: ARB, BS, ZDS")
        sys.exit(1)

    if not brand.token:
        _log(f"ERROR: No token configured for {brand_key}")
        sys.exit(1)

    _log(f"Starting single brand: {brand.display_name}")
    asyncio.run(run_worker_async(brand_key))


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="RoboVAI Multi-Bot System Launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python launcher.py                  # Full system (threading)
  python launcher.py --async          # Full system (asyncio.gather)
  python launcher.py --master-only    # Master only
  python launcher.py --workers-only   # Workers only (asyncio)
  python launcher.py --brand BS       # BlockSignals only
        """,
    )

    parser.add_argument(
        "--master-only",
        action="store_true",
        help="Run only the master controller (no brand workers)",
    )
    parser.add_argument(
        "--workers-only",
        action="store_true",
        help="Run only brand workers (no master controller)",
    )
    parser.add_argument(
        "--brand",
        type=str,
        help="Run only a specific brand worker (e.g., --brand BS)",
    )
    parser.add_argument(
        "--async",
        dest="use_async",
        action="store_true",
        help="Use asyncio.gather for concurrent execution (recommended)",
    )
    parser.add_argument(
        "--no-env-check",
        action="store_true",
        help="Skip environment variable check",
    )

    args = parser.parse_args()

    # Print banner
    _log("=" * 50)
    _log("    RoboVAI Hub-and-Spoke System")
    _log("    Architecture: Supervisor-Worker Pattern")
    _log("=" * 50)

    # Check environment
    if not args.no_env_check and not check_environment():
        sys.exit(1)

    # Run appropriate mode
    if args.brand:
        run_single_brand(args.brand.upper())
    elif args.master_only:
        run_master_only()
    elif args.workers_only:
        run_workers_only()
    elif args.use_async:
        _log("Using asyncio.gather for true concurrency...")
        asyncio.run(run_full_system_async())
    else:
        run_full_system()


if __name__ == "__main__":
    main()
