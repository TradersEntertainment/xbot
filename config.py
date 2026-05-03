import os
from dotenv import load_dotenv

load_dotenv()

# --- X (Twitter) ---
X_USERNAME = os.getenv("X_USERNAME", "girlmathtorich")
X_EMAIL = os.getenv("X_EMAIL", "")
X_PASSWORD = os.getenv("X_PASSWORD", "")

# --- Groq AI ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# --- Telegram ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
GROQ_MODEL = "llama-3.3-70b-versatile"

# --- Polymarket ---
POLYMARKET_WALLET = os.getenv("POLYMARKET_WALLET", "0xa1d57d329227c75b12b09f927fb3d6d6ef8f1343")
POLYMARKET_REF_LINK = os.getenv("POLYMARKET_REF_LINK", "https://polymarket.com/?r=1kto1m")
POLYMARKET_REF_CODE = os.getenv("POLYMARKET_REF_CODE", "1kto1m")
TELEGRAM_LINK = os.getenv("TELEGRAM_LINK", "https://t.me/girlmathpoly")
POLYMARKET_PROFILE = "https://polymarket.com/@1kto1m"

# --- API Endpoints ---
GAMMA_API_BASE = "https://gamma-api.polymarket.com"
DATA_API_BASE = "https://data-api.polymarket.com"

# --- Scheduler ---
TWEETS_PER_DAY = 8
TRENDING_INTERVAL_HOURS = 4
PORTFOLIO_INTERVAL_HOURS = 6
VIRAL_INTERVAL_HOURS = 5

# --- Tweet Settings ---
MAX_TWEET_LENGTH = 280
REPLY_DELAY_MIN = 30   # seconds before auto-reply
REPLY_DELAY_MAX = 90
TWEET_JITTER_MIN = 5   # minutes of random jitter on schedule
TWEET_JITTER_MAX = 25

# --- Auto-Reply Template ---
AUTO_REPLY_TEXT = (
    f"🎯 Trade on Polymarket → {POLYMARKET_REF_LINK}\n"
    f"Or enter code \"{POLYMARKET_REF_CODE}\" in Settings within 24hrs of signup!\n\n"
    f"💎 Premium signals: {TELEGRAM_LINK}"
)

# --- Cookie file ---
COOKIES_FILE = "cookies.json"
TELEGRAM_ENABLED = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)
TWEET_HISTORY_FILE = "data/tweet_history.json"
