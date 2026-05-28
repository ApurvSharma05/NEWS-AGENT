"""
RSS Feed Fetcher Tool.

Fetches and normalizes articles from 24+ configured RSS feeds including
8 industry publications and 15 Google News competitor-specific searches.
Designed as a standalone, reusable tool module.
"""

import logging
from datetime import datetime, timezone
from time import mktime
from typing import Any

import feedparser

from core.config import RSS_FEEDS, MAX_ARTICLES_PER_FEED

logger = logging.getLogger(__name__)


class RSSFetcher:
    """
    Fetches articles from multiple RSS feeds and returns a normalized list.

    Each article dict contains:
        - title: str
        - link: str
        - summary: str  (raw RSS summary / description)
        - source: str    (feed name)
        - published: str  (ISO 8601)
    """

    def __init__(self, feeds: list[dict[str, str]] | None = None) -> None:
        self.feeds = feeds or RSS_FEEDS

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
        Parse a single RSS feed and return normalized articles.
        """
        feed = feedparser.parse(url)

        if feed.bozo and not feed.entries:
            logger.warning("Feed %s returned bozo error: %s", name, feed.bozo_exception)
            return []

        articles: list[dict[str, Any]] = []
        for entry in feed.entries[:MAX_ARTICLES_PER_FEED]:
            article = self._normalize_entry(entry, name)
            if article:
                articles.append(article)

        return articles

    @staticmethod
    def _normalize_entry(entry: Any, source: str) -> dict[str, Any] | None:
        """
        Convert a feedparser entry into a clean article dict.
        """
        title = getattr(entry, "title", "") or ""
        link = getattr(entry, "link", "") or ""

        if not title or not link:
            return None

        # Extract summary — prefer 'summary', fall back to 'description'
        summary = (
            getattr(entry, "summary", "")
            or getattr(entry, "description", "")
            or ""
        )
        # Strip HTML tags from summary (lightweight approach)
        import re
        summary = re.sub(r"<[^>]+>", "", summary).strip()
        # Truncate very long summaries
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
            "summary": summary,
            "source": source,
            "published": published,
        }
