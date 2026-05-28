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
TELEGRAM_CHAT_IDS: list[str] = [
    cid.strip() for cid in os.getenv("TELEGRAM_CHAT_ID", "").split(",") if cid.strip()
]

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
    "Saipem": ["saipem", "saipem spa", "sai.mi"],
    "Fluor": ["fluor", "fluor corporation", "fluor corp", "flr"],
    "Bechtel": ["bechtel", "bechtel corporation", "bechtel corp", "bechtel group"],
    "Worley": ["worley", "worley limited", "worleyparsons", "worley parsons", "wor.ax"],
    "Petrofac": ["petrofac", "petrofac limited", "petrofac ltd"],
    "McDermott": ["mcdermott", "mcdermott international", "cb&i", "lummus"],
    "Wood Group": ["wood group", "john wood group", "wood plc", "john wood", "wood"],
    "MAIRE": ["maire", "maire tecnimont", "tecnimont", "maire spa", "nextchem"],
    "JGC Holdings": ["jgc", "jgc holdings", "jgc corporation", "jgc corp", "chiyoda"],
    "Larsen & Toubro": ["larsen & toubro", "larsen and toubro", "l&t", "l & t", "l&t hydrocarbon", "l&t energy"],
    "Samsung E&A": ["samsung e&a", "samsung engineering", "samsung e & a", "samsung eng", "kt-kinetics"],
    "AECOM": ["aecom", "aecom technology", "acm"],
    "Baker Hughes": ["baker hughes", "bakerhughes", "baker hughes co", "bkr"],
    "Linde": ["linde", "linde plc", "linde engineering", "linde group", "lin"],
    "AtkinsRealis": ["atkinsrealis", "atkins realis", "snc-lavalin", "snc lavalin", "sncl", "faithful+gould", "faithful & gould"],
}

# ─── Keyword Weights (for importance scoring) ────────────────────────────────
# Tuned for EPC / Energy sector competitive intelligence
KEYWORD_WEIGHTS: dict[str, float] = {
    # Strategic / High-impact events
    "contract": 3.0,
    "awarded": 3.5,
    "wins": 3.5,
    "epc": 3.0,
    "feed": 3.0,
    "project": 1.5,
    "tender": 2.5,
    "bid": 2.5,
    "pre-qualification": 2.0,
    "feasibility": 2.0,
    "fid": 4.0,
    "final investment decision": 4.0,
    "acquisition": 4.0,
    "acquire": 3.5,
    "merger": 4.0,
    "ipo": 3.5,
    "market share": 3.0,
    "expansion": 3.0,
    "new market": 3.0,
    "technology license": 3.0,
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
    "decarbonization": 2.5,
    "energy transition": 2.5,
    # Business
    "partnership": 2.5,
    "joint venture": 3.0,
    "jv": 2.5,
    "backlog": 3.0,
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
    # Risk / disruption
    "delay": 3.0,
    "overrun": 3.0,
    "safety": 1.0,
    "incident": 2.0,
    "regulation": 2.0,
    "sanction": 3.0,
    "lawsuit": 2.5,
    "investigation": 3.0,
    "bankruptcy": 4.0,
    "restructuring": 3.0,
    "layoff": 2.5,
    "shutdown": 3.0,
}

# ─── RSS Sources ──────────────────────────────────────────────────────────────
# Energy, Oil & Gas, and EPC industry feeds
RSS_FEEDS: list[dict[str, str]] = [
    # General EPC / Energy feeds
    {"name": "Offshore Engineer", "url": "https://www.oedigital.com/rss"},
    {"name": "Offshore Energy", "url": "https://www.offshore-energy.biz/feed/"},
    {"name": "NS Energy", "url": "https://www.nsenergybusiness.com/feed/"},
    {"name": "Hydrocarbons Technology", "url": "https://www.hydrocarbons-technology.com/feed/"},
    {"name": "Chemical Engineering", "url": "https://www.chemengonline.com/feed/"},
    {"name": "Process Engineering", "url": "https://www.thechemicalengineer.com/rss"},
    {"name": "Oil & Gas 360", "url": "https://www.oilandgas360.com/feed/"},
    {"name": "Utility Dive", "url": "https://www.utilitydive.com/feeds/news/"},
    # Google News feeds per competitor for high hit-rate
    {"name": "Google News: Saipem", "url": "https://news.google.com/rss/search?q=%22Saipem%22&hl=en&gl=US&ceid=US:en"},
    {"name": "Google News: Baker Hughes", "url": "https://news.google.com/rss/search?q=%22Baker+Hughes%22&hl=en&gl=US&ceid=US:en"},
    {"name": "Google News: Fluor", "url": "https://news.google.com/rss/search?q=%22Fluor+Corporation%22&hl=en&gl=US&ceid=US:en"},
    {"name": "Google News: Bechtel", "url": "https://news.google.com/rss/search?q=%22Bechtel%22&hl=en&gl=US&ceid=US:en"},
    {"name": "Google News: Worley", "url": "https://news.google.com/rss/search?q=%22Worley%22+energy+OR+engineering&hl=en&gl=US&ceid=US:en"},
    {"name": "Google News: Petrofac", "url": "https://news.google.com/rss/search?q=%22Petrofac%22&hl=en&gl=US&ceid=US:en"},
    {"name": "Google News: McDermott", "url": "https://news.google.com/rss/search?q=%22McDermott+International%22&hl=en&gl=US&ceid=US:en"},
    {"name": "Google News: MAIRE", "url": "https://news.google.com/rss/search?q=%22MAIRE%22+OR+%22Tecnimont%22+energy&hl=en&gl=US&ceid=US:en"},
    {"name": "Google News: Linde", "url": "https://news.google.com/rss/search?q=%22Linde+plc%22+OR+%22Linde+engineering%22&hl=en&gl=US&ceid=US:en"},
    {"name": "Google News: AECOM", "url": "https://news.google.com/rss/search?q=%22AECOM%22+engineering&hl=en&gl=US&ceid=US:en"},
    {"name": "Google News: Samsung E&A", "url": "https://news.google.com/rss/search?q=%22Samsung+Engineering%22+OR+%22Samsung+E%26A%22&hl=en&gl=US&ceid=US:en"},
    {"name": "Google News: L&T", "url": "https://news.google.com/rss/search?q=%22Larsen+%26+Toubro%22+OR+%22L%26T%22+engineering&hl=en&gl=US&ceid=US:en"},
    {"name": "Google News: Wood Group", "url": "https://news.google.com/rss/search?q=%22Wood+Group%22+OR+%22John+Wood+Group%22&hl=en&gl=US&ceid=US:en"},
    {"name": "Google News: JGC", "url": "https://news.google.com/rss/search?q=%22JGC+Holdings%22+OR+%22JGC+Corporation%22&hl=en&gl=US&ceid=US:en"},
    {"name": "Google News: AtkinsRealis", "url": "https://news.google.com/rss/search?q=%22AtkinsRealis%22+OR+%22SNC-Lavalin%22&hl=en&gl=US&ceid=US:en"},
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
    if not TELEGRAM_CHAT_IDS:
        errors.append("TELEGRAM_CHAT_ID is not set (can be a comma-separated list).")
    return errors
