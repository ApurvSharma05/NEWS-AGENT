"""
Telegram Delivery Tool.

Sends formatted news briefings and alerts to configured Telegram channels/chats
using the Telegram Bot API via REST requests, with retry logic and rate-limit handling.
"""

import logging
import time
from typing import Any

import requests

from core.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_IDS

logger = logging.getLogger(__name__)

# Base URL for Telegram Bot API
_TG_API_BASE = "https://api.telegram.org/bot{token}"
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class TelegramSender:
    """
    Handles message delivery to Telegram channels/chats.

    Supports Markdown formatting, long message splitting (handled by caller),
    retries on network/rate-limit errors, and multi-chat broadcast.
    """

    def __init__(
        self,
        bot_token: str | None = None,
        chat_ids: list[str] | None = None,
        max_retries: int = 3,
        base_delay: float = 2.0,
    ) -> None:
        self.bot_token = bot_token or TELEGRAM_BOT_TOKEN
        self.chat_ids = chat_ids or TELEGRAM_CHAT_IDS
        self.max_retries = max_retries
        self.base_delay = base_delay

        if not self.bot_token or not self.chat_ids:
            raise ValueError(
                "TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set."
            )

        self.api_base = _TG_API_BASE.format(token=self.bot_token)

    def _post_with_retry(
        self, endpoint: str, payload: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Post a request to the Telegram API with exponential backoff."""
        url = f"{self.api_base}/{endpoint}"
        last_exc: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                response = requests.post(url, json=payload, timeout=30)
                if response.status_code == 200:
                    return response.json()

                if response.status_code in _RETRYABLE_STATUS_CODES:
                    # Respect Telegram retry_after parameter if provided
                    retry_after = self.base_delay * (2 ** (attempt - 1))
                    try:
                        err_json = response.json()
                        if "parameters" in err_json and "retry_after" in err_json["parameters"]:
                            retry_after = float(err_json["parameters"]["retry_after"])
                    except Exception:
                        pass

                    logger.warning(
                        "Telegram %s HTTP %d (attempt %d/%d). Retrying in %.1fs...",
                        endpoint,
                        response.status_code,
                        attempt,
                        self.max_retries,
                        retry_after,
                    )
                    time.sleep(retry_after)
                    continue

                # Non-retryable HTTP error
                response.raise_for_status()

            except requests.exceptions.RequestException as exc:
                last_exc = exc
                if attempt < self.max_retries:
                    delay = self.base_delay * (2 ** (attempt - 1))
                    logger.warning(
                        "Telegram connection error on %s (attempt %d/%d): %s. Retrying in %.1fs...",
                        endpoint,
                        attempt,
                        self.max_retries,
                        exc,
                        delay,
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        "Telegram %s failed after %d attempts: %s",
                        endpoint,
                        self.max_retries,
                        exc,
                    )

        return None

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
        results = []
        for chat_id in self.chat_ids:
            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": disable_preview,
            }

            result = self._post_with_retry("sendMessage", payload)
            if result:
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
            else:
                logger.error("Failed to deliver message to chat %s after retries.", chat_id)

        return results

    def send_photo(
        self,
        photo_url: str,
        caption: str = "",
    ) -> list[dict[str, Any]]:
        """
        Send a photo with optional caption to all configured chats.
        """
        results = []
        for chat_id in self.chat_ids:
            payload = {
                "chat_id": chat_id,
                "photo": photo_url,
                "caption": caption,
                "parse_mode": "Markdown",
            }

            result = self._post_with_retry("sendPhoto", payload)
            if result:
                results.append(result)

        return results

    def verify_bot(self) -> bool:
        """
        Verify that the bot token is valid and can connect to Telegram.
        """
        try:
            url = f"{self.api_base}/getMe"
            response = requests.get(url, timeout=10)
            if response.status_code == 200 and response.json().get("ok"):
                bot_info = response.json().get("result", {})
                logger.info(
                    "Telegram bot verified: @%s (%s)",
                    bot_info.get("username", "?"),
                    bot_info.get("first_name", "?"),
                )
                return True
            logger.error("Failed to verify Telegram bot: %s", response.text)
            return False
        except requests.exceptions.RequestException as exc:
            logger.error("Telegram verification request failed: %s", exc)
            return False
