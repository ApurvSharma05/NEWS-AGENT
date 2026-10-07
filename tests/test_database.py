"""
Unit tests for NewsDatabase in tools/database.py.
"""

import gc
import tempfile
from pathlib import Path
import pytest

from tools.database import NewsDatabase


@pytest.fixture
def temp_db():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_file = Path(tmpdir) / "test_news.db"
        db = NewsDatabase(db_path=str(db_file))
        yield db
        # Ensure SQLite file locks are released on Windows before exit
        del db
        gc.collect()


def test_database_initialization(temp_db):
    assert Path(temp_db.db_path).exists()
    assert temp_db.count_articles() == 0


def test_save_and_count_articles(temp_db):
    sample_articles = [
        {
            "title": "Fluor wins FEED project",
            "link": "https://example.com/fluor-1",
            "source": "Offshore Energy",
            "published": "2026-10-01T12:00:00Z",
            "summary": "Engineering study for green hydrogen.",
            "companies": ["Fluor"],
            "importance_score": 15.5,
        },
        {
            "title": "Bechtel begins LNG construction",
            "link": "https://example.com/bechtel-1",
            "source": "LNG Industry",
            "published": "2026-10-02T12:00:00Z",
            "summary": "Terminal construction under notice to proceed.",
            "companies": ["Bechtel"],
            "importance_score": 18.0,
        },
    ]

    inserted = temp_db.save_articles(sample_articles)
    assert inserted == 2
    assert temp_db.count_articles() == 2

    # Attempt inserting duplicates — should return 0 new inserts
    re_inserted = temp_db.save_articles(sample_articles)
    assert re_inserted == 0
    assert temp_db.count_articles() == 2


def test_filter_new_articles_deduplication(temp_db):
    existing = [
        {"title": "Article A", "link": "https://example.com/a", "companies": ["Saipem"]},
    ]
    temp_db.save_articles(existing)

    incoming = [
        {"title": "Article A", "link": "https://example.com/a", "companies": ["Saipem"]},
        {"title": "Article B", "link": "https://example.com/b", "companies": ["Worley"]},
    ]

    new_articles = temp_db.filter_new_articles(incoming)
    assert len(new_articles) == 1
    assert new_articles[0]["link"] == "https://example.com/b"


def test_summary_cache(temp_db):
    summaries = [
        {
            "title": "Technip Rival Award",
            "link": "https://example.com/award-1",
            "summary": "Saipem awarded deal.",
            "companies": ["Saipem"],
            "strategic_implication": "Competitor expands backlog.",
            "importance_score": 20.0,
        }
    ]

    cached_count = temp_db.cache_summaries(summaries)
    assert cached_count == 1

    lookup = temp_db.get_cached_summaries(["https://example.com/award-1", "https://example.com/missing"])
    assert "https://example.com/award-1" in lookup
    assert lookup["https://example.com/award-1"]["strategic_implication"] == "Competitor expands backlog."
    assert "https://example.com/missing" not in lookup


def test_get_articles_pagination_and_filter(temp_db):
    articles = [
        {"title": f"Article {i}", "link": f"https://example.com/{i}", "companies": ["Saipem" if i % 2 == 0 else "Fluor"], "importance_score": float(i)}
        for i in range(10)
    ]
    temp_db.save_articles(articles)

    all_articles = temp_db.get_articles(limit=5, offset=0)
    assert len(all_articles) == 5

    saipem_only = temp_db.get_articles(company="Saipem")
    assert len(saipem_only) == 5
    assert all("Saipem" in a["companies"] for a in saipem_only)
