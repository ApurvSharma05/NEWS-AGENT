"""
RSS Feed Fetcher Tool.

Fetches and normalizes articles from configured industry RSS feeds and
Google News competitor-specific searches.
Designed as a standalone, reusable tool module with timeout protection,
user-agent headers, and BeautifulSoup HTML cleaning.
"""

import logging
import re
from datetime import datetime, timezone
from time import mktime
from typing import Any

from bs4 import BeautifulSoup
import feedparser
import requests

from core.config import RSS_FEEDS, MAX_ARTICLES_PER_FEED

logger = logging.getLogger(__name__)

# Default request timeout in seconds for fetching feeds
_FEED_REQUEST_TIMEOUT = 15

# Default browser-like User-Agent to avoid HTTP 403 blocks from news feeds
_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36 EPCIntelligenceBot/2.0"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}

_HTML_TAG_RE = re.compile(r"<[^>]+>")


class RSSFetcher:
    """
    Fetches articles from multiple RSS feeds and returns a normalized list.

    Each article dict contains:
        - title: str
        - link: str
        - summary: str  (cleaned text summary / description)
        - source: str    (feed name)
        - published: str  (ISO 8601)
    """

    def __init__(
        self,
        feeds: list[dict[str, str]] | None = None,
        timeout: int = _FEED_REQUEST_TIMEOUT,
    ) -> None:
        self.feeds = feeds or RSS_FEEDS
        self.timeout = timeout

    def fetch_all(self) -> list[dict[str, Any]]:
        """
        Fetch articles from all configured feeds.

        Returns:
            A list of normalized article dictionaries.
        """
        all_articles: list[dict[str, Any]] = []

        for feed_cfg in self.feeds:
            name = feed_cfg["name"]
            url = feed_cfg["url"]
            try:
                articles = self._fetch_single_feed(name, url)
                all_articles.extend(articles)
                logger.info("Fetched %d articles from %s", len(articles), name)
            except Exception as exc:
                logger.error("Failed to fetch %s: %s", name, exc, exc_info=True)

        return all_articles

    def _fetch_single_feed(
        self, name: str, url: str
    ) -> list[dict[str, Any]]:
        """
        Fetch and parse a single RSS feed with timeout protection.
        """
        feed_content = None

        # Fetch with requests first to enforce strict timeout and headers
        try:
            resp = requests.get(
                url,
                headers=_DEFAULT_HEADERS,
                timeout=self.timeout,
            )
            if resp.status_code == 200:
                feed_content = resp.content
            else:
                logger.warning(
                    "Feed %s returned HTTP %d, falling back to direct feedparser",
                    name,
                    resp.status_code,
                )
        except requests.exceptions.RequestException as req_err:
            logger.warning(
                "Network request failed for %s (%s). Attempting feedparser fallback...",
                name,
                req_err,
            )

        # Parse feed content (from bytes if fetched, or fallback to url)
        if feed_content is not None:
            feed = feedparser.parse(feed_content)
        else:
            feed = feedparser.parse(url)

        if feed.bozo and not feed.entries:
            logger.warning("Feed %s returned bozo error: %s", name, getattr(feed, "bozo_exception", "Unknown XML error"))
            return []

        articles: list[dict[str, Any]] = []
        for entry in feed.entries[:MAX_ARTICLES_PER_FEED]:
            article = self._normalize_entry(entry, name)
            if article:
                articles.append(article)

        return articles

    @staticmethod
    def _clean_html(text: str) -> str:
        """Strip HTML tags and convert HTML entities into clean text."""
        if not text:
            return ""
        try:
            soup = BeautifulSoup(text, "html.parser")
            cleaned = soup.get_text(separator=" ", strip=True)
            return cleaned
        except Exception:
            return _HTML_TAG_RE.sub(" ", text).strip()

    @classmethod
    def _normalize_entry(cls, entry: Any, source: str) -> dict[str, Any] | None:
        """
        Convert a feedparser entry into a clean, normalized article dict.
        """
        title_raw = getattr(entry, "title", "") or ""
        link = getattr(entry, "link", "") or ""

        if not title_raw or not link:
            return None

        title = cls._clean_html(title_raw)

        # Extract summary — prefer 'summary', fall back to 'description'
        raw_summary = (
            getattr(entry, "summary", "")
            or getattr(entry, "description", "")
            or ""
        )
        summary = cls._clean_html(raw_summary)

        # Truncate very long summaries to keep token usage bounded
        if len(summary) > 1000:
            summary = summary[:1000] + "…"

        # Parse published date
        published_parsed = getattr(entry, "published_parsed", None)
        if published_parsed:
            try:
                published = datetime.fromtimestamp(
                    mktime(published_parsed), tz=timezone.utc
                ).isoformat()
            except (ValueError, OverflowError, OSError):
                published = datetime.now(timezone.utc).isoformat()
        else:
            published = datetime.now(timezone.utc).isoformat()

        return {
            "title": title.strip(),
            "link": link.strip(),
            "summary": summary.strip(),
            "source": source,
            "published": published,
        }
