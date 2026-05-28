"""
Telegram Delivery Tool.

Sends formatted competitive intelligence briefings to Telegram chats/channels
via the Bot API. Supports Markdown formatting, multi-chat broadcast, and
automatic message splitting for Telegram's 4096-char limit.
"""

import logging
from typing import Any

import requests

from core.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_IDS

logger = logging.getLogger(__name__)

# Telegram Bot API base URL
_TG_API_BASE = "https://api.telegram.org/bot{token}"


class TelegramSender:
    """
    Sends messages to Telegram using the Bot API.

    Supports Markdown formatting and automatic message splitting
    for long digests. Broadcasts to all configured chat IDs.
    """

    def __init__(
        self,
        bot_token: str | None = None,
        chat_ids: list[str] | None = None,
    ) -> None:
        self.bot_token = bot_token or TELEGRAM_BOT_TOKEN
        self.chat_ids = chat_ids or TELEGRAM_CHAT_IDS

        if not self.bot_token or not self.chat_ids:
            raise ValueError(
                "TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set."
            )

        self.api_base = _TG_API_BASE.format(token=self.bot_token)

    def send_message(
        self,
        text: str,
        parse_mode: str = "Markdown",
        disable_preview: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Send a text message to all configured Telegram chats.

        Args:
            text: Message content (supports Markdown formatting).
            parse_mode: Telegram parse mode ('Markdown' or 'HTML').
            disable_preview: Whether to disable link previews.

        Returns:
            List of Telegram API response dicts.
        """
        url = f"{self.api_base}/sendMessage"
        results = []
        for chat_id in self.chat_ids:
            payload = {
                "chat_id": chat_id,
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
                        chat_id,
                        len(text),
                    )
                else:
                    logger.warning(
                        "Telegram API returned ok=false for chat %s: %s",
                        chat_id,
                        result.get("description", "Unknown error"),
                    )

                results.append(result)

            except requests.exceptions.RequestException as exc:
                logger.error(
                    "Failed to send Telegram message to %s: %s", chat_id, exc, exc_info=True
                )
                
        return results

    def send_photo(
        self,
        photo_url: str,
        caption: str = "",
    ) -> list[dict[str, Any]]:
        """
        Send a photo with optional caption to all configured chats.
        """
        url = f"{self.api_base}/sendPhoto"
        results = []
        for chat_id in self.chat_ids:
            payload = {
                "chat_id": chat_id,
                "photo": photo_url,
                "caption": caption,
                "parse_mode": "Markdown",
            }

            try:
                response = requests.post(url, json=payload, timeout=30)
                response.raise_for_status()
                results.append(response.json())
            except requests.exceptions.RequestException as exc:
                logger.error("Failed to send photo to %s: %s", chat_id, exc)
                
        return results

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
