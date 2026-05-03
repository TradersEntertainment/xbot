"""Polymarket Twitter Bot — Main scheduler entry point.

Runs as a Railway worker process. No web server needed.
Schedules tweet modules throughout the day using APScheduler.
"""

import asyncio
import random
import logging
import signal
import sys

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

import config
from modules import trending, portfolio, viral
import telegram_notifier

# --- Logging setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("poly_bot")


async def run_with_jitter(module_fn, name: str):
    """Run a module function with random jitter to look natural."""
    jitter = random.randint(config.TWEET_JITTER_MIN * 60, config.TWEET_JITTER_MAX * 60)
    logger.info(f"[scheduler] {name} triggered, waiting {jitter}s jitter...")
    await asyncio.sleep(jitter)
    try:
        await module_fn()
    except Exception as e:
        logger.error(f"[scheduler] {name} failed: {e}", exc_info=True)


# --- Wrapper functions for APScheduler (it needs sync callables) ---
def _run_trending():
    asyncio.get_event_loop().create_task(run_with_jitter(trending.run, "trending"))

def _run_portfolio():
    asyncio.get_event_loop().create_task(run_with_jitter(portfolio.run, "portfolio"))

def _run_viral():
    asyncio.get_event_loop().create_task(run_with_jitter(viral.run, "viral"))


def create_scheduler() -> AsyncIOScheduler:
    """Create and configure the APScheduler with all tweet jobs.
    
    Schedule (UTC — Railway runs UTC):
      06:00 UTC (09:00 TR) — trending
      08:00 UTC (11:00 TR) — viral #1
      10:00 UTC (13:00 TR) — portfolio
      12:00 UTC (15:00 TR) — trending
      14:00 UTC (17:00 TR) — viral #2
      16:00 UTC (19:00 TR) — portfolio
      18:00 UTC (21:00 TR) — viral #3
      20:00 UTC (23:00 TR) — trending
    """
    scheduler = AsyncIOScheduler()

    # Trending — 3x/day
    scheduler.add_job(_run_trending, CronTrigger(hour=6, minute=0), id="trending_morning")
    scheduler.add_job(_run_trending, CronTrigger(hour=12, minute=0), id="trending_afternoon")
    scheduler.add_job(_run_trending, CronTrigger(hour=20, minute=0), id="trending_night")

    # Portfolio — 2x/day
    scheduler.add_job(_run_portfolio, CronTrigger(hour=10, minute=0), id="portfolio_midday")
    scheduler.add_job(_run_portfolio, CronTrigger(hour=16, minute=0), id="portfolio_evening")

    # Viral — 3x/day
    scheduler.add_job(_run_viral, CronTrigger(hour=8, minute=0), id="viral_1")
    scheduler.add_job(_run_viral, CronTrigger(hour=14, minute=0), id="viral_2")
    scheduler.add_job(_run_viral, CronTrigger(hour=18, minute=0), id="viral_3")

    return scheduler


async def startup_tweet():
    """Post a single tweet on startup to verify everything works."""
    logger.info("Running startup tweet to verify bot is operational...")
    try:
        await trending.run()
        logger.info("Startup tweet completed successfully!")
    except Exception as e:
        logger.error(f"Startup tweet failed: {e}", exc_info=True)


async def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("  Polymarket Twitter Bot Starting")
    logger.info(f"  Account: @{config.X_USERNAME}")
    logger.info(f"  Wallet: {config.POLYMARKET_WALLET[:10]}...")
    logger.info(f"  Ref: {config.POLYMARKET_REF_CODE}")
    logger.info("=" * 60)

    # Validate config
    if not config.X_EMAIL or not config.X_PASSWORD:
        logger.error("X_EMAIL and X_PASSWORD must be set in .env")
        sys.exit(1)
    if not config.GROQ_API_KEY:
        logger.error("GROQ_API_KEY must be set in .env")
        sys.exit(1)

    # Send Telegram startup notification
    await telegram_notifier.notify_startup()

    # Post a tweet on startup
    await startup_tweet()

    # Start scheduler
    scheduler = create_scheduler()
    scheduler.start()
    logger.info("Scheduler started. Waiting for next scheduled tweet...")

    # Print upcoming jobs
    for job in scheduler.get_jobs():
        logger.info(f"  Job: {job.id} -> next run: {job.next_run_time}")

    # Keep running
    stop_event = asyncio.Event()

    def _shutdown(sig, frame):
        logger.info(f"Received signal {sig}, shutting down...")
        stop_event.set()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    await stop_event.wait()
    scheduler.shutdown()
    logger.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
