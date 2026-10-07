"""
SQLite Database Tool — Deduplication & Caching Layer.

Provides persistent storage for article deduplication (never sends the
same article twice) and LLM summary caching (avoids redundant API calls
across runs). Uses the article URL as the unique key.
"""

import json
import logging
import sqlite3
from datetime import datetime, timezone
from typing import Any

from core.config import DB_PATH

logger = logging.getLogger(__name__)

# SQL for creating the articles table
_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS articles (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT    NOT NULL,
    link        TEXT    NOT NULL UNIQUE,
    source      TEXT,
    published   TEXT,
    summary     TEXT,
    companies   TEXT,
    importance  REAL    DEFAULT 0.0,
    created_at  TEXT    NOT NULL
);
"""

_CREATE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_articles_link ON articles(link);
"""

# Summary cache table — stores LLM-generated summaries keyed by article link
# so re-running the agent never re-summarizes the same article.
_CREATE_CACHE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS summary_cache (
    link        TEXT    PRIMARY KEY,
    summary_json TEXT   NOT NULL,
    created_at  TEXT    NOT NULL
);
"""


class NewsDatabase:
    """
    SQLite-backed storage for deduplication and article history.

    Uses the article link as the unique key for deduplication.
    """

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = str(db_path or DB_PATH)
        self._init_db()

    def _init_db(self) -> None:
        """Create tables and indexes if they don't exist."""
        try:
            with self._connect() as conn:
                conn.execute(_CREATE_TABLE_SQL)
                conn.execute(_CREATE_INDEX_SQL)
                conn.execute(_CREATE_CACHE_TABLE_SQL)
                conn.commit()
            logger.info("Database initialized at %s", self.db_path)
        except sqlite3.Error as exc:
            logger.error("Database initialization failed: %s", exc)
            raise

    def _connect(self) -> sqlite3.Connection:
        """Open a connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def filter_new_articles(
        self, articles: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Return only articles whose links are NOT already in the database.
        Uses batched 'WHERE link IN (...)' queries to avoid N+1 query bottlenecks.

        Args:
            articles: List of article dicts (must have 'link' key).

        Returns:
            Subset of articles that are new.
        """
        if not articles:
            return []

        links = [a.get("link", "") for a in articles if a.get("link")]
        if not links:
            return articles

        existing_links: set[str] = set()
        try:
            with self._connect() as conn:
                batch_size = 500
                for i in range(0, len(links), batch_size):
                    batch = links[i : i + batch_size]
                    placeholders = ",".join("?" for _ in batch)
                    rows = conn.execute(
                        f"SELECT link FROM articles WHERE link IN ({placeholders})",
                        batch,
                    ).fetchall()
                    existing_links.update(row["link"] for row in rows)

            new_articles = [
                a for a in articles if a.get("link") and a.get("link") not in existing_links
            ]
        except sqlite3.Error as exc:
            logger.error("Dedup query failed: %s", exc)
            # On error, return all articles to avoid data loss
            return articles

        logger.info(
            "Dedup: %d total → %d new articles (%d already seen).",
            len(articles),
            len(new_articles),
            len(existing_links),
        )
        return new_articles

    def save_articles(self, articles: list[dict[str, Any]]) -> int:
        """
        Insert articles into the database. Skips duplicates silently.
        Accurately counts newly inserted rows using cursor rowcount.

        Args:
            articles: List of article dicts.

        Returns:
            Number of newly inserted rows.
        """
        inserted = 0
        now = datetime.now(timezone.utc).isoformat()

        try:
            with self._connect() as conn:
                for article in articles:
                    try:
                        cursor = conn.execute(
                            """
                            INSERT OR IGNORE INTO articles
                                (title, link, source, published, summary, companies, importance, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                article.get("title", ""),
                                article.get("link", ""),
                                article.get("source", ""),
                                article.get("published", ""),
                                article.get("summary", ""),
                                ",".join(article.get("companies", [])),
                                article.get("importance_score", 0.0),
                                now,
                            ),
                        )
                        if cursor.rowcount > 0:
                            inserted += 1
                    except sqlite3.IntegrityError:
                        # Duplicate link — skip
                        pass
                conn.commit()
        except sqlite3.Error as exc:
            logger.error("Failed to save articles: %s", exc)

        logger.info("Saved %d new articles to database.", inserted)
        return inserted

    def get_recent_articles(
        self, limit: int = 50
    ) -> list[dict[str, Any]]:
        """
        Retrieve the most recent articles from the database.
        """
        return self.get_articles(limit=limit)

    def get_articles(
        self,
        limit: int = 50,
        offset: int = 0,
        company: str | None = None,
        min_importance: float | None = None,
    ) -> list[dict[str, Any]]:
        """
        Retrieve articles with optional filtering and pagination.

        Args:
            limit: Maximum articles to return.
            offset: Pagination offset.
            company: Optional company name substring filter.
            min_importance: Minimum importance score threshold.

        Returns:
            List of article dicts.
        """
        query = "SELECT * FROM articles WHERE 1=1"
        params: list[Any] = []

        if company:
            query += " AND companies LIKE ?"
            params.append(f"%{company}%")

        if min_importance is not None:
            query += " AND importance >= ?"
            params.append(min_importance)

        query += " ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        try:
            with self._connect() as conn:
                rows = conn.execute(query, params).fetchall()
                return [dict(row) for row in rows]
        except sqlite3.Error as exc:
            logger.error("Failed to retrieve articles: %s", exc)
            return []

    def count_articles(self, company: str | None = None) -> int:
        """Return total number of stored articles, optionally filtered by company."""
        query = "SELECT COUNT(*) as cnt FROM articles"
        params: list[Any] = []
        if company:
            query += " WHERE companies LIKE ?"
            params.append(f"%{company}%")

        try:
            with self._connect() as conn:
                row = conn.execute(query, params).fetchone()
                return row["cnt"] if row else 0
        except sqlite3.Error as exc:
            logger.error("Failed to count articles: %s", exc)
            return 0

    # ── Summary Cache ─────────────────────────────────────────────────────

    def get_cached_summaries(
        self, links: list[str]
    ) -> dict[str, dict]:
        """
        Look up previously cached LLM summaries by article link.
        Uses batched IN queries for high throughput.

        Args:
            links: List of article URLs to check.

        Returns:
            Dict mapping link -> summary dict for articles found in cache.
        """
        valid_links = [l for l in links if l]
        if not valid_links:
            return {}

        cached: dict[str, dict] = {}
        try:
            with self._connect() as conn:
                batch_size = 500
                for i in range(0, len(valid_links), batch_size):
                    batch = valid_links[i : i + batch_size]
                    placeholders = ",".join("?" for _ in batch)
                    rows = conn.execute(
                        f"SELECT link, summary_json FROM summary_cache WHERE link IN ({placeholders})",
                        batch,
                    ).fetchall()
                    for row in rows:
                        try:
                            cached[row["link"]] = json.loads(row["summary_json"])
                        except json.JSONDecodeError:
                            pass  # Corrupted cache entry — skip
        except sqlite3.Error as exc:
            logger.error("Cache lookup failed: %s", exc)

        return cached

    def cache_summaries(self, summaries: list[dict]) -> int:
        """
        Store LLM-generated summaries in the cache.

        Args:
            summaries: List of summary dicts (must have 'link' key).

        Returns:
            Number of entries cached.
        """
        if not summaries:
            return 0

        cached_count = 0
        now = datetime.now(timezone.utc).isoformat()

        try:
            with self._connect() as conn:
                for summary in summaries:
                    link = summary.get("link", "")
                    if not link:
                        continue
                    try:
                        conn.execute(
                            """
                            INSERT OR REPLACE INTO summary_cache
                                (link, summary_json, created_at)
                            VALUES (?, ?, ?)
                            """,
                            (link, json.dumps(summary, ensure_ascii=False), now),
                        )
                        cached_count += 1
                    except sqlite3.Error:
                        pass  # Skip individual failures
                conn.commit()
        except sqlite3.Error as exc:
            logger.error("Failed to cache summaries: %s", exc)

        logger.debug("Cached %d summaries.", cached_count)
        return cached_count
