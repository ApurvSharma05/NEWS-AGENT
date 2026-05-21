"""
Telegram Delivery Tool.

Sends formatted messages to a Telegram chat/channel via the Bot API.
Designed as a standalone tool that can be swapped for Slack, Discord, etc.
"""

import logging
from typing import Any

import requests

from core.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger(__name__)

# Telegram Bot API base URL
_TG_API_BASE = "https://api.telegram.org/bot{token}"


class TelegramSender:
    """
    Sends messages to Telegram using the Bot API.

    Supports Markdown formatting and automatic message splitting
    for long digests.
    """

    def __init__(
        self,
        bot_token: str | None = None,
        chat_id: str | None = None,
    ) -> None:
        self.bot_token = bot_token or TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or TELEGRAM_CHAT_ID

        if not self.bot_token or not self.chat_id:
            raise ValueError(
                "TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set."
            )

        self.api_base = _TG_API_BASE.format(token=self.bot_token)

    def send_message(
        self,
        text: str,
        parse_mode: str = "Markdown",
        disable_preview: bool = True,
    ) -> dict[str, Any]:
        """
        Send a text message to the configured Telegram chat.

        Args:
            text: Message content (supports Markdown formatting).
            parse_mode: Telegram parse mode ('Markdown' or 'HTML').
            disable_preview: Whether to disable link previews.

        Returns:
            Telegram API response dict.

        Raises:
            requests.HTTPError: If the API call fails.
        """
        url = f"{self.api_base}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_preview,
        }

        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()

            if result.get("ok"):
                logger.info(
                    "Message sent to Telegram (chat_id=%s, length=%d)",
                    self.chat_id,
                    len(text),
                )
            else:
                logger.warning(
                    "Telegram API returned ok=false: %s",
                    result.get("description", "Unknown error"),
                )

            return result

        except requests.exceptions.RequestException as exc:
            logger.error(
                "Failed to send Telegram message: %s", exc, exc_info=True
            )
            raise

    def send_photo(
        self,
        photo_url: str,
        caption: str = "",
    ) -> dict[str, Any]:
        """
        Send a photo with optional caption. Useful for future chart/graph features.
        """
        url = f"{self.api_base}/sendPhoto"
        payload = {
            "chat_id": self.chat_id,
            "photo": photo_url,
            "caption": caption,
            "parse_mode": "Markdown",
        }

        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as exc:
            logger.error("Failed to send photo: %s", exc)
            raise

    def verify_bot(self) -> bool:
        """
        Verify the bot token is valid by calling getMe.
        """
        url = f"{self.api_base}/getMe"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            if data.get("ok"):
                bot_name = data["result"].get("username", "unknown")
                logger.info("Telegram bot verified: @%s", bot_name)
                return True
            return False
        except requests.exceptions.RequestException as exc:
            logger.error("Bot verification failed: %s", exc)
            return False
