"""
Unit tests for NewsFilter in tools/filter_news.py.
"""

import pytest
from tools.filter_news import NewsFilter


@pytest.fixture
def news_filter():
    return NewsFilter()


def test_filter_positive_company_match(news_filter):
    articles = [
        {"title": "Saipem wins major offshore contract", "summary": "Details about Qatar LNG.", "link": "https://example.com/1"},
        {"title": "Unrelated weather update", "summary": "Sunny day in London.", "link": "https://example.com/2"},
    ]
    result = news_filter.filter_articles(articles)
    assert len(result) == 1
    assert result[0]["title"] == "Saipem wins major offshore contract"
    assert "Saipem" in result[0]["companies"]


def test_alias_matching(news_filter):
    articles = [
        {"title": "SNC-Lavalin legacy contracts update", "summary": "Reviewing execution.", "link": "https://example.com/snc"},
        {"title": "CB&I awarded storage tank project", "summary": "LNG cryogenic tanks.", "link": "https://example.com/cbi"},
        {"title": "L&T Hydrocarbon wins mega project", "summary": "Gas plant in Saudi Arabia.", "link": "https://example.com/lt"},
    ]
    result = news_filter.filter_articles(articles)
    assert len(result) == 3
    assert "AtkinsRealis" in result[0]["companies"]
    assert "McDermott" in result[1]["companies"]
    assert "Larsen & Toubro" in result[2]["companies"]


def test_false_positive_substring_prevention(news_filter):
    """Verify that short aliases like 'lin', 'wood', 'flr' do not trigger false alarms on substrings."""
    distractors = [
        {"title": "Hollywood box office surge", "summary": "Summer movie releases.", "link": "https://example.com/h"},
        {"title": "Online banking system maintenance", "summary": "Platform operational again.", "link": "https://example.com/o"},
        {"title": "Airline passenger demand rises", "summary": "Jet fuel consumption climbs.", "link": "https://example.com/a"},
        {"title": "Fire breaks out in Oregon woodland", "summary": "Forestry report.", "link": "https://example.com/w"},
        {"title": "Driftwood sculptures in art museum", "summary": "Coastal crafts.", "link": "https://example.com/d"},
        {"title": "Biomass facility using wood chips", "summary": "Boiler conversion complete.", "link": "https://example.com/wc"},
    ]
    result = news_filter.filter_articles(distractors)
    assert len(result) == 0


def test_score_articles_calculation(news_filter):
    articles = [
        {
            "title": "Saipem awarded billion contract",
            "summary": "Major LNG project underway.",
            "companies": ["Saipem"],
        }
    ]
    scored = news_filter.score_articles(articles)
    assert len(scored) == 1
    score = scored[0]["importance_score"]
    # "contract": 3.0 * 1.5 (title) = 4.5
    # "awarded": 3.5 * 1.5 (title) = 5.25
    # "billion": 2.0 * 1.5 (title) = 3.0
    # "lng": 2.5 * 1.0 (summary) = 2.5
    # "project": 1.5 * 1.0 (summary) = 1.5
    # company bonus: 1.0
    # Total = 4.5 + 5.25 + 3.0 + 2.5 + 1.5 + 1.0 = 17.75
    assert score == pytest.approx(17.75, abs=0.1)


def test_empty_articles_input(news_filter):
    assert news_filter.filter_articles([]) == []
    assert news_filter.score_articles([]) == []
