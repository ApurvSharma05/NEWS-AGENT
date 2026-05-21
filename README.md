# 🤖 AI News Monitoring Agent

A production-ready Python agent that monitors tech/AI news daily, filters articles about specific competitor companies, summarizes them with an LLM, and delivers a clean digest to Telegram.

![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)

---

## 📋 Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Setup Guide](#setup-guide)
  - [1. Prerequisites](#1-prerequisites)
  - [2. Clone & Install](#2-clone--install)
  - [3. Google Gemini API Setup](#3-google-gemini-api-setup)
  - [4. Telegram Bot Setup](#4-telegram-bot-setup)
  - [5. Configure Environment](#5-configure-environment)
- [Running Locally](#running-locally)
- [Automating Daily Execution](#automating-daily-execution)
  - [Linux/macOS (cron)](#linuxmacos-cron)
  - [Windows (Task Scheduler)](#windows-task-scheduler)
- [Deploying to Cloud](#deploying-to-cloud)
  - [Railway](#railway)
  - [Render](#render)
- [Extending into a Real AI Agent](#extending-into-a-real-ai-agent)
- [Configuration Reference](#configuration-reference)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📰 **Multi-source RSS** | Fetches from TechCrunch, The Verge, Ars Technica, HN, and more |
| 🎯 **Smart Filtering** | Fuzzy company matching with aliases (e.g., "ChatGPT" → OpenAI) |
| 🧠 **LLM Summarization** | Concise, actionable summaries via Google Gemini API (free tier!) |
| 📊 **Importance Scoring** | Keyword-weighted ranking with breaking news detection |
| 🔄 **Deduplication** | SQLite-backed, never sends the same article twice |
| 📱 **Telegram Delivery** | Clean, formatted daily digest to your phone |
| 🌐 **Hindi Support** | Optional Hindi summaries with technical terms in English |
| 🔧 **Modular Tools** | Each component is a standalone, reusable tool |

---

## 🏗️ Architecture

```
main.py                 → CLI entry point (digest / test / status)
  └─ core/agent.py      → Orchestrator (runs the pipeline)
       ├─ tools/fetch_rss.py       → RSS feed fetcher
       ├─ tools/filter_news.py     → Company filter + importance scorer
       ├─ tools/database.py        → SQLite dedup + storage
       ├─ tools/summarize_news.py  → Gemini summarizer
       └─ tools/send_telegram.py   → Telegram delivery
  └─ core/config.py     → Centralized configuration
```

---

## 🚀 Setup Guide

### 1. Prerequisites

- **Python 3.11+** (tested on 3.11, 3.12, 3.13)
- A **Telegram account**
- A **Google Gemini API key** (free at [aistudio.google.com](https://aistudio.google.com/apikey))

### 2. Clone & Install

```bash
# Navigate to the project
cd news-agent

# Create a virtual environment
python -m venv venv

# Activate it
# Linux/macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Google Gemini API Setup

1. Go to [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. Sign in with your Google account
3. Click **"Create API Key"**
4. Copy the key

> **💡 Cost:** The free tier gives you **15 requests/minute** and **1M tokens/minute** — more than enough for daily digests. Zero cost!

### 4. Telegram Bot Setup

#### Create the Bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot`
3. Choose a name (e.g., "AI News Digest")
4. Choose a username (e.g., `ai_news_digest_bot`)
5. Copy the **bot token** (format: `123456789:ABCdef...`)

#### Get Your Chat ID

1. Send any message to your new bot
2. Open this URL in your browser (replace `<TOKEN>` with your bot token):
   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```
3. Find `"chat":{"id": <YOUR_CHAT_ID>}` in the response
4. Copy the chat ID (a number like `123456789`)

#### For a Channel

1. Create a Telegram channel
2. Add your bot as an **administrator**
3. The chat ID for channels is `@channel_username` or the numeric ID

### 5. Configure Environment

```bash
# Copy the example file
cp .env.example .env

# Edit with your values
# Linux/macOS: nano .env
# Windows: notepad .env
```

Fill in these **required** values:
```env
GEMINI_API_KEY=your-gemini-api-key
TELEGRAM_BOT_TOKEN=123456789:ABCdef...
TELEGRAM_CHAT_ID=your-chat-id
```

---

## 🏃 Running Locally

```bash
# Run the daily digest
python main.py

# Test Telegram connectivity
python main.py --test

# Check database status
python main.py --status
```

### What happens when you run the digest:

1. Fetches articles from 8+ RSS feeds
2. Filters for mentions of tracked companies
3. Removes articles you've already seen
4. Scores articles by importance
5. Sends top articles to Gemini for summarization
6. Formats and delivers the digest to Telegram

---

## ⏰ Automating Daily Execution

### Linux/macOS (cron)

```bash
# Open crontab editor
crontab -e

# Add this line to run at 8 AM daily:
0 8 * * * cd /path/to/news-agent && /path/to/venv/bin/python main.py >> /var/log/news-agent.log 2>&1

# For twice-daily (8 AM and 6 PM):
0 8,18 * * * cd /path/to/news-agent && /path/to/venv/bin/python main.py >> /var/log/news-agent.log 2>&1
```

### Windows (Task Scheduler)

1. Open **Task Scheduler** (`taskschd.msc`)
2. Click **"Create Basic Task"**
3. Name: `AI News Digest`
4. Trigger: **Daily** at your preferred time
5. Action: **Start a program**
   - Program: `C:\path\to\news-agent\venv\Scripts\python.exe`
   - Arguments: `main.py`
   - Start in: `C:\path\to\news-agent`
6. Click **Finish**

---

## ☁️ Deploying to Cloud

### Railway

1. Install the Railway CLI:
   ```bash
   npm install -g @railway/cli
   ```

2. Create a `Procfile`:
   ```
   worker: python main.py
   ```

3. Create a `railway.json`:
   ```json
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

4. Deploy:
   ```bash
   railway login
   railway init
   railway up
   ```

5. Set environment variables in the Railway dashboard (Settings → Variables).

### Render

1. Create a `render.yaml`:
   ```yaml
   services:
     - type: cron
       name: ai-news-agent
       runtime: python
       schedule: "0 8 * * *"
       buildCommand: pip install -r requirements.txt
       startCommand: python main.py
       envVars:
         - key: GEMINI_API_KEY
           sync: false
         - key: TELEGRAM_BOT_TOKEN
           sync: false
         - key: TELEGRAM_CHAT_ID
           sync: false
   ```

2. Push to GitHub and connect the repo in [Render Dashboard](https://dashboard.render.com).
3. Render will auto-detect the `render.yaml` and set up the cron job.

---

## 🔮 Extending into a Real AI Agent

The modular tool-based architecture makes this easy to extend into a full AI agent:

### 1. Add New Tools

Create a new file in `tools/` with a class that follows the same pattern:

```python
# tools/analyze_sentiment.py
class SentimentAnalyzer:
    def analyze(self, articles: list[dict]) -> list[dict]:
        # Add sentiment scores to each article
        ...
```

### 2. Build a Tool Registry

```python
# core/tool_registry.py
class ToolRegistry:
    def __init__(self):
        self.tools = {}

    def register(self, name: str, tool: Any):
        self.tools[name] = tool

    def get(self, name: str):
        return self.tools.get(name)
```

### 3. Add an LLM-Driven Planner

Let the agent decide which tools to use based on the task:

```python
# The LLM receives a list of available tools and decides the execution plan
tools = ["fetch_rss", "filter_news", "summarize", "send_telegram", "analyze_sentiment"]
plan = llm.plan(task="Generate daily digest with sentiment analysis", tools=tools)
```

### 4. Add Memory & Conversation

- Use SQLite or Redis for long-term memory
- Track which articles the user found useful
- Learn preferences over time

### 5. Add More Delivery Channels

Swap `TelegramSender` for `SlackSender`, `DiscordSender`, or `EmailSender` — all following the same interface.

---

## ⚙️ Configuration Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GEMINI_API_KEY` | ✅ | — | Google Gemini API key (free) |
| `GEMINI_MODEL` | ❌ | `gemini-2.0-flash` | Model for summarization |
| `TELEGRAM_BOT_TOKEN` | ✅ | — | Telegram bot token |
| `TELEGRAM_CHAT_ID` | ✅ | — | Target chat/channel ID |
| `TRACKED_COMPANIES` | ❌ | 6 defaults | Comma-separated company list |
| `MAX_ARTICLES_PER_FEED` | ❌ | `50` | Max articles per RSS feed |
| `DIGEST_MAX_ARTICLES` | ❌ | `30` | Max articles in digest |
| `BREAKING_NEWS_THRESHOLD` | ❌ | `8.0` | Score threshold for 🔴 flag |
| `SUMMARY_LANGUAGE` | ❌ | `english` | `english` or `hindi` |
| `LOG_LEVEL` | ❌ | `INFO` | Logging verbosity |

---

## 📁 Project Structure

```
news-agent/
├── core/
│   ├── __init__.py
│   ├── config.py           # Centralized configuration
│   └── agent.py            # Pipeline orchestrator
├── tools/
│   ├── __init__.py
│   ├── fetch_rss.py        # RSS feed fetcher
│   ├── filter_news.py      # Company filter + scorer
│   ├── summarize_news.py   # LLM summarizer
│   ├── send_telegram.py    # Telegram delivery
│   └── database.py         # SQLite dedup + storage
├── data/
│   └── news.db             # SQLite database (auto-created)
├── .env                    # Your secrets (never commit!)
├── .env.example            # Template for .env
├── requirements.txt        # Python dependencies
├── main.py                 # CLI entry point
└── README.md               # This file
```

---

## 📄 License

MIT License — use freely, modify as needed.
