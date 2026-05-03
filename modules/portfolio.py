"""Portfolio module — tweets about personal trading activity."""

import logging

import bot_settings
import config
from polymarket.data_api import get_user_trades, get_user_activity, format_trade, calculate_trade_pnl
from content_generator import generate_tweet
from twitter_client import post_tweet_with_ref, get_recent_tweet_texts
from templates.prompts import PORTFOLIO_PROMPT

logger = logging.getLogger(__name__)

MODULE = "portfolio"


def _build_context(trades: list[dict], activity: list[dict]) -> str:
    """Build context from trade/activity data."""
    lines = ["Here is your recent Polymarket trading activity:\n"]

    # Format recent trades
    trade_items = [t for t in activity if t.get("type") == "TRADE"]
    redeem_items = [t for t in activity if t.get("type") == "REDEEM"]
    rebate_items = [t for t in activity if t.get("type") == "MAKER_REBATE"]

    if trade_items:
        lines.append("RECENT TRADES:")
        for t in trade_items[:8]:
            ft = format_trade(t)
            lines.append(
                f"  - {ft['side']} {ft['outcome']} on \"{ft['title']}\" "
                f"| Size: {ft['size']} shares @ ${ft['price']:.2f} "
                f"| USDC: ${ft['usdc_size']:.2f}"
            )

    if redeem_items:
        lines.append("\nRECENT WINS (REDEEMED):")
        for t in redeem_items[:5]:
            ft = format_trade(t)
            lines.append(f"  - \"{ft['title']}\" → Redeemed ${ft['usdc_size']:.2f}")

    if rebate_items:
        total_rebate = sum(t.get("usdcSize", 0) for t in rebate_items)
        lines.append(f"\nMAKER REBATES EARNED: ${total_rebate:.2f}")

    # P&L summary
    pnl = calculate_trade_pnl(activity)
    lines.append(f"\nSESSION SUMMARY:")
    lines.append(f"  Total bought: ${pnl['total_buy']:.2f}")
    lines.append(f"  Total sold: ${pnl['total_sell']:.2f}")
    lines.append(f"  Total redeemed: ${pnl['total_redeem']:.2f}")
    lines.append(f"  Net P&L: ${pnl['pnl']:+.2f}")

    return "\n".join(lines)


async def run():
    """Execute the portfolio module."""
    if bot_settings.is_paused():
        logger.info(f"[{MODULE}] Bot is paused, skipping")
        return
    if not bot_settings.get().get("portfolio_enabled", True):
        logger.info(f"[{MODULE}] Module disabled, skipping")
        return

    logger.info(f"[{MODULE}] Starting portfolio module...")
    wallet = config.POLYMARKET_WALLET

    try:
        activity = await get_user_activity(wallet, limit=20)
    except Exception as e:
        logger.error(f"[{MODULE}] Failed to fetch activity: {e}")
        return

    if not activity:
        logger.warning(f"[{MODULE}] No activity found")
        return

    trades = [a for a in activity if a.get("type") == "TRADE"]
    context = _build_context(trades, activity)
    recent = get_recent_tweet_texts(50)

    tweet = generate_tweet(PORTFOLIO_PROMPT, context)
    if tweet and tweet not in recent:
        await post_tweet_with_ref(tweet, MODULE)
    else:
        logger.info(f"[{MODULE}] Tweet was duplicate or empty, trying again...")
        tweet = generate_tweet(
            PORTFOLIO_PROMPT,
            context + "\nFocus on a specific interesting trade and share your reasoning."
        )
        if tweet and tweet not in recent:
            await post_tweet_with_ref(tweet, MODULE)

    logger.info(f"[{MODULE}] Done")
