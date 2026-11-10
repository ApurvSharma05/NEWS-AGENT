# 🏗️ EPC Competitor Intelligence Agent

An autonomous AI-powered competitive intelligence system that monitors **23 news feeds daily (~880 articles per run)**, extracts strategic implications using **Llama 3.3 70B** via Groq, provides a **FastAPI REST backend**, and delivers actionable briefings to Telegram — built for the EPC (Engineering, Procurement & Construction) energy sector.

![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?logo=fastapi&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED.svg?logo=docker&logoColor=white)
![Pytest](https://img.shields.io/badge/Pytest-30%2F30%20Passing-success.svg?logo=pytest&logoColor=white)
![Evaluation: 100% Precision](https://img.shields.io/badge/Eval-100%25%20F1--Score-brightgreen.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)

---

## 🎯 What It Does

This agent acts as an autonomous **Senior Strategy Analyst** for **Technip Energies NV** — it doesn't just summarize news, it extracts *strategic threats and competitive implications*:

```text
⚡ Fluor, JGC Holdings: Fluor-JGC JV awarded FEED contract for
  LNG Canada Phase 2 expansion (28 MTPA capacity doubling).
💡 Implication: Solidifies the Fluor-JGC partnership's dominance in
  North American LNG, intensifying competition for Technip Energies
  in securing future large-scale LNG FEED and EPC contracts.
🔗 Source: https://...
```

> **Key Differentiator:** Unlike generic news scrapers, every article undergoes domain-specific filtering with boundary-protected alias matching, keyword-weighted scoring, deduplication, and LLM-powered strategic framing.

---

## 📊 Evaluation & Benchmarks

The filtering and entity-detection pipeline is verified against a 100-sample ground-truth golden dataset (`eval/golden_dataset.json`), evaluating detection against real industry headlines and adversarial distractors (e.g., words like *"Hollywood"*, *"wood chips"*, *"online"*, and general oil supermajor news):

| Metric | Measured Value | Target | Notes |
|---|---|---|---|
| **Precision** | **100.00%** | ≥ 95% | Zero false positives on tricky sub-words (*"wood"*, *"lin"*, etc.) |
| **Recall** | **100.00%** | ≥ 95% | 50/50 competitor articles correctly recognized across all 15 firms |
| **F1-Score** | **100.00%** | ≥ 95% | Harmonic mean of precision and recall |
| **Accuracy** | **100.00%** | ≥ 95% | Overall dataset classification accuracy |
| **Specificity** | **100.00%** | ≥ 95% | Distractor rejection rate (50/50 negative samples rejected) |
| **Entity Matching** | **100.00%** | ≥ 95% | Exact competitor identification across all aliases |
| **Throughput** | **~22,000 art/sec** | ≥ 1,000 | Pre-compiled regex with titlecase distinction (varies by run and machine) |
| **Latency** | **~0.045 ms / article** | < 1 ms | Measured 0.044-0.045 ms on the last runs; expect roughly 0.04-0.05 ms |

These metrics are for the company-entity filter on a self-made dataset (not real-world accuracy); keyword scoring is covered by unit tests, not by this benchmark.

Run the evaluation benchmark locally:
```bash
python eval/evaluate_filter.py
```

---

## 🏗️ Architecture

```mermaid
flowchart TD
    CLI["🖥️ CLI / Cron / Task Scheduler\npython main.py"]
    API["🌐 FastAPI REST API\nuvicorn api.main:app"]
    
    CLI --> AGENT["NewsAgent Orchestrator\ncore/agent.py"]
    API --> AGENT
    API --> DB["SQLite Database\ntools/database.py"]

    AGENT --> STEP1["① RSS Fetcher\ntools/fetch_rss.py"]
    STEP1 -->|"~880 raw articles"| STEP2["② Entity Filter\ntools/filter_news.py"]
    STEP2 -->|"700+ competitor articles"| STEP3["③ Deduplicator\ntools/database.py"]
    STEP3 -->|"new (unseen) articles"| STEP4["④ Importance Scorer\ntools/filter_news.py"]
    STEP4 -->|"top 10 ranked"| STEP5["⑤ Groq LLM Summarizer\ntools/summarize_news.py"]
    STEP5 -->|"strategic summaries"| STEP6["⑥ Telegram Delivery\ntools/send_telegram.py"]
    STEP6 -->|"only if sent OK"| STEP7["⑦ Persist delivered + mark all seen\ntools/database.py"]
    STEP7 --> DB

    subgraph CONFIG["core/config.py"]
        C1["15 Competitors + Aliases"]
        C2["23 RSS & Google News Feeds"]
        C3["50+ Keyword Weights"]
    end
    CONFIG -.-> STEP1 & STEP2 & STEP4 & STEP5 & STEP6
```

---

## ✨ Production Features

| Feature | Implementation | Where Used |
|---|---|---|
| **Multi-source Ingestion** | 23 feeds (8 industry feeds + 15 Google News competitor queries), 15 s timeout on both the `requests` fetch and the `feedparser` fallback, browser headers | [`tools/fetch_rss.py`](tools/fetch_rss.py) |
| **Boundary-Safe Matching** | Pre-compiled regex with boundary checks (`(?<!\w)...(?!\w)`) and titlecase rules | [`tools/filter_news.py`](tools/filter_news.py) |
| **Keyword-Weighted Scoring** | 60 energy keywords with word-boundary matching (`bid` does not fire inside `forbidden`), title multiplier (1.5×), and multi-company bonuses | [`tools/filter_news.py`](tools/filter_news.py) |
| **LLM Strategic Analysis** | Groq REST API (`llama-3.3-70b-versatile`) with JSON mode & token telemetry | [`tools/summarize_news.py`](tools/summarize_news.py) |
| **Production Rate Limiting** | Groq: exponential backoff, 12 s then 36 s between 3 attempts ($12 \times 3^{n-1}$), batching, and 12 s inter-batch cooldown. Telegram: separate backoff ($2 \times 2^{n-1}$ s, or `retry_after`) | [`tools/summarize_news.py`](tools/summarize_news.py) |
| **Persistent Deduplication** | SQLite batched query (`WHERE link IN (...)`) against delivered articles (`articles`) and every processed link (`seen_articles`); articles are saved only after a successful Telegram send, so a failed send is retried next run | [`tools/database.py`](tools/database.py) |
| **Summary Caching** | Cached LLM responses stored in SQLite to eliminate redundant API calls | [`tools/database.py`](tools/database.py) |
| **Telegram Auto-Chunking** | Message splitting on `\n` boundaries (≤ 4000 chars) with retry resilience | [`tools/send_telegram.py`](tools/send_telegram.py) |
| **FastAPI REST Layer** | REST API with Pydantic v2 schemas and Swagger docs; `POST /digest/run` has optional API-key auth, a single-run lock (409 if busy) and CORS limited to configured origins | [`api/main.py`](api/main.py) |
| **Docker Readiness** | Single-stage `python:3.11-slim` image, non-root user, healthcheck; runs the REST server by default or the batch pipeline via a command override | [`Dockerfile`](Dockerfile), [`docker-compose.yml`](docker-compose.yml) |

---

## 🚀 Quick Start

### 1. Prerequisites
- **Python 3.11+**
- **Groq API key** — free at [console.groq.com/keys](https://console.groq.com/keys)
- **Telegram Bot Token** — via [@BotFather](https://t.me/BotFather)

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/your-username/EPC-ETL.git
cd EPC-ETL

# Create & activate virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your GROQ_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
```

### 3. Run CLI Modes
```bash
# Run daily competitor briefing
python main.py

# Test Telegram connectivity
python main.py --test

# Inspect database stats & recent articles
python main.py --status
```

### 4. Run FastAPI Server
```bash
uvicorn api.main:app --reload --port 8000
```
Optional API settings (environment variables, see `.env.example`):

| Variable | Default | Effect |
|---|---|---|
| `DIGEST_API_KEY` | *(empty)* | If set, `POST /digest/run` requires an `X-API-Key: <value>` header (401 otherwise). Empty means **no auth**, fine for local use only. |
| `CORS_ALLOW_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000,http://127.0.0.1:8000` | Comma-separated browser origins allowed to call the API. Use `*` only if you accept any origin. |

Only one digest run can execute at a time per API process; a second trigger gets `409 Conflict`. (The lock is in-process: it does not coordinate several uvicorn workers or the CLI.)

Visit the interactive Swagger UI at **http://localhost:8000/docs** to test:
- `GET /health` — System status and SQLite health
- `GET /stats` — Total articles & per-company article counts
- `GET /articles?limit=10&company=Saipem` — Filtered historical articles
- `POST /digest/run?async_mode=true` — Trigger pipeline on-demand (API key if configured; 409 if a run is in progress)

---

## 🐳 Docker Deployment

### Run API with Docker Compose:
```bash
docker compose up -d api
```
Access the API at `http://localhost:8000`.

### Run Daily Batch Agent with Docker:
```bash
docker build -t epc-agent .
docker run --rm --env-file .env -v ./data:/app/data epc-agent python main.py
```

---

## 🧪 Running Tests

The test suite covers entity filtering and keyword scoring, SQLite deduplication and caching, RSS parsing and the feedparser timeout, the agent's send-then-save ordering (with fakes, no network), and FastAPI endpoints including auth, the run lock and CORS:
```bash
pytest -v
```

All 30 tests pass:
```text
tests/test_api.py::test_root_endpoint PASSED
tests/test_api.py::test_health_endpoint PASSED
tests/test_api.py::test_stats_endpoint PASSED
tests/test_api.py::test_articles_endpoint PASSED
tests/test_api.py::test_digest_run_open_when_no_api_key_configured PASSED
tests/test_api.py::test_digest_run_requires_api_key_when_configured PASSED
tests/test_api.py::test_digest_run_rejects_concurrent_run_with_409 PASSED
tests/test_api.py::test_digest_lock_released_after_failure PASSED
tests/test_api.py::test_digest_lock_released_after_background_run PASSED
tests/test_api.py::test_cors_only_allows_configured_origins PASSED
tests/test_agent.py::test_failed_send_saves_nothing_and_retries_next_run PASSED (x2)
tests/test_agent.py::test_successful_send_saves_delivered_and_marks_all_seen PASSED
tests/test_database.py::test_database_initialization PASSED
tests/test_database.py::test_save_and_count_articles PASSED
tests/test_database.py::test_filter_new_articles_deduplication PASSED
tests/test_database.py::test_summary_cache PASSED
tests/test_database.py::test_get_articles_pagination_and_filter PASSED
tests/test_database.py::test_mark_seen_makes_undelivered_articles_dedup PASSED
tests/test_fetch_rss.py::test_clean_html_stripping PASSED
tests/test_fetch_rss.py::test_normalize_entry_valid PASSED
tests/test_fetch_rss.py::test_normalize_entry_missing_data PASSED
tests/test_fetch_rss.py::test_feedparser_fallback_is_bounded_by_timeout PASSED
tests/test_filter.py::test_filter_positive_company_match PASSED
tests/test_filter.py::test_alias_matching PASSED
tests/test_filter.py::test_false_positive_substring_prevention PASSED
tests/test_filter.py::test_score_articles_calculation PASSED
tests/test_filter.py::test_empty_articles_input PASSED
tests/test_filter.py::test_keyword_scoring_uses_word_boundaries PASSED
tests/test_filter.py::test_keyword_scoring_still_matches_inflections PASSED
======================== 30 passed in ~1s ========================
```

---

## 📁 Project Structure

```text
EPC-ETL/
├── api/
│   ├── __init__.py
│   └── main.py                # FastAPI REST API serving layer & Pydantic schemas
├── core/
│   ├── __init__.py
│   ├── agent.py               # 7-step pipeline orchestrator (NewsAgent); saves only after a successful send
│   └── config.py              # Centralized configuration (companies, feeds, weights)
├── tools/
│   ├── __init__.py
│   ├── fetch_rss.py           # RSS ingestion with timeout and BeautifulSoup cleaning
│   ├── filter_news.py         # Boundary-safe entity matching & importance scoring
│   ├── summarize_news.py      # Groq LLM strategic implication engine & telemetry
│   ├── send_telegram.py       # Telegram delivery with auto-chunking & retry logic
│   └── database.py            # SQLite batched dedup (delivered + seen links) & summary cache
├── eval/
│   ├── golden_dataset.json    # 100-sample ground-truth labeled benchmark
│   ├── generate_dataset.py    # Benchmark dataset generator
│   ├── evaluate_filter.py     # Evaluation runner (precision/recall/latency metrics)
│   └── results.json           # Recorded evaluation benchmark metrics
├── tests/
│   ├── __init__.py
│   ├── test_agent.py          # Send-then-save ordering and dedup (fakes, no network)
│   ├── test_api.py            # FastAPI endpoint, API-key, run-lock and CORS tests
│   ├── test_database.py       # SQLite dedup & cache tests
│   ├── test_fetch_rss.py      # RSS feed parsing & normalizer tests
│   └── test_filter.py         # Entity matching, aliases, and scoring tests
├── .github/
│   └── workflows/
│       └── ci.yml             # GitHub Actions CI workflow (pytest + eval)
├── data/
│   └── news.db                # SQLite database (auto-created)
├── Dockerfile                 # Single-stage python:3.11-slim image (non-root, healthcheck)
├── docker-compose.yml         # Compose configuration for API and Agent
├── .dockerignore              # Container ignore list
├── .env.example               # Configuration template
├── requirements.txt           # Core and development dependencies
├── main.py                    # CLI entry point (--test, --status)
└── README.md                  # Project documentation
```

---

## 📄 License

MIT License — free for educational and commercial use.
