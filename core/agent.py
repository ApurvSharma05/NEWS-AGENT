"""
Orchestrator agent for the EPC Competitor Intelligence pipeline.

Coordinates the full daily digest workflow:
  1. Fetch RSS articles from 24+ energy/EPC industry sources
  2. Filter by 15 tracked competitors using fuzzy alias matching
  3. Deduplicate against SQLite history (never sends the same article twice)
  4. Score importance using 50+ weighted industry keywords
  5. Summarize top 10 articles with Groq LLM for strategic implications
  6. Format and deliver a tight, scannable briefing via Telegram
"""

import logging
from datetime import datetime, timezone

from core.config import (
    TRACKED_COMPANIES,
    DIGEST_MAX_ARTICLES,
    BREAKING_NEWS_THRESHOLD,
    SUMMARY_LANGUAGE,
    validate_config,
)
from tools.fetch_rss import RSSFetcher
from tools.filter_news import NewsFilter
from tools.database import NewsDatabase
from tools.summarize_news import NewsSummarizer
from tools.send_telegram import TelegramSender

logger = logging.getLogger(__name__)


class NewsAgent:
    """
    Main orchestrator that runs the full news monitoring pipeline.

    Each step is handled by a dedicated tool module, making the agent
    extensible — you can swap or add tools without changing the orchestration.
    """

    def __init__(self) -> None:
        # Validate configuration before anything else
        errors = validate_config()
        if errors:
            for err in errors:
                logger.error(f"Config error: {err}")
            raise RuntimeError(
                "Configuration is incomplete. Fix the above errors and retry."
            )

        self.fetcher = RSSFetcher()
        self.filter = NewsFilter()
        self.db = NewsDatabase()
        self.summarizer = NewsSummarizer()
        self.sender = TelegramSender()

        logger.info("NewsAgent initialized. Tracking: %s", TRACKED_COMPANIES)

    # ── Public API ────────────────────────────────────────────────────────

    def run_daily_digest(self) -> None:
        """
        Execute the complete daily digest pipeline.
        """
        logger.info("═" * 60)
        logger.info("Starting daily digest run at %s", datetime.now(timezone.utc).isoformat())
        logger.info("═" * 60)

        # Step 1 — Fetch
        raw_articles = self.fetcher.fetch_all()
        logger.info("Fetched %d raw articles from RSS feeds.", len(raw_articles))

        if not raw_articles:
            logger.warning("No articles fetched. Sending empty-digest notice.")
            self.sender.send_message("📭 *EPC Competitor Digest*\n\nNo articles found today.")
            return

        # Step 2 — Filter by tracked companies
        filtered = self.filter.filter_articles(raw_articles)
        logger.info("Filtered to %d company-relevant articles.", len(filtered))

        if not filtered:
            logger.info("No relevant articles today. Sending notice.")
            self.sender.send_message(
                "📭 *EPC Competitor Digest*\n\nNo relevant competitor news found today."
            )
            return

        # Step 3 — Deduplicate
        new_articles = self.db.filter_new_articles(filtered)
        logger.info("%d new (non-duplicate) articles after dedup.", len(new_articles))

        if not new_articles:
            logger.info("All articles were duplicates. Nothing new to report.")
            return

        # Step 4 — Score importance and sort
        scored = self.filter.score_articles(new_articles)
        scored.sort(key=lambda a: a.get("importance_score", 0), reverse=True)

        # Check for breaking news
        breaking = [a for a in scored if a.get("importance_score", 0) >= BREAKING_NEWS_THRESHOLD]
        if breaking:
            logger.info("🚨 %d breaking-news articles detected!", len(breaking))

        # Cap to digest limit
        top_articles = scored[:DIGEST_MAX_ARTICLES]
        logger.info("Preparing digest with top %d articles.", len(top_articles))

        # Step 5 — Summarize (with caching to avoid redundant API calls)
        summaries = self.summarizer.summarize_batch(
            top_articles, language=SUMMARY_LANGUAGE, cache_db=self.db
        )
        logger.info("Generated %d summaries.", len(summaries))

        # Step 6 — Build and send digest
        digest = self._format_digest(summaries)

        # Telegram has a 4096-char limit per message; split if needed
        chunks = self._split_message(digest, max_length=4000)
        for i, chunk in enumerate(chunks, 1):
            self.sender.send_message(chunk)
            logger.info("Sent digest chunk %d/%d.", i, len(chunks))

        # Step 7 — Persist articles so they won't appear again
        self.db.save_articles(top_articles)
        logger.info("Saved %d articles to database.", len(top_articles))

        logger.info("Daily digest complete. ✅")

    # ── Private helpers ───────────────────────────────────────────────────

    def _format_digest(self, summaries: list[dict]) -> str:
        """
        Format summaries into a clean, tight Telegram update.
        """
        today = datetime.now().strftime("%B %d, %Y")
        lines = [f"🏗️ *EPC Competitor Intelligence — {today}*"]

        # Sort articles by importance score descending
        summaries_sorted = sorted(
            summaries, key=lambda a: a.get("importance_score", 0), reverse=True
        )
        
        if not summaries_sorted:
            lines.append("\nNo high-priority updates.")
            return "\n".join(lines)

        seen_titles = set()
        for article in summaries_sorted:
            title = article.get("title", "Untitled")
            if title in seen_titles:
                continue
            seen_titles.add(title)

            companies_str = ", ".join(article.get("companies", []))
            summary_text = article.get("summary", "")
            implication = article.get("strategic_implication", "")
            link = article.get("link", "")
            score = article.get("importance_score", 0)

            prefix = "🔴" if score >= BREAKING_NEWS_THRESHOLD else "⚡"
            
            lines.append(f"\n{prefix} *{companies_str}*: {summary_text}")
            
            if implication:
                lines.append(f"💡 *Implication*: _{implication}_")
                
            if link:
                lines.append(f"🔗 [Source]({link})")

        lines.append("\n---\n_Technip Energies Competitor Intelligence_")
        return "\n".join(lines)

    @staticmethod
    def _split_message(text: str, max_length: int = 4000) -> list[str]:
        """
        Split a long message into chunks that fit Telegram's per-message limit.
        Splits on newline boundaries to avoid breaking formatting.
        """
        if len(text) <= max_length:
            return [text]

        chunks = []
        current = ""
        for line in text.split("\n"):
            if len(current) + len(line) + 1 > max_length:
                chunks.append(current)
                current = line
            else:
                current = f"{current}\n{line}" if current else line
        if current:
            chunks.append(current)
        return chunks
