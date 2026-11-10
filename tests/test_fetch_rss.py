"""
Unit tests for RSSFetcher in tools/fetch_rss.py.
"""

from tools.fetch_rss import RSSFetcher


def test_clean_html_stripping():
    raw_html = "<p>Fluor awarded <b>$2.5B</b> contract &amp; expansion.&nbsp;Read <a href='https://example.com'>more</a>.</p>"
    cleaned = RSSFetcher._clean_html(raw_html)
    assert "<" not in cleaned
    assert ">" not in cleaned
    assert "Fluor awarded" in cleaned
    assert "&amp;" not in cleaned
    assert "contract & expansion" in cleaned


def test_normalize_entry_valid():
    class MockEntry:
        title = "<h3>Petrofac secures North Africa award</h3>"
        link = "https://example.com/petrofac-news"
        summary = "<div>Engineering study completed.</div>"
        published_parsed = None

    entry = MockEntry()
    normalized = RSSFetcher._normalize_entry(entry, "Offshore Energy")
    assert normalized is not None
    assert normalized["title"] == "Petrofac secures North Africa award"
    assert normalized["link"] == "https://example.com/petrofac-news"
    assert normalized["summary"] == "Engineering study completed."
    assert normalized["source"] == "Offshore Energy"
    assert "published" in normalized


def test_normalize_entry_missing_data():
    class IncompleteEntry:
        title = ""
        link = ""

    assert RSSFetcher._normalize_entry(IncompleteEntry(), "Source") is None


def test_feedparser_fallback_is_bounded_by_timeout(monkeypatch):
    import socket
    import requests
    import tools.fetch_rss as fetch_rss

    def failing_get(*args, **kwargs):
        raise requests.exceptions.ConnectionError("down")

    seen = {}

    class _Feed:
        bozo = False
        entries = []

    def fake_parse(arg):
        seen["timeout"] = socket.getdefaulttimeout()
        return _Feed()

    monkeypatch.setattr(fetch_rss.requests, "get", failing_get)
    monkeypatch.setattr(fetch_rss.feedparser, "parse", fake_parse)

    before = socket.getdefaulttimeout()
    fetcher = RSSFetcher(feeds=[{"name": "x", "url": "https://example.invalid/rss"}], timeout=7)
    assert fetcher._fetch_single_feed("x", "https://example.invalid/rss") == []
    assert seen["timeout"] == 7                      # applied during the fallback parse
    assert socket.getdefaulttimeout() == before      # and restored afterwards
