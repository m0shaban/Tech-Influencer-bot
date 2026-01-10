"""
Enhanced Logging System for Tech Influencer Bot
Provides detailed logs for debugging and monitoring
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
from logging.handlers import RotatingFileHandler
import json

# Log directory
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Log file paths
MAIN_LOG = LOG_DIR / "bot.log"
ERROR_LOG = LOG_DIR / "errors.log"
PUBLISH_LOG = LOG_DIR / "publishing.log"
AI_LOG = LOG_DIR / "ai_generation.log"


class ColoredFormatter(logging.Formatter):
    """Colored log formatter for console output"""

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[41m",  # Red background
    }
    RESET = "\033[0m"

    def format(self, record):
        # Add color based on level
        color = self.COLORS.get(record.levelname, "")
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        record.msg = f"{color}{record.msg}{self.RESET}"
        return super().format(record)


class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging"""

    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add extra fields if present
        if hasattr(record, "brand"):
            log_data["brand"] = record.brand
        if hasattr(record, "platform"):
            log_data["platform"] = record.platform
        if hasattr(record, "error_type"):
            log_data["error_type"] = record.error_type
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms

        # Add exception info
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)


def setup_logging(
    level: str = "INFO",
    console: bool = True,
    file: bool = True,
    json_format: bool = False,
) -> logging.Logger:
    """
    Setup enhanced logging system

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        console: Enable console output
        file: Enable file output
        json_format: Use JSON format for file logs

    Returns:
        Configured logger
    """
    # Get root logger
    logger = logging.getLogger("robobot")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Clear existing handlers
    logger.handlers.clear()

    # Console handler with colors
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)

        if sys.stdout.isatty():  # Only use colors in terminal
            console_formatter = ColoredFormatter(
                "%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s",
                datefmt="%H:%M:%S",
            )
        else:
            console_formatter = logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%H:%M:%S",
            )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    # File handler for all logs
    if file:
        # Main log file (rotating, 10MB max, keep 5 backups)
        main_handler = RotatingFileHandler(
            MAIN_LOG, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        main_handler.setLevel(logging.DEBUG)

        if json_format:
            main_handler.setFormatter(JSONFormatter())
        else:
            main_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            )
        logger.addHandler(main_handler)

        # Error log file (errors only)
        error_handler = RotatingFileHandler(
            ERROR_LOG, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)s | %(name)s | %(funcName)s:%(lineno)d\n%(message)s\n---\n",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(error_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a child logger with the given name"""
    return logging.getLogger(f"robobot.{name}")


# Pre-configured loggers for different components
def get_publish_logger() -> logging.Logger:
    """Logger for publishing operations"""
    logger = get_logger("publish")

    # Add publishing-specific file handler if not already added
    if not any(
        isinstance(h, RotatingFileHandler) and PUBLISH_LOG.name in str(h.baseFilename)
        for h in logger.handlers
    ):
        handler = RotatingFileHandler(
            PUBLISH_LOG, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
            )
        )
        logger.addHandler(handler)

    return logger


def get_ai_logger() -> logging.Logger:
    """Logger for AI generation operations"""
    logger = get_logger("ai")

    # Add AI-specific file handler if not already added
    if not any(
        isinstance(h, RotatingFileHandler) and AI_LOG.name in str(h.baseFilename)
        for h in logger.handlers
    ):
        handler = RotatingFileHandler(
            AI_LOG, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)s | Brand: %(brand)s | Platform: %(platform)s\n%(message)s\n---\n",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(handler)

    return logger


class LogContext:
    """Context manager for adding extra log fields"""

    def __init__(self, logger: logging.Logger, **kwargs):
        self.logger = logger
        self.extra = kwargs
        self.old_factory = None

    def __enter__(self):
        # Store old factory
        self.old_factory = logging.getLogRecordFactory()

        # Create new factory that adds our extra fields
        extra = self.extra

        def record_factory(*args, **kwargs):
            record = self.old_factory(*args, **kwargs)
            for key, value in extra.items():
                setattr(record, key, value)
            return record

        logging.setLogRecordFactory(record_factory)
        return self.logger

    def __exit__(self, *args):
        # Restore old factory
        logging.setLogRecordFactory(self.old_factory)


# Utility functions
def log_publish_attempt(
    brand: str,
    platform: str,
    title: str,
    success: bool,
    error: Optional[str] = None,
    url: Optional[str] = None,
    duration_ms: Optional[int] = None,
):
    """Log a publishing attempt with structured data"""
    logger = get_publish_logger()

    status = "✅ SUCCESS" if success else "❌ FAILED"
    msg_parts = [
        f"{status}",
        f"Brand: {brand}",
        f"Platform: {platform}",
        f"Title: {title[:50]}...",
    ]

    if url:
        msg_parts.append(f"URL: {url}")
    if duration_ms:
        msg_parts.append(f"Duration: {duration_ms}ms")
    if error:
        msg_parts.append(f"Error: {error}")

    message = " | ".join(msg_parts)

    if success:
        logger.info(message, extra={"brand": brand, "platform": platform})
    else:
        logger.error(message, extra={"brand": brand, "platform": platform})


def log_ai_generation(
    brand: str,
    platform: str,
    model: str,
    success: bool,
    error: Optional[str] = None,
    tokens_used: Optional[int] = None,
    duration_ms: Optional[int] = None,
):
    """Log an AI generation attempt"""
    logger = get_ai_logger()

    status = "✅" if success else "❌"
    msg = f"{status} AI Generation | Model: {model}"

    if tokens_used:
        msg += f" | Tokens: {tokens_used}"
    if duration_ms:
        msg += f" | Duration: {duration_ms}ms"
    if error:
        msg += f" | Error: {error}"

    log_level = logging.INFO if success else logging.ERROR
    logger.log(log_level, msg, extra={"brand": brand, "platform": platform})


# Initialize logging when module is imported
_root_logger = setup_logging(
    level=os.getenv("LOG_LEVEL", "INFO"), console=True, file=True
)

# Export
__all__ = [
    "setup_logging",
    "get_logger",
    "get_publish_logger",
    "get_ai_logger",
    "LogContext",
    "log_publish_attempt",
    "log_ai_generation",
]
