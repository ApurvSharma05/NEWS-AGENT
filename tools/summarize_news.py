"""
LLM Summarization Tool.

Uses the Google Gemini API to generate concise, actionable summaries
of news articles for the daily digest.

Free tier: 15 requests/minute, 1M tokens/minute — more than enough for daily digests.
"""

import json
import logging
from typing import Any

import requests

from core.config import GEMINI_API_KEY, GEMINI_MODEL

logger = logging.getLogger(__name__)

# Gemini API endpoint (REST, no SDK required)
_GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class NewsSummarizer:
    """
    Summarizes news articles using Google's Gemini API.

    Sends a batch of articles and receives structured summaries
    grouped by company.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self.api_key = api_key or GEMINI_API_KEY
        self.model = model or GEMINI_MODEL

        if not self.api_key:
            raise ValueError(
                "Gemini API key is required for summarization. "
                "Get one free at https://aistudio.google.com/apikey"
            )

    def summarize_batch(
        self,
        articles: list[dict[str, Any]],
        language: str = "english",
    ) -> list[dict]:
        """
        Summarize a batch of articles into concise bullet points.

        Args:
            articles: List of article dicts with title, summary, link, companies.
            language: Target summary language ("english" or "hindi").

        Returns:
            List of dicts with keys: title, summary, link, companies, importance_score.
        """
        if not articles:
            return []

        # Build the article list for the prompt
        article_descriptions = []
        for i, article in enumerate(articles, 1):
            companies = ", ".join(article.get("companies", []))
            score = article.get("importance_score", 0)
            desc = (
                f"{i}. [{companies}] (score: {score})\n"
                f"   Title: {article['title']}\n"
                f"   Source: {article.get('source', 'Unknown')}\n"
                f"   Content: {article.get('summary', 'N/A')[:500]}\n"
                f"   Link: {article.get('link', '')}"
            )
            article_descriptions.append(desc)

        articles_text = "\n\n".join(article_descriptions)

        lang_instruction = ""
        if language.lower() == "hindi":
            lang_instruction = (
                "Write the summaries in Hindi (Devanagari script). "
                "Keep company names and technical terms in English."
            )
        else:
            lang_instruction = "Write the summaries in clear, concise English."

        system_instruction = (
            "You are an expert AI industry analyst. Your job is to create "
            "a concise daily intelligence digest about AI competitor companies. "
            "Focus on what matters: product launches, funding, partnerships, "
            "leadership changes, regulatory actions, and technical breakthroughs. "
            "Skip fluff and opinion pieces.\n\n"
            f"{lang_instruction}"
        )

        user_prompt = (
            f"Summarize each of the following {len(articles)} news articles into "
            "a single concise bullet point (1-2 sentences max). "
            "Preserve the company association and importance score.\n\n"
            "Return your response as a JSON array where each element has:\n"
            '  - "title": original article title\n'
            '  - "summary": your 1-2 sentence summary\n'
            '  - "companies": list of company names\n'
            '  - "importance_score": the original score\n'
            '  - "link": original article link\n\n'
            f"Articles:\n\n{articles_text}\n\n"
            "Respond ONLY with the JSON array, no markdown fences or extra text."
        )

        try:
            result = self._call_gemini(system_instruction, user_prompt)
            summaries = self._parse_response(result, articles)
            return summaries
        except Exception as exc:
            logger.error("Summarization failed: %s", exc, exc_info=True)
            # Fallback: return articles with truncated original summaries
            return self._fallback_summaries(articles)

    def _call_gemini(self, system_instruction: str, user_prompt: str) -> str:
        """
        Make a Gemini generateContent API call via REST.

        Uses the system_instruction field for the system prompt and
        a single user turn for the article data.
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
                "Gemini API error (HTTP %d): %s", response.status_code, error_detail
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

        logger.debug("Gemini response length: %d chars", len(content))
        return content

    @staticmethod
    def _parse_response(
        raw_response: str,
        original_articles: list[dict[str, Any]],
    ) -> list[dict]:
        """
        Parse the JSON array from the LLM response.
        Falls back to original articles on parse failure.
        """
        # Strip markdown code fences if present
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

        # Fallback
        return NewsSummarizer._fallback_summaries(original_articles)

    @staticmethod
    def _fallback_summaries(articles: list[dict[str, Any]]) -> list[dict]:
        """
        Generate fallback summaries using original article data.
        Used when the LLM call fails.
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
