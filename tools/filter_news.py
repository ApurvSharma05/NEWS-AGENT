"""
News Filtering & Importance Scoring Tool.

Filters articles by 15 tracked EPC competitors using regex-based fuzzy
alias matching, then scores importance using 50+ configurable keyword
weights tuned for the energy and construction sector.
"""

import logging
import re
from typing import Any

from core.config import (
    TRACKED_COMPANIES,
    COMPANY_ALIASES,
    KEYWORD_WEIGHTS,
)

logger = logging.getLogger(__name__)


class NewsFilter:
    """
    Filters and scores news articles based on company relevance and importance.
    """

    def __init__(
        self,
        companies: list[str] | None = None,
        aliases: dict[str, list[str]] | None = None,
        keyword_weights: dict[str, float] | None = None,
    ) -> None:
        self.companies = companies or TRACKED_COMPANIES
        self.aliases = aliases or COMPANY_ALIASES
        self.keyword_weights = keyword_weights or KEYWORD_WEIGHTS

        # Pre-compile regex patterns for each company
        self._patterns: dict[str, re.Pattern] = {}
        for company in self.companies:
            terms = [re.escape(company)]
            for alias in self.aliases.get(company, []):
                terms.append(re.escape(alias))
            pattern = re.compile("|".join(terms), re.IGNORECASE)
            self._patterns[company] = pattern

    def filter_articles(
        self, articles: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Keep only articles that mention at least one tracked company.
        Adds a 'companies' key with the list of matched companies.

        Args:
            articles: Raw article dicts from the fetcher.

        Returns:
            Filtered articles with company tags.
        """
        filtered: list[dict[str, Any]] = []

        for article in articles:
            text = f"{article.get('title', '')} {article.get('summary', '')}"
            matched_companies = self._match_companies(text)

            if matched_companies:
                article["companies"] = matched_companies
                filtered.append(article)

        logger.info(
            "Filtered %d → %d company-relevant articles.",
            len(articles),
            len(filtered),
        )
        return filtered

    def score_articles(
        self, articles: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Compute an importance score for each article based on keyword weights
        and company mention count.

        Scoring formula:
          base = sum of keyword weight for every keyword found
          company_bonus = 1.0 per unique company mentioned
          title_bonus = 1.5× multiplier if keyword is in the title

        Args:
            articles: Company-filtered articles.

        Returns:
            Same articles with an 'importance_score' field added.
        """
        for article in articles:
            title = article.get("title", "").lower()
            summary = article.get("summary", "").lower()
            full_text = f"{title} {summary}"

            score = 0.0

            # Keyword scoring
            for keyword, weight in self.keyword_weights.items():
                if keyword.lower() in full_text:
                    multiplier = 1.5 if keyword.lower() in title else 1.0
                    score += weight * multiplier

            # Company mention bonus
            companies = article.get("companies", [])
            score += len(companies) * 1.0

            article["importance_score"] = round(score, 2)

        return articles

    def _match_companies(self, text: str) -> list[str]:
        """
        Find all tracked companies mentioned in the text.
        """
        matched = []
        for company, pattern in self._patterns.items():
            if pattern.search(text):
                matched.append(company)
        return matched
