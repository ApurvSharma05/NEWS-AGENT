# 🏗️ EPC Competitor Intelligence Agent

An autonomous AI-powered competitive intelligence system that monitors **880+ news sources daily**, extracts strategic implications using **Llama 3.3 70B** via Groq, and delivers actionable briefings to Telegram — built for the EPC (Engineering, Procurement & Construction) energy sector.

![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)
![LLM: Groq](https://img.shields.io/badge/LLM-Groq%20%7C%20Llama%203.3-orange.svg)
![Delivery: Telegram](https://img.shields.io/badge/Delivery-Telegram-26A5E4.svg)

---

## 🎯 What It Does

This agent acts as a **Senior Strategy Analyst** — it doesn't just summarize news, it tells you *why it matters* to your competitive position:

```
⚡ Fluor, JGC Holdings: Fluor-JGC JV awarded FEED contract for
  LNG Canada Phase 2 expansion (28 MTPA capacity doubling).
💡 Implication: Solidifies the Fluor-JGC partnership's dominance in
  North American LNG, intensifying competition for Technip Energies
  in securing future large-scale LNG FEED and EPC contracts.
🔗 Source
```

> **Key Differentiator:** Unlike generic news aggregators, every article is analyzed through a competitive lens — scoring importance, extracting strategic implications, and highlighting direct threats to your market position.

---

## ✨ Technical Highlights

| Feature | Implementation |
|---------|---------------|
| **Multi-source Ingestion** | 24+ RSS feeds (8 industry publications + 15 Google News competitor searches) |
| **Fuzzy Entity Matching** | Regex-based alias system (e.g., `"SNC-Lavalin"` → `AtkinsRealis`, `"CB&I"` → `McDermott`) |
| **Keyword-Weighted Scoring** | 50+ industry-specific keywords with configurable weights and title multipliers |
| **LLM Strategic Analysis** | Groq API (Llama 3.3 70B) with JSON mode for structured implication extraction |
| **Production Rate Limiting** | Exponential backoff (3^n), smart batching, inter-batch cooldown, auto-retry on 429/5xx |
| **Deduplication** | SQLite-backed — never sends the same article twice across runs |
| **Summary Caching** | Avoids redundant LLM API calls; cached summaries persist across pipeline runs |
| **Graceful Degradation** | Falls back to raw summaries if LLM fails after retries — digest always ships |
| **Breaking News Detection** | Configurable importance threshold flags high-priority articles with 🔴 |
| **Multi-language Support** | English and Hindi output (technical terms preserved in English) |

---

## 🏗️ Architecture

```
main.py                     → CLI entry point (digest / test / status)
  └─ core/agent.py          → Pipeline orchestrator (7-step workflow)
       ├─ tools/fetch_rss.py        → RSS ingestion (880+ articles/run)
       ├─ tools/filter_news.py      → Entity matching + importance scoring
       ├─ tools/database.py         → SQLite dedup + summary cache
       ├─ tools/summarize_news.py   → Groq LLM strategic analysis engine
       └─ tools/send_telegram.py    → Telegram delivery (auto-chunking)
  └─ core/config.py         → Centralized configuration (env + defaults)
```

### Pipeline Flow

```
880+ articles → Company Filter (741) → Dedup (616 new) → Score & Rank
  → Top 10 → Groq LLM Analysis → Strategic Briefing → Telegram
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+**
- **Groq API key** — free at [console.groq.com/keys](https://console.groq.com/keys)
- **Telegram Bot Token** — via [@BotFather](https://t.me/BotFather)

### Setup

```bash
cd news-agent

# Create & activate virtual environment
python -m venv venv
source venv/bin/activate        # Linux/macOS
venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your API keys
```

### Run

```bash
python main.py              # Run daily digest
python main.py --test       # Test Telegram connectivity
python main.py --status     # Show database stats
```

---

## 📱 Telegram Bot Setup

### Create the Bot

1. Open Telegram → search **@BotFather** → send `/newbot`
2. Choose a name and username
3. Copy the **bot token** (format: `123456789:ABCdef...`)

### Get Your Chat ID

1. Send any message to your new bot
2. Visit: `https://api.telegram.org/bot<TOKEN>/getUpdates`
3. Find `"chat":{"id": <YOUR_CHAT_ID>}` in the response

### For Channels

1. Create a channel → add your bot as **administrator**
2. Use `@channel_username` or the numeric ID as `TELEGRAM_CHAT_ID`

---

## ⏰ Automating Daily Execution

### Linux/macOS (cron)

```bash
# Run at 8 AM daily
0 8 * * * cd /path/to/news-agent && /path/to/venv/bin/python main.py >> /var/log/news-agent.log 2>&1

# Twice daily (8 AM and 6 PM)
0 8,18 * * * cd /path/to/news-agent && /path/to/venv/bin/python main.py >> /var/log/news-agent.log 2>&1
```

### Windows (Task Scheduler)

1. Open **Task Scheduler** (`taskschd.msc`)
2. **Create Basic Task** → Name: `EPC Intelligence Agent`
3. Trigger: **Daily** at your preferred time
4. Action: **Start a program**
   - Program: `C:\path\to\news-agent\venv\Scripts\python.exe`
   - Arguments: `main.py`
   - Start in: `C:\path\to\news-agent`

---

## ☁️ Cloud Deployment

### Railway

```json
// railway.json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": { "builder": "NIXPACKS" },
  "deploy": {
    "numReplicas": 1,
    "restartPolicyType": "ON_FAILURE",
    "cronSchedule": "0 8 * * *"
  }
}
```

```bash
railway login && railway init && railway up
```

### Render

```yaml
# render.yaml
services:
  - type: cron
    name: epc-intelligence-agent
    runtime: python
    schedule: "0 8 * * *"
    buildCommand: pip install -r requirements.txt
    startCommand: python main.py
    envVars:
      - key: GROQ_API_KEY
        sync: false
      - key: TELEGRAM_BOT_TOKEN
        sync: false
      - key: TELEGRAM_CHAT_ID
        sync: false
```

---

## 🔮 Extending the Agent

The modular tool-based architecture makes this easy to extend:

### Add New Tools

```python
# tools/analyze_sentiment.py
class SentimentAnalyzer:
    def analyze(self, articles: list[dict]) -> list[dict]:
        # Add sentiment scores to each article
        ...
```

### Build a Tool Registry

```python
# core/tool_registry.py
class ToolRegistry:
    def __init__(self):
        self.tools = {}

    def register(self, name: str, tool: Any):
        self.tools[name] = tool
```

### Add an LLM-Driven Planner

```python
# Let the agent autonomously decide which tools to use
tools = ["fetch_rss", "filter_news", "summarize", "send_telegram", "analyze_sentiment"]
plan = llm.plan(task="Generate daily digest with sentiment analysis", tools=tools)
```

### Future Directions

- **Memory & Learning** — Track which articles the user found useful, learn preferences over time
- **Multi-channel Delivery** — Swap `TelegramSender` for `SlackSender`, `DiscordSender`, or `EmailSender`
- **Dashboard** — Build a web UI on top of the SQLite article database

---

## ⚙️ Configuration Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GROQ_API_KEY` | ✅ | — | Groq API key ([free tier](https://console.groq.com/keys)) |
| `GROQ_MODEL` | ❌ | `llama-3.3-70b-versatile` | LLM model for strategic analysis |
| `TELEGRAM_BOT_TOKEN` | ✅ | — | Telegram bot token via @BotFather |
| `TELEGRAM_CHAT_ID` | ✅ | — | Target chat/channel ID (comma-separated for multi-chat) |
| `TRACKED_COMPANIES` | ❌ | 15 EPC competitors | Comma-separated company list |
| `MAX_ARTICLES_PER_FEED` | ❌ | `50` | Max articles fetched per RSS feed |
| `DIGEST_MAX_ARTICLES` | ❌ | `10` | Max articles in daily briefing |
| `BREAKING_NEWS_THRESHOLD` | ❌ | `8.5` | Importance score threshold for 🔴 flag |
| `SUMMARY_LANGUAGE` | ❌ | `english` | Output language (`english` or `hindi`) |
| `GROQ_BATCH_SIZE` | ❌ | `10` | Articles per LLM API call |
| `GROQ_RETRY_ATTEMPTS` | ❌ | `3` | Max retry attempts on API failure |
| `LOG_LEVEL` | ❌ | `INFO` | Logging verbosity |

---

## 📁 Project Structure

```
news-agent/
├── core/
│   ├── __init__.py
│   ├── config.py              # Centralized configuration (companies, feeds, weights)
│   └── agent.py               # 7-step pipeline orchestrator
├── tools/
│   ├── __init__.py
│   ├── fetch_rss.py           # RSS ingestion (24+ feeds)
│   ├── filter_news.py         # Entity matching + importance scoring
│   ├── summarize_news.py      # Groq LLM strategic analysis engine
│   ├── send_telegram.py       # Telegram delivery with auto-chunking
│   └── database.py            # SQLite dedup + summary cache
├── data/
│   └── news.db                # SQLite database (auto-created)
├── .env                       # Secrets (never committed)
├── .env.example               # Template for .env
├── requirements.txt           # Python dependencies
├── main.py                    # CLI entry point
└── README.md
```

---

## 📄 License

MIT License — use freely, modify as needed.
