"""
Configuration module for the AI News Monitoring Agent.

Centralizes all configuration: environment variables, tracked companies,
RSS sources, keyword weights, and application settings.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "news.db"

# Ensure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ─── API Keys ─────────────────────────────────────────────────────────────────
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

# ─── Companies to Track ──────────────────────────────────────────────────────
# Configurable via TRACKED_COMPANIES env var (comma-separated) or defaults
_default_companies = [
    "OpenAI",
    "Anthropic",
    "Google DeepMind",
    "Perplexity",
    "xAI",
    "Mistral AI",
]

_env_companies = os.getenv("TRACKED_COMPANIES", "")
TRACKED_COMPANIES: list[str] = (
    [c.strip() for c in _env_companies.split(",") if c.strip()]
    if _env_companies
    else _default_companies
)

# ─── Company Aliases (for fuzzy matching) ────────────────────────────────────
# Maps canonical company name → list of alternative spellings / abbreviations
COMPANY_ALIASES: dict[str, list[str]] = {
    "OpenAI": ["openai", "open ai", "open-ai", "chatgpt", "gpt-4", "gpt-5", "gpt4", "gpt5", "dall-e", "dalle", "sora"],
    "Anthropic": ["anthropic", "claude", "claude 3", "claude 4", "claude opus", "claude sonnet"],
    "Google DeepMind": ["google deepmind", "deepmind", "gemini", "gemini pro", "gemini ultra", "google ai", "bard"],
    "Perplexity": ["perplexity", "perplexity ai", "perplexity.ai"],
    "xAI": ["xai", "x.ai", "grok", "elon musk ai"],
    "Mistral AI": ["mistral", "mistral ai", "mistralai", "mixtral", "le chat"],
}

# ─── Keyword Weights (for importance scoring) ────────────────────────────────
KEYWORD_WEIGHTS: dict[str, float] = {
    # High-impact events
    "launch": 3.0,
    "release": 3.0,
    "announce": 2.5,
    "unveil": 3.0,
    "breakthrough": 3.5,
    "acquisition": 3.0,
    "acquire": 3.0,
    "merger": 3.0,
    "ipo": 3.5,
    "funding": 2.5,
    "raises": 2.5,
    "valuation": 2.5,
    "billion": 2.0,
    "million": 1.5,
    # Breaking / urgent
    "breaking": 4.0,
    "urgent": 3.5,
    "exclusive": 3.0,
    "leaked": 2.5,
    # Product & tech
    "model": 1.5,
    "api": 1.5,
    "open source": 2.0,
    "benchmark": 2.0,
    "safety": 2.0,
    "regulation": 2.0,
    "partnership": 2.0,
    "compete": 1.5,
    "sued": 2.5,
    "lawsuit": 2.5,
    "ban": 2.5,
    "shutdown": 3.0,
    # Leadership
    "ceo": 2.0,
    "fired": 3.0,
    "resigned": 3.0,
    "hired": 2.0,
}

# ─── RSS Sources ──────────────────────────────────────────────────────────────
RSS_FEEDS: list[dict[str, str]] = [
    {"name": "TechCrunch", "url": "https://techcrunch.com/feed/"},
    {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml"},
    {"name": "Ars Technica", "url": "https://feeds.arstechnica.com/arstechnica/index"},
    {"name": "Hacker News", "url": "https://hnrss.org/frontpage"},
    {"name": "MIT Tech Review", "url": "https://www.technologyreview.com/feed/"},
    {"name": "VentureBeat", "url": "https://venturebeat.com/feed/"},
    {"name": "The Information (AI)", "url": "https://www.theinformation.com/feed"},
    {"name": "AI News", "url": "https://www.artificialintelligence-news.com/feed/"},
]

# ─── Application Settings ────────────────────────────────────────────────────
MAX_ARTICLES_PER_FEED: int = int(os.getenv("MAX_ARTICLES_PER_FEED", "50"))
DIGEST_MAX_ARTICLES: int = int(os.getenv("DIGEST_MAX_ARTICLES", "30"))
BREAKING_NEWS_THRESHOLD: float = float(os.getenv("BREAKING_NEWS_THRESHOLD", "8.0"))
SUMMARY_LANGUAGE: str = os.getenv("SUMMARY_LANGUAGE", "english")  # "english" or "hindi"
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

# ─── Gemini Rate Limiting ─────────────────────────────────────────────────────
# Tuned for the free tier (configured for 5 RPM to prevent rate limiting)
GEMINI_BATCH_SIZE: int = int(os.getenv("GEMINI_BATCH_SIZE", "10"))
GEMINI_RETRY_ATTEMPTS: int = int(os.getenv("GEMINI_RETRY_ATTEMPTS", "3"))
GEMINI_RETRY_BASE_DELAY: float = float(os.getenv("GEMINI_RETRY_BASE_DELAY", "12.0"))
GEMINI_COOLDOWN_DELAY: float = float(os.getenv("GEMINI_COOLDOWN_DELAY", "12.0"))

# ─── Validation ───────────────────────────────────────────────────────────────
def validate_config() -> list[str]:
    """Validate that all required configuration is present. Returns list of errors."""
    errors = []
    if not GEMINI_API_KEY:
        errors.append("GEMINI_API_KEY is not set. Get one free at https://aistudio.google.com/apikey")
    if not TELEGRAM_BOT_TOKEN:
        errors.append("TELEGRAM_BOT_TOKEN is not set.")
    if not TELEGRAM_CHAT_ID:
        errors.append("TELEGRAM_CHAT_ID is not set.")
    return errors
