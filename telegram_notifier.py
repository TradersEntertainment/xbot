"""Telegram notifier — sends posted tweets to a Telegram group for monitoring."""

import logging
import httpx
import config

logger = logging.getLogger(__name__)

TELEGRAM_API = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}"


async def send_message(text: str, disable_preview: bool = True):
    """Send a message to the configured Telegram chat."""
    if not config.TELEGRAM_ENABLED:
        return

    payload = {
        "chat_id": config.TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": disable_preview,
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(f"{TELEGRAM_API}/sendMessage", json=payload)
            resp.raise_for_status()
            logger.info("Telegram notification sent")
    except Exception as e:
        logger.error(f"Telegram send failed: {e}")


async def notify_tweet(tweet_text: str, module: str, tweet_id: str | None = None):
    """Notify Telegram about a posted tweet."""
    tweet_url = f"https://x.com/{config.X_USERNAME}/status/{tweet_id}" if tweet_id else ""

    msg = (
        f"🐦 <b>New Tweet Posted</b>\n"
        f"📂 Module: <code>{module}</code>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{tweet_text}\n"
        f"━━━━━━━━━━━━━━━\n"
    )
    if tweet_url:
        msg += f"🔗 <a href=\"{tweet_url}\">View on X</a>\n"
    msg += f"📎 Auto-reply with ref link ✅"

    await send_message(msg)


async def notify_thread(tweets: list[str], module: str, first_id: str | None = None):
    """Notify Telegram about a posted thread."""
    tweet_url = f"https://x.com/{config.X_USERNAME}/status/{first_id}" if first_id else ""

    parts = "\n\n".join([f"🧵 {i+1}/{len(tweets)}: {t}" for i, t in enumerate(tweets)])
    msg = (
        f"🧵 <b>New Thread Posted</b>\n"
        f"📂 Module: <code>{module}</code>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{parts}\n"
        f"━━━━━━━━━━━━━━━\n"
    )
    if tweet_url:
        msg += f"🔗 <a href=\"{tweet_url}\">View on X</a>\n"
    msg += f"📎 Auto-reply with ref link ✅"

    await send_message(msg)


async def notify_error(module: str, error: str):
    """Notify Telegram about an error."""
    msg = (
        f"⚠️ <b>Bot Error</b>\n"
        f"📂 Module: <code>{module}</code>\n"
        f"❌ {error}"
    )
    await send_message(msg)


async def notify_startup():
    """Send startup notification."""
    msg = (
        f"🟢 <b>Polymarket Bot Started (Manual Queue Mode)</b>\n"
        f"👤 Account: @{config.X_USERNAME}\n"
        f"💰 Wallet: <code>{config.POLYMARKET_WALLET[:12]}...</code>\n"
        f"🔗 Ref: {config.POLYMARKET_REF_CODE}\n"
        f"📝 Tweets are now generated to the Pending Queue in the Dashboard."
    )
    await send_message(msg)
