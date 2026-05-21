"""
LLM Summarization Tool.

Uses the OpenAI API to generate concise, actionable summaries
of news articles for the daily digest.
"""

import json
import logging
from typing import Any

import requests

from core.config import OPENAI_API_KEY, OPENAI_MODEL

logger = logging.getLogger(__name__)

# OpenAI Chat Completions endpoint
_OPENAI_URL = "https://api.openai.com/v1/chat/completions"


class NewsSummarizer:
    """
    Summarizes news articles using OpenAI's Chat API.

    Sends a batch of articles and receives structured summaries
    grouped by company.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self.api_key = api_key or OPENAI_API_KEY
        self.model = model or OPENAI_MODEL

        if not self.api_key:
            raise ValueError("OpenAI API key is required for summarization.")

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

        system_prompt = (
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
            result = self._call_openai(system_prompt, user_prompt)
            summaries = self._parse_response(result, articles)
            return summaries
        except Exception as exc:
            logger.error("Summarization failed: %s", exc, exc_info=True)
            # Fallback: return articles with truncated original summaries
            return self._fallback_summaries(articles)

    def _call_openai(self, system_prompt: str, user_prompt: str) -> str:
        """
        Make a Chat Completion API call.
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.3,
            "max_tokens": 3000,
        }

        response = requests.post(
            _OPENAI_URL,
            headers=headers,
            json=payload,
            timeout=60,
        )
        response.raise_for_status()

        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()
        logger.debug("OpenAI response length: %d chars", len(content))
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
            # Remove opening and closing fences
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
