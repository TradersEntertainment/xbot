"""Dynamic bot settings — can be changed from the dashboard at runtime."""

import json
import os
import logging

logger = logging.getLogger(__name__)

SETTINGS_FILE = "data/settings.json"

DEFAULT_SETTINGS = {
    # Content style
    "aggressiveness": 5,        # 1-10: 1=safe/professional, 10=ultra bold/degen
    "style": "balanced",        # professional, balanced, casual, degen, educational
    "language": "en",

    # Schedule
    "tweets_per_day": 8,
    "trending_enabled": True,
    "portfolio_enabled": True,
    "viral_enabled": True,
    "auto_reply_enabled": True,

    # Timing (UTC hours)
    "schedule": {
        "trending": [6, 12, 20],
        "portfolio": [10, 16],
        "viral": [8, 14, 18],
    },

    # Bot state
    "paused": False,
}

_settings: dict | None = None


def _ensure_dir():
    os.makedirs("data", exist_ok=True)


def load() -> dict:
    """Load settings from file, or create defaults."""
    global _settings
    _ensure_dir()

    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                _settings = json.load(f)
            # Merge with defaults for any missing keys
            for k, v in DEFAULT_SETTINGS.items():
                if k not in _settings:
                    _settings[k] = v
            return _settings
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")

    _settings = DEFAULT_SETTINGS.copy()
    save()
    return _settings


def save():
    """Save current settings to file."""
    _ensure_dir()
    if _settings is None:
        return
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(_settings, f, indent=2)


def get() -> dict:
    """Get current settings (loads if not loaded yet)."""
    if _settings is None:
        return load()
    return _settings


def update(updates: dict) -> dict:
    """Update settings with partial dict and save."""
    current = get()
    for k, v in updates.items():
        if k in current:
            current[k] = v
    save()
    logger.info(f"Settings updated: {list(updates.keys())}")
    return current


def get_temperature() -> float:
    """Map aggressiveness (1-10) to LLM temperature."""
    aggr = get().get("aggressiveness", 5)
    # 1 → 0.4, 5 → 0.8, 10 → 1.3
    return 0.3 + (aggr * 0.1)


def get_style_modifier() -> str:
    """Return style instruction based on current setting."""
    style = get().get("style", "balanced")
    aggr = get().get("aggressiveness", 5)

    modifiers = {
        "professional": (
            "Be professional and analytical. Use data and facts. "
            "Avoid slang, memes, and excessive emojis. Sound like a Wall Street analyst."
        ),
        "balanced": (
            "Be confident and data-driven but approachable. "
            "Mix analysis with personality. Use emojis sparingly."
        ),
        "casual": (
            "Be casual and conversational. Write like you're texting a friend about markets. "
            "Use informal language and emojis freely."
        ),
        "degen": (
            "Be ultra-bold and provocative. Use crypto/degen slang (ape in, send it, LFG). "
            "Make controversial takes. Be fearless and hype-driven. WAGMI energy."
        ),
        "educational": (
            "Be informative and helpful. Explain concepts clearly for newcomers. "
            "Use 'did you know' style. Make prediction markets accessible to everyone."
        ),
    }

    base = modifiers.get(style, modifiers["balanced"])

    if aggr >= 8:
        base += " Be EXTREMELY bold with your takes. Make people stop scrolling."
    elif aggr >= 6:
        base += " Don't be afraid to make bold claims."
    elif aggr <= 2:
        base += " Stay conservative and factual. Avoid controversy."

    return base


def is_paused() -> bool:
    return get().get("paused", False)
