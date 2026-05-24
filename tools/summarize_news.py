"""
LLM Summarization Tool — Production-grade with rate limiting.

Uses the Google Gemini API to generate concise, actionable summaries
of news articles for the daily digest.

Rate-limit resilient:
  - Exponential backoff retry on 429/500/503 errors
  - Smart batching (chunks of GEMINI_BATCH_SIZE articles per API call)
  - Inter-batch cooldown to respect RPM limits
  - Summary caching via SQLite to avoid redundant API calls
  - Graceful fallback to raw summaries on persistent failure
"""

import json
import logging
import time
from typing import Any

import requests

from core.config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    GEMINI_BATCH_SIZE,
    GEMINI_RETRY_ATTEMPTS,
    GEMINI_RETRY_BASE_DELAY,
    GEMINI_COOLDOWN_DELAY,
)

logger = logging.getLogger(__name__)

# Gemini API endpoint (REST, no SDK required)
_GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

# HTTP status codes that should trigger a retry
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503}

# Cooldown between batch API calls (seconds) to stay under RPM
_INTER_BATCH_COOLDOWN = GEMINI_COOLDOWN_DELAY


class NewsSummarizer:
    """
    Summarizes news articles using Google's Gemini API.

    Production-grade features:
      - Exponential backoff with jitter on rate limit errors
      - Smart batching to stay under token limits
      - SQLite-based summary caching to avoid redundant API calls
      - Fallback to raw summaries on persistent failure
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self.api_key = api_key or GEMINI_API_KEY
        self.model = model or GEMINI_MODEL
        self.max_retries = GEMINI_RETRY_ATTEMPTS
        self.base_delay = GEMINI_RETRY_BASE_DELAY

        if not self.api_key:
            raise ValueError(
                "Gemini API key is required for summarization. "
                "Get one free at https://aistudio.google.com/apikey"
            )

    # ── Public API ────────────────────────────────────────────────────────

    def summarize_batch(
        self,
        articles: list[dict[str, Any]],
        language: str = "english",
        cache_db: Any = None,
    ) -> list[dict]:
        """
        Summarize a batch of articles into concise bullet points.

        Uses SQLite caching (if cache_db provided) to skip articles that
        have already been summarized in a previous run.

        Args:
            articles: List of article dicts with title, summary, link, companies.
            language: Target summary language ("english" or "hindi").
            cache_db: Optional NewsDatabase instance for summary caching.

        Returns:
            List of dicts with keys: title, summary, link, companies, importance_score.
        """
        if not articles:
            return []

        # ── Step 1: Check cache for already-summarized articles ──────────
        cached_summaries: list[dict] = []
        uncached_articles: list[dict] = articles

        if cache_db is not None:
            try:
                cached_map = cache_db.get_cached_summaries(
                    [a.get("link", "") for a in articles]
                )
                cached_summaries = []
                uncached_articles = []

                for article in articles:
                    link = article.get("link", "")
                    if link in cached_map:
                        cached_summaries.append(cached_map[link])
                        logger.debug("Cache hit for: %s", article.get("title", "")[:60])
                    else:
                        uncached_articles.append(article)

                logger.info(
                    "Summary cache: %d hits, %d misses.",
                    len(cached_summaries),
                    len(uncached_articles),
                )
            except Exception as exc:
                logger.warning("Cache lookup failed, summarizing all: %s", exc)
                uncached_articles = articles

        if not uncached_articles:
            logger.info("All articles found in cache. No API calls needed.")
            return cached_summaries

        # ── Step 2: Split uncached articles into manageable batches ───────
        batches = self._split_into_batches(uncached_articles, GEMINI_BATCH_SIZE)
        logger.info(
            "Splitting %d uncached articles into %d batch(es) of ≤%d.",
            len(uncached_articles),
            len(batches),
            GEMINI_BATCH_SIZE,
        )

        # ── Step 3: Process each batch with rate-limit-aware calls ───────
        all_summaries: list[dict] = []

        for batch_idx, batch in enumerate(batches, 1):
            logger.info(
                "Processing batch %d/%d (%d articles)...",
                batch_idx,
                len(batches),
                len(batch),
            )

            try:
                batch_summaries = self._summarize_single_batch(batch, language)
                all_summaries.extend(batch_summaries)

                # Cache the fresh summaries
                if cache_db is not None:
                    try:
                        cache_db.cache_summaries(batch_summaries)
                    except Exception as exc:
                        logger.warning("Failed to cache summaries: %s", exc)

            except Exception as exc:
                logger.error(
                    "Batch %d/%d failed after retries: %s",
                    batch_idx,
                    len(batches),
                    exc,
                )
                # Fallback for this batch
                all_summaries.extend(self._fallback_summaries(batch))

            # Inter-batch cooldown (skip after the last batch)
            if batch_idx < len(batches):
                logger.debug(
                    "Cooling down %.1fs before next batch...",
                    _INTER_BATCH_COOLDOWN,
                )
                time.sleep(_INTER_BATCH_COOLDOWN)

        # ── Step 4: Merge cached + fresh summaries ───────────────────────
        return cached_summaries + all_summaries

    # ── Private: Single batch summarization ───────────────────────────────

    def _summarize_single_batch(
        self,
        articles: list[dict[str, Any]],
        language: str,
    ) -> list[dict]:
        """
        Summarize a single batch of articles (≤ GEMINI_BATCH_SIZE).
        Includes retry logic with exponential backoff.
        """
        system_instruction, user_prompt = self._build_prompts(articles, language)

        raw_response = self._call_gemini_with_retry(system_instruction, user_prompt)
        summaries = self._parse_response(raw_response, articles)
        return summaries

    def _build_prompts(
        self,
        articles: list[dict[str, Any]],
        language: str,
    ) -> tuple[str, str]:
        """Build compact, token-efficient prompts for the Gemini API."""

        # Compact article descriptions to minimize tokens
        article_lines = []
        for i, article in enumerate(articles, 1):
            companies = ",".join(article.get("companies", []))
            # Truncate content aggressively to save tokens
            content = article.get("summary", "")[:300]
            article_lines.append(
                f"{i}.[{companies}] {article['title']} | "
                f"{article.get('source', '?')} | "
                f"{content}"
            )

        articles_text = "\n".join(article_lines)

        lang_note = (
            "Reply in Hindi (Devanagari). Keep names/tech terms in English."
            if language.lower() == "hindi"
            else ""
        )

        system_instruction = (
            "You are a Senior Strategy Analyst at Technip Energies NV. "
            "Create concise competitive intelligence summaries about your EPC peers "
            "(e.g., Saipem, Fluor, Bechtel, Wood, MAIRE). "
            "Focus strictly on strategic value: contract awards, project milestones, M&A, "
            "partnerships, leadership changes, financial results, and energy transition moves. "
            f"Skip opinion/fluff. {lang_note}"
        )

        user_prompt = (
            f"Summarize these {len(articles)} competitor articles (1-2 sentences each).\n"
            "For each, assign a 'category' (choose from: CONTRACT_WIN, M&A, EXPANSION, LEADERSHIP, FINANCIAL, RISK, TECH_CAPABILITY, PARTNERSHIP, OTHER).\n"
            "Also provide a 'strategic_implication' (1 sentence: what this means for Technip Energies' competitive position).\n"
            "CRITICAL: You must return a STRICTLY VALID JSON array. Do not use trailing commas. Ensure all property names are enclosed in double quotes.\n"
            "Return JSON array exactly like this: [{\"title\":\"string\",\"summary\":\"string\","
            "\"companies\":[\"string\"],\"importance_score\":0.0,\"link\":\"string\","
            "\"category\":\"string\",\"strategic_implication\":\"string\"}]\n\n"
            f"{articles_text}"
        )

        return system_instruction, user_prompt

    # ── Private: Gemini API call with exponential backoff ─────────────────

    def _call_gemini_with_retry(
        self,
        system_instruction: str,
        user_prompt: str,
    ) -> str:
        """
        Make a Gemini API call with exponential backoff retry.

        Retry strategy:
          - Attempt 1: immediate
          - Attempt 2: wait base_delay * 1   (5s)
          - Attempt 3: wait base_delay * 3   (15s)
          - Attempt 4: wait base_delay * 9   (45s)

        Only retries on 429, 500, 502, 503 status codes.
        """
        last_exception: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                return self._call_gemini(system_instruction, user_prompt)

            except requests.exceptions.HTTPError as exc:
                status_code = exc.response.status_code if exc.response is not None else 0

                if status_code not in _RETRYABLE_STATUS_CODES:
                    # Non-retryable error (400, 401, 403, etc.) — fail immediately
                    logger.error(
                        "Non-retryable Gemini error (HTTP %d): %s",
                        status_code,
                        exc,
                    )
                    raise

                last_exception = exc

                if attempt < self.max_retries:
                    # Exponential backoff: delay * 3^(attempt-1)
                    delay = self.base_delay * (3 ** (attempt - 1))
                    logger.warning(
                        "Gemini 429/5xx (attempt %d/%d). "
                        "Retrying in %.1fs... [HTTP %d]",
                        attempt,
                        self.max_retries,
                        delay,
                        status_code,
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        "Gemini API failed after %d attempts. Last error: HTTP %d",
                        self.max_retries,
                        status_code,
                    )

            except requests.exceptions.RequestException as exc:
                last_exception = exc

                if attempt < self.max_retries:
                    delay = self.base_delay * (3 ** (attempt - 1))
                    logger.warning(
                        "Network error (attempt %d/%d). Retrying in %.1fs...: %s",
                        attempt,
                        self.max_retries,
                        delay,
                        exc,
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        "Network error persisted after %d attempts: %s",
                        self.max_retries,
                        exc,
                    )

        raise last_exception  # type: ignore[misc]

    def _call_gemini(self, system_instruction: str, user_prompt: str) -> str:
        """
        Make a single Gemini generateContent API call via REST.
        """
        url = _GEMINI_URL.format(model=self.model)
        params = {"key": self.api_key}

        payload = {
            "system_instruction": {
                "parts": [{"text": system_instruction}]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_prompt}],
                }
            ],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 4000,
                "responseMimeType": "application/json",
            },
        }

        response = requests.post(
            url,
            params=params,
            json=payload,
            timeout=90,
        )

        if response.status_code != 200:
            error_detail = response.text[:500]
            logger.error(
                "Gemini API error (HTTP %d): %s",
                response.status_code,
                error_detail,
            )
            response.raise_for_status()

        data = response.json()

        # Extract text from Gemini response structure
        try:
            content = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except (KeyError, IndexError) as exc:
            logger.error("Unexpected Gemini response structure: %s", exc)
            logger.debug("Full response: %s", json.dumps(data)[:1000])
            raise ValueError(f"Could not parse Gemini response: {exc}") from exc

        logger.debug("Gemini response: %d chars", len(content))
        return content

    # ── Private: Helpers ──────────────────────────────────────────────────

    @staticmethod
    def _split_into_batches(
        articles: list[dict[str, Any]],
        batch_size: int,
    ) -> list[list[dict[str, Any]]]:
        """Split articles into chunks of batch_size."""
        return [
            articles[i : i + batch_size]
            for i in range(0, len(articles), batch_size)
        ]

    @staticmethod
    def _parse_response(
        raw_response: str,
        original_articles: list[dict[str, Any]],
    ) -> list[dict]:
        """
        Parse the JSON array from the LLM response.
        Falls back to original articles on parse failure.
        """
        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            cleaned = "\n".join(lines)

        try:
            summaries = json.loads(cleaned)
            if isinstance(summaries, list):
                return summaries
        except json.JSONDecodeError as exc:
            logger.warning("Failed to parse LLM JSON response: %s", exc)

        return NewsSummarizer._fallback_summaries(original_articles)

    @staticmethod
    def _fallback_summaries(articles: list[dict[str, Any]]) -> list[dict]:
        """
        Generate fallback summaries using original article data.
        Used when the LLM call fails after all retries.
        """
        fallbacks = []
        for article in articles:
            summary_text = article.get("summary", "")
            if len(summary_text) > 200:
                summary_text = summary_text[:200] + "…"
            fallbacks.append({
                "title": article.get("title", "Untitled"),
                "summary": summary_text or article.get("title", ""),
                "companies": article.get("companies", []),
                "importance_score": article.get("importance_score", 0),
                "link": article.get("link", ""),
            })
        return fallbacks
