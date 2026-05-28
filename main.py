#!/usr/bin/env python3
"""
EPC Competitor Intelligence Agent — Entry Point

An autonomous AI-powered competitive intelligence system that monitors
880+ news sources daily, extracts strategic implications using LLM analysis,
and delivers actionable briefings via Telegram.

Usage:
    python main.py              # Run daily digest
    python main.py --test       # Test Telegram connectivity
    python main.py --status     # Show database stats
"""

__version__ = "2.0.0"

import argparse
import io
import logging
import sys
from datetime import datetime

from core.config import LOG_LEVEL, TRACKED_COMPANIES, DB_PATH


def setup_logging() -> None:
    """Configure structured logging for the application."""
    log_format = (
        "%(asctime)s │ %(levelname)-8s │ %(name)-24s │ %(message)s"
    )
    # Wrap stdout in a UTF-8 stream so Unicode log separators (│) don't
    # crash on Windows consoles that default to cp1252.
    utf8_stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True,
    )
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
        format=log_format,
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(utf8_stdout),
            logging.FileHandler("news_agent.log", encoding="utf-8"),
        ],
    )
    # Suppress noisy third-party loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)


def run_digest() -> None:
    """Run the full daily digest pipeline."""
    from core.agent import NewsAgent

    agent = NewsAgent()
    agent.run_daily_digest()


def test_telegram() -> None:
    """Send a test message to verify Telegram setup."""
    from tools.send_telegram import TelegramSender

    sender = TelegramSender()
    if sender.verify_bot():
        sender.send_message(
            f"✅ *EPC Competitor Intelligence — Test Message*\n\n"
            f"Bot is connected and working!\n"
            f"Tracking: {', '.join(TRACKED_COMPANIES)}\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        print("[OK] Test message sent successfully!")
    else:
        print("[FAIL] Failed to verify Telegram bot. Check your TELEGRAM_BOT_TOKEN.")
        sys.exit(1)


def show_status() -> None:
    """Display database and configuration status."""
    from tools.database import NewsDatabase

    db = NewsDatabase()
    count = db.count_articles()
    recent = db.get_recent_articles(limit=5)

    # Use ASCII-safe characters so --status never crashes on Windows
    # consoles that use cp1252 encoding.
    border = "=" * 50
    print(f"\n{border}")
    print("  EPC Competitor Intelligence -- Status")
    print(border)
    print(f"  Database:    {DB_PATH}")
    print(f"  Articles:    {count} total")
    print(f"  Tracking:    {', '.join(TRACKED_COMPANIES)}")
    print(border)

    if recent:
        print("\n  Recent articles:")
        for article in recent:
            title = article.get("title", "Untitled")[:60]
            source = article.get("source", "?")
            print(f"    - [{source}] {title}")
    print()


def main() -> None:
    """Parse CLI arguments and dispatch."""
    parser = argparse.ArgumentParser(
        description="EPC Competitor Intelligence Agent — Daily Digest",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Send a test message to Telegram",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show database and configuration status",
    )
    args = parser.parse_args()

    setup_logging()
    logger = logging.getLogger(__name__)

    try:
        if args.test:
            test_telegram()
        elif args.status:
            show_status()
        else:
            run_digest()
    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
        sys.exit(0)
    except Exception as exc:
        logger.critical("Fatal error: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
