"""
Configuration module for the Competitor News Monitoring Agent.

Centralizes all configuration: environment variables, tracked companies,
RSS sources, keyword weights, and application settings.

Configured to monitor Technip Energies NV's key competitors in the
EPC (Engineering, Procurement & Construction) / Energy sector.
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
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

# ─── Companies to Track ──────────────────────────────────────────────────────
# Technip Energies NV competitors (EPC / Energy sector)
# Configurable via TRACKED_COMPANIES env var (comma-separated) or defaults
_default_companies = [
    "Saipem",
    "Fluor",
    "Bechtel",
    "Worley",
    "Petrofac",
    "McDermott",
    "Wood Group",
    "MAIRE",
    "JGC Holdings",
    "Larsen & Toubro",
    "Samsung E&A",
    "AECOM",
    "Baker Hughes",
    "Linde",
    "AtkinsRealis",
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
    "Saipem": ["saipem", "saipem spa"],
    "Fluor": ["fluor", "fluor corporation", "fluor corp"],
    "Bechtel": ["bechtel", "bechtel corporation", "bechtel corp", "bechtel group"],
    "Worley": ["worley", "worley limited", "worleyparsons", "worley parsons"],
    "Petrofac": ["petrofac", "petrofac limited", "petrofac ltd"],
    "McDermott": ["mcdermott", "mcdermott international", "cb&i", "lummus"],
    "Wood Group": ["wood group", "john wood group", "wood plc", "john wood"],
    "MAIRE": ["maire", "maire tecnimont", "tecnimont", "maire spa", "nextchem"],
    "JGC Holdings": ["jgc", "jgc holdings", "jgc corporation", "jgc corp"],
    "Larsen & Toubro": ["larsen & toubro", "larsen and toubro", "l&t", "l & t", "l&t hydrocarbon", "l&t energy"],
    "Samsung E&A": ["samsung e&a", "samsung engineering", "samsung e & a", "samsung eng"],
    "AECOM": ["aecom", "aecom technology"],
    "Baker Hughes": ["baker hughes", "bakerhughes", "baker hughes co"],
    "Linde": ["linde", "linde plc", "linde engineering", "linde group"],
    "AtkinsRealis": ["atkinsrealis", "atkins realis", "snc-lavalin", "snc lavalin", "sncl"],
}

# ─── Keyword Weights (for importance scoring) ────────────────────────────────
# Tuned for EPC / Energy sector competitive intelligence
KEYWORD_WEIGHTS: dict[str, float] = {
    # High-impact events
    "contract": 3.5,
    "awarded": 3.5,
    "epc": 3.0,
    "feed": 2.5,
    "project": 2.0,
    "acquisition": 3.0,
    "acquire": 3.0,
    "merger": 3.0,
    "ipo": 3.5,
    "funding": 2.5,
    "valuation": 2.5,
    "billion": 2.0,
    "million": 1.5,
    # Breaking / urgent
    "breaking": 4.0,
    "exclusive": 3.0,
    # Sector-specific
    "lng": 2.5,
    "refinery": 2.0,
    "petrochemical": 2.0,
    "hydrogen": 2.5,
    "carbon capture": 3.0,
    "ccus": 3.0,
    "offshore": 2.0,
    "onshore": 1.5,
    "subsea": 2.0,
    "pipeline": 1.5,
    "modular": 2.0,
    "floating": 2.0,
    "fpso": 2.5,
    "decarbonization": 2.5,
    "energy transition": 2.5,
    "green hydrogen": 3.0,
    "blue hydrogen": 2.5,
    "ammonia": 2.0,
    "ethylene": 2.0,
    "downstream": 1.5,
    "upstream": 1.5,
    "midstream": 1.5,
    # Business
    "partnership": 2.0,
    "joint venture": 2.5,
    "jv": 2.0,
    "backlog": 2.5,
    "revenue": 2.0,
    "earnings": 2.0,
    "quarterly results": 2.5,
    "order intake": 3.0,
    "capex": 2.0,
    # Leadership
    "ceo": 2.0,
    "fired": 3.0,
    "resigned": 3.0,
    "appointed": 2.5,
    "hired": 2.0,
    # Risk / disruption
    "delay": 2.5,
    "overrun": 2.5,
    "safety": 2.0,
    "incident": 2.5,
    "regulation": 2.0,
    "sanction": 3.0,
    "lawsuit": 2.5,
    "investigation": 2.5,
    "bankruptcy": 3.5,
    "restructuring": 3.0,
    "layoff": 2.5,
    "shutdown": 3.0,
}

# ─── RSS Sources ──────────────────────────────────────────────────────────────
# Energy, Oil & Gas, and EPC industry feeds
RSS_FEEDS: list[dict[str, str]] = [
    {"name": "Rigzone", "url": "https://www.rigzone.com/news/rss/rigzone_latest.aspx"},
    {"name": "Offshore Engineer", "url": "https://www.oedigital.com/rss"},
    {"name": "Offshore Energy", "url": "https://www.offshore-energy.biz/feed/"},
    {"name": "NS Energy", "url": "https://www.nsenergybusiness.com/feed/"},
    {"name": "Hydrocarbons Technology", "url": "https://www.hydrocarbons-technology.com/feed/"},
    {"name": "Chemical Engineering", "url": "https://www.chemengonline.com/feed/"},
    {"name": "Process Engineering", "url": "https://www.thechemicalengineer.com/rss"},
    {"name": "Oil & Gas 360", "url": "https://www.oilandgas360.com/feed/"},
    {"name": "Utility Dive", "url": "https://www.utilitydive.com/feeds/news/"},
    {"name": "Hacker News", "url": "https://hnrss.org/frontpage"},
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
