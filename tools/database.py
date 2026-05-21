"""
SQLite Database Tool for article deduplication and storage.

Manages a local SQLite database to track which articles have already
been processed, preventing duplicate entries in the digest.
"""

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

        Args:
            articles: List of article dicts (must have 'link' key).

        Returns:
            Subset of articles that are new.
        """
        if not articles:
            return []

        new_articles: list[dict[str, Any]] = []
        try:
            with self._connect() as conn:
                for article in articles:
                    link = article.get("link", "")
                    if not link:
                        continue
                    row = conn.execute(
                        "SELECT 1 FROM articles WHERE link = ?", (link,)
                    ).fetchone()
                    if row is None:
                        new_articles.append(article)
        except sqlite3.Error as exc:
            logger.error("Dedup query failed: %s", exc)
            # On error, return all articles to avoid data loss
            return articles

        logger.info(
            "Dedup: %d total → %d new articles.",
            len(articles),
            len(new_articles),
        )
        return new_articles

    def save_articles(self, articles: list[dict[str, Any]]) -> int:
        """
        Insert articles into the database. Skips duplicates silently.

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
                        conn.execute(
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
                        if conn.total_changes:
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

        Useful for debugging or building a web dashboard later.
        """
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT * FROM articles ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
                return [dict(row) for row in rows]
        except sqlite3.Error as exc:
            logger.error("Failed to retrieve articles: %s", exc)
            return []

    def count_articles(self) -> int:
        """Return total number of stored articles."""
        try:
            with self._connect() as conn:
                row = conn.execute("SELECT COUNT(*) as cnt FROM articles").fetchone()
                return row["cnt"] if row else 0
        except sqlite3.Error as exc:
            logger.error("Failed to count articles: %s", exc)
            return 0
