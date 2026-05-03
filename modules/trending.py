"""Trending markets module — tweets about the hottest Polymarket events."""

import random
import logging

import bot_settings
from polymarket.gamma_api import get_trending_markets, format_market_summary
from content_generator import generate_tweet, generate_thread
from twitter_client import post_tweet_with_ref, post_thread_with_ref, get_recent_tweet_texts
from templates.prompts import TRENDING_PROMPT, THREAD_PROMPT

logger = logging.getLogger(__name__)

MODULE = "trending"


def _build_context(markets: list[dict]) -> str:
    """Build a context string from market data for the LLM."""
    lines = []
    for i, m in enumerate(markets[:10], 1):
        s = format_market_summary(m)
        line = (
            f"{i}. {s['question']}\n"
            f"   YES: {s['yes_pct']}% | NO: {s['no_pct']}%\n"
            f"   24h Volume: ${s['volume_24h']:,.0f}\n"
            f"   24h Price Change: {s['one_day_change'] or 'N/A'}\n"
        )
        lines.append(line)
    return "Here are today's trending Polymarket markets:\n\n" + "\n".join(lines)


async def run():
    """Execute the trending module — fetch markets and tweet."""
    if bot_settings.is_paused():
        logger.info(f"[{MODULE}] Bot is paused, skipping")
        return
    if not bot_settings.get().get("trending_enabled", True):
        logger.info(f"[{MODULE}] Module disabled, skipping")
        return

    logger.info(f"[{MODULE}] Starting trending module...")

    try:
        markets = await get_trending_markets(limit=20)
    except Exception as e:
        logger.error(f"[{MODULE}] Failed to fetch markets: {e}")
        return

    if not markets:
        logger.warning(f"[{MODULE}] No markets returned")
        return

    context = _build_context(markets)
    recent = get_recent_tweet_texts(50)

    # Decide: single tweet or thread (20% chance for thread)
    if random.random() < 0.2 and len(markets) >= 3:
        logger.info(f"[{MODULE}] Generating thread...")
        thread_context = context + "\n\nWrite a 3-tweet thread about the most interesting trending markets."
        tweets = generate_thread(THREAD_PROMPT, thread_context)
        if tweets and tweets[0] not in recent:
            await post_thread_with_ref(tweets, MODULE)
        else:
            logger.info(f"[{MODULE}] Thread was duplicate or empty, skipping")
    else:
        logger.info(f"[{MODULE}] Generating single tweet...")
        tweet = generate_tweet(TRENDING_PROMPT, context)
        if tweet and tweet not in recent:
            await post_tweet_with_ref(tweet, MODULE)
        else:
            logger.info(f"[{MODULE}] Tweet was duplicate or empty, retrying with different temp...")
            tweet = generate_tweet(TRENDING_PROMPT, context + "\nWrite something completely different from usual.")
            if tweet and tweet not in recent:
                await post_tweet_with_ref(tweet, MODULE)

    logger.info(f"[{MODULE}] Done")
