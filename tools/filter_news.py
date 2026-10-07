"""
News Filtering & Importance Scoring Tool.

Filters articles by 15 tracked EPC competitors using regex-based alias matching
with strict boundary checks to avoid substring false positives, then scores
importance using 50+ configurable keyword weights tuned for the energy and
construction sector.
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

# Common English words that can be company names/aliases only when capitalized
# (e.g., "Wood" as the engineering contractor vs "wood chips" / "driftwood")
_TITLECASE_ONLY_TERMS = {"wood"}


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

        # Pre-compile regex patterns for each company with boundary protection
        # (?<![a-zA-Z0-9]) and (?![a-zA-Z0-9]) prevent false positives on substrings
        # (e.g., alias "wood" matching "Hollywood" or alias "lin" matching "online")
        self._patterns: dict[str, list[re.Pattern]] = {}
        for company in self.companies:
            raw_terms = [company] + self.aliases.get(company, [])
            unique_terms = set(raw_terms)

            patterns: list[re.Pattern] = []

            # Split into titlecase-sensitive terms and general case-insensitive terms
            case_sensitive_terms = [
                re.escape(t.capitalize())
                for t in unique_terms
                if t.lower() in _TITLECASE_ONLY_TERMS
            ]
            case_insensitive_terms = [
                re.escape(t)
                for t in unique_terms
                if t.lower() not in _TITLECASE_ONLY_TERMS and t.strip()
            ]

            if case_insensitive_terms:
                # Sort by descending length so multi-word aliases match preferentially
                case_insensitive_terms.sort(key=len, reverse=True)
                ci_pattern_str = rf"(?<![a-zA-Z0-9])(?:{'|'.join(case_insensitive_terms)})(?![a-zA-Z0-9])"
                patterns.append(re.compile(ci_pattern_str, re.IGNORECASE))

            if case_sensitive_terms:
                cs_pattern_str = rf"(?<![a-zA-Z0-9])(?:{'|'.join(case_sensitive_terms)})(?![a-zA-Z0-9])"
                patterns.append(re.compile(cs_pattern_str))

            self._patterns[company] = patterns

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
                kw_lower = keyword.lower()
                if kw_lower in full_text:
                    multiplier = 1.5 if kw_lower in title else 1.0
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
        for company, patterns in self._patterns.items():
            if any(p.search(text) for p in patterns):
                matched.append(company)
        return matched
