"""
Tests for the delivery/persistence ordering in core/agent.py (no network:
fetcher, summarizer and Telegram sender are fakes).
"""

import gc
import tempfile
from pathlib import Path

import pytest

from core.agent import NewsAgent
from tools.database import NewsDatabase
from tools.filter_news import NewsFilter


class _FakeFetcher:
    def __init__(self, articles):
        self.articles = articles

    def fetch_all(self):
        return [dict(a) for a in self.articles]


class _FakeSummarizer:
    def summarize_batch(self, articles, language="english", cache_db=None):
        return [{**a, "strategic_implication": "x"} for a in articles]

    def get_metrics(self):
        return {}


class _FakeSender:
    def __init__(self, response):
        self.response = response
        self.sent = []

    def send_message(self, text, **kwargs):
        self.sent.append(text)
        return self.response


def _articles(n):
    return [
        {"title": f"Saipem wins contract {i}", "summary": "LNG project", "link": f"https://example.com/{i}"}
        for i in range(n)
    ]


@pytest.fixture
def make_agent():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db = NewsDatabase(db_path=str(Path(tmpdir) / "t.db"))

        def _make(sender_response, n=12):
            agent = NewsAgent.__new__(NewsAgent)  # skip config validation / real clients
            agent.fetcher = _FakeFetcher(_articles(n))
            agent.filter = NewsFilter()
            agent.db = db
            agent.summarizer = _FakeSummarizer()
            agent.sender = _FakeSender(sender_response)
            return agent

        yield _make, db
        gc.collect()


@pytest.mark.parametrize("response", [[], [{"ok": False, "description": "blocked"}]])
def test_failed_send_saves_nothing_and_retries_next_run(make_agent, response):
    make, db = make_agent
    result = make(response).run_daily_digest()

    assert result["status"] == "delivery_failed"
    assert result["articles_saved"] == 0
    assert db.count_articles() == 0

    # Nothing was persisted, so the next run sees the same articles as new.
    retry = make([{"ok": True}]).run_daily_digest()
    assert retry["status"] == "success"
    assert retry["new_articles"] == 12


def test_successful_send_saves_delivered_and_marks_all_seen(make_agent):
    make, db = make_agent
    result = make([{"ok": True}]).run_daily_digest()

    assert result["status"] == "success"
    assert result["articles_saved"] == 10            # delivered top 10
    assert result["articles_marked_seen"] == 12      # every processed link
    assert db.count_articles() == 10

    # Dedup is real: even the 2 articles below the cut-off are no longer "new".
    again = make([{"ok": True}]).run_daily_digest()
    assert again["status"] == "all_duplicates"
    assert again["new_articles"] == 0
