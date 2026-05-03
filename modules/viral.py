"""Viral content module — tweets designed for maximum engagement."""

import random
import logging

from polymarket.gamma_api import get_trending_markets, get_hot_events, format_market_summary
from content_generator import generate_tweet
from twitter_client import post_tweet_with_ref, get_recent_tweet_texts
from templates.prompts import VIRAL_PROMPT

logger = logging.getLogger(__name__)

MODULE = "viral"

# Viral angles to rotate through
VIRAL_ANGLES = [
    "Write a contrarian hot take about one of these markets. Be bold and provocative.",
    "Write an educational tweet explaining what prediction markets are and why they matter. Make it accessible to newcomers.",
    "Write a tweet comparing what Twitter/social media thinks vs what Polymarket odds say. Highlight the gap.",
    "Write a funny/meme-worthy observation about one of these markets. Make people laugh and retweet.",
    "Write an engagement-bait tweet asking followers their opinion on a market. Make them want to reply.",
    "Write a tweet about how prediction markets predicted something before mainstream media. Sound impressed.",
    "Write a tweet about the most surprising or absurd market you see in the data. Express genuine surprise.",
    "Write a tweet sharing a bold prediction on one of these markets. Be specific with numbers.",
    "Write a 'did you know' style tweet about an interesting Polymarket fact from the data.",
    "Write a tweet that starts with 'The market is telling us something...' and share an insight.",
]


def _build_context(markets: list[dict], events: list[dict]) -> str:
    """Build context combining markets and events."""
    lines = ["Current hot Polymarket data:\n"]

    lines.append("TOP MARKETS BY VOLUME:")
    for i, m in enumerate(markets[:8], 1):
        s = format_market_summary(m)
        lines.append(
            f"  {i}. \"{s['question']}\" — YES: {s['yes_pct']}% "
            f"| 24h Vol: ${s['volume_24h']:,.0f} "
            f"| Change: {s['one_day_change'] or 'N/A'}"
        )

    if events:
        lines.append("\nHOT EVENTS:")
        for i, e in enumerate(events[:5], 1):
            lines.append(
                f"  {i}. \"{e.get('title', 'Unknown')}\" "
                f"| Volume: ${e.get('volume', 0):,.0f}"
            )

    return "\n".join(lines)


async def run():
    """Execute the viral module."""
    logger.info(f"[{MODULE}] Starting viral module...")

    try:
        markets = await get_trending_markets(limit=15)
        events = await get_hot_events(limit=5)
    except Exception as e:
        logger.error(f"[{MODULE}] Failed to fetch data: {e}")
        return

    if not markets:
        logger.warning(f"[{MODULE}] No market data")
        return

    # Pick a random viral angle
    angle = random.choice(VIRAL_ANGLES)
    context = _build_context(markets, events)
    full_context = f"{context}\n\nINSTRUCTION: {angle}"

    recent = get_recent_tweet_texts(50)

    tweet = generate_tweet(VIRAL_PROMPT, full_context)
    if tweet and tweet not in recent:
        await post_tweet_with_ref(tweet, MODULE)
    else:
        # Try with a different angle
        angle2 = random.choice([a for a in VIRAL_ANGLES if a != angle])
        full_context2 = f"{context}\n\nINSTRUCTION: {angle2}"
        tweet = generate_tweet(VIRAL_PROMPT, full_context2)
        if tweet and tweet not in recent:
            await post_tweet_with_ref(tweet, MODULE)
        else:
            logger.warning(f"[{MODULE}] Could not generate non-duplicate tweet")

    logger.info(f"[{MODULE}] Done")
