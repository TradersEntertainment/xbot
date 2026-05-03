"""Twikit-based Twitter client — no API key needed."""

import asyncio
import json
import os
import random
import logging
from datetime import datetime

from twikit import Client

import config
import telegram_notifier

logger = logging.getLogger(__name__)

_client: Client | None = None
_logged_in = False


async def _get_client() -> Client:
    """Get or create an authenticated Twikit client."""
    global _client, _logged_in

    if _client is None:
        _client = Client("en-US")

    if not _logged_in:
        # Try loading cookies first
        if os.path.exists(config.COOKIES_FILE):
            try:
                _client.load_cookies(config.COOKIES_FILE)
                _logged_in = True
                logger.info("Loaded session from cookies file")
                return _client
            except Exception as e:
                logger.warning(f"Cookie load failed, will re-login: {e}")

        # Fresh login
        logger.info("Logging into X as @%s ...", config.X_USERNAME)
        await _client.login(
            auth_info_1=config.X_USERNAME,
            auth_info_2=config.X_EMAIL,
            password=config.X_PASSWORD,
        )
        _client.save_cookies(config.COOKIES_FILE)
        _logged_in = True
        logger.info("Login successful, cookies saved")

    return _client


def _save_tweet_record(tweet_id: str, text: str, module: str):
    """Append a record to the tweet history JSON file."""
    os.makedirs("data", exist_ok=True)
    history_file = config.TWEET_HISTORY_FILE
    history = []
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []

    history.append({
        "id": tweet_id,
        "text": text,
        "module": module,
        "timestamp": datetime.utcnow().isoformat(),
    })

    # Keep last 500 tweets
    history = history[-500:]

    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


async def post_tweet_with_ref(text: str, module: str = "unknown") -> str | None:
    """Post a tweet, then auto-reply with the referral link.

    Returns the main tweet ID or None on failure.
    """
    client = await _get_client()

    try:
        # Post main tweet
        main_tweet = await client.create_tweet(text=text)
        main_id = main_tweet.id
        logger.info(f"[{module}] Tweet posted: {main_id}")
        _save_tweet_record(main_id, text, module)

        # Wait before replying (look natural)
        delay = random.randint(config.REPLY_DELAY_MIN, config.REPLY_DELAY_MAX)
        logger.info(f"Waiting {delay}s before auto-reply...")
        await asyncio.sleep(delay)

        # Auto-reply with ref link
        await client.create_tweet(
            text=config.AUTO_REPLY_TEXT,
            reply_to=main_id,
        )
        logger.info(f"[{module}] Ref reply posted under tweet {main_id}")

        # Notify Telegram
        await telegram_notifier.notify_tweet(text, module, main_id)

        return main_id

    except Exception as e:
        logger.error(f"[{module}] Failed to post tweet: {e}")
        await telegram_notifier.notify_error(module, str(e))
        # Reset login state in case of auth issues
        global _logged_in
        _logged_in = False
        return None


async def post_thread_with_ref(tweets: list[str], module: str = "unknown") -> str | None:
    """Post a thread (list of tweets), then auto-reply with ref link on the last tweet.

    Returns the first tweet ID or None on failure.
    """
    if not tweets:
        return None

    client = await _get_client()
    first_id = None
    last_id = None

    try:
        for i, text in enumerate(tweets):
            if i == 0:
                tweet = await client.create_tweet(text=text)
                first_id = tweet.id
                last_id = tweet.id
            else:
                tweet = await client.create_tweet(text=text, reply_to=last_id)
                last_id = tweet.id

            logger.info(f"[{module}] Thread tweet {i+1}/{len(tweets)} posted: {tweet.id}")
            _save_tweet_record(tweet.id, text, module)

            # Small delay between thread tweets
            if i < len(tweets) - 1:
                await asyncio.sleep(random.randint(3, 8))

        # Auto-reply ref link on the last tweet
        delay = random.randint(config.REPLY_DELAY_MIN, config.REPLY_DELAY_MAX)
        await asyncio.sleep(delay)
        await client.create_tweet(
            text=config.AUTO_REPLY_TEXT,
            reply_to=last_id,
        )
        logger.info(f"[{module}] Ref reply posted under thread")

        # Notify Telegram
        await telegram_notifier.notify_thread(tweets, module, first_id)

        return first_id

    except Exception as e:
        logger.error(f"[{module}] Failed to post thread: {e}")
        await telegram_notifier.notify_error(module, str(e))
        global _logged_in
        _logged_in = False
        return None


def get_recent_tweet_texts(limit: int = 50) -> list[str]:
    """Get recent tweet texts for duplicate checking."""
    if not os.path.exists(config.TWEET_HISTORY_FILE):
        return []
    try:
        with open(config.TWEET_HISTORY_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)
        return [h["text"] for h in history[-limit:]]
    except Exception:
        return []
