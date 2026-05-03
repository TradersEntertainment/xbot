"""FastAPI server — serves dashboard + API + runs bot scheduler."""

import asyncio
import json
import os
import random
import sys
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

import config
import bot_settings
import telegram_notifier
from modules import trending, portfolio, viral
from polymarket.gamma_api import get_trending_markets, format_market_summary
from polymarket.data_api import get_user_activity
from content_generator import preview_tweet

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("poly_bot")

scheduler: AsyncIOScheduler | None = None


# ─── Scheduler helpers ───────────────────────────────────────────────

async def run_with_jitter(module_fn, name: str):
    jitter = random.randint(config.TWEET_JITTER_MIN * 60, config.TWEET_JITTER_MAX * 60)
    logger.info(f"[scheduler] {name} triggered, waiting {jitter}s jitter...")
    await asyncio.sleep(jitter)
    try:
        await module_fn()
    except Exception as e:
        logger.error(f"[scheduler] {name} failed: {e}", exc_info=True)


def _run_trending():
    asyncio.get_event_loop().create_task(run_with_jitter(trending.run, "trending"))

def _run_portfolio():
    asyncio.get_event_loop().create_task(run_with_jitter(portfolio.run, "portfolio"))

def _run_viral():
    asyncio.get_event_loop().create_task(run_with_jitter(viral.run, "viral"))


def create_scheduler() -> AsyncIOScheduler:
    s = bot_settings.get().get("schedule", {})
    sched = AsyncIOScheduler()

    for i, hour in enumerate(s.get("trending", [6, 12, 20])):
        sched.add_job(_run_trending, CronTrigger(hour=hour, minute=0), id=f"trending_{i}")
    for i, hour in enumerate(s.get("portfolio", [10, 16])):
        sched.add_job(_run_portfolio, CronTrigger(hour=hour, minute=0), id=f"portfolio_{i}")
    for i, hour in enumerate(s.get("viral", [8, 14, 18])):
        sched.add_job(_run_viral, CronTrigger(hour=hour, minute=0), id=f"viral_{i}")

    return sched


# ─── FastAPI lifecycle ────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global scheduler
    logger.info("=" * 60)
    logger.info("  Polymarket Twitter Bot + Dashboard Starting")
    logger.info(f"  Account: @{config.X_USERNAME}")
    logger.info("=" * 60)

    bot_settings.load()
    await telegram_notifier.notify_startup()

    scheduler = create_scheduler()
    scheduler.start()
    logger.info("Scheduler started")
    for job in scheduler.get_jobs():
        logger.info(f"  Job: {job.id} -> next: {job.next_run_time}")

    yield

    if scheduler:
        scheduler.shutdown()
    logger.info("Bot stopped.")


app = FastAPI(title="Polymarket Bot Dashboard", lifespan=lifespan)

# Serve static files
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


# ─── Dashboard page ──────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


# ─── API Endpoints ───────────────────────────────────────────────────

@app.get("/api/status")
async def api_status():
    settings = bot_settings.get()
    jobs = []
    if scheduler:
        for job in scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            })

    # Read tweet history
    tweet_count = 0
    if os.path.exists(config.TWEET_HISTORY_FILE):
        try:
            with open(config.TWEET_HISTORY_FILE, "r", encoding="utf-8") as f:
                tweet_count = len(json.load(f))
        except Exception:
            pass

    return {
        "paused": settings.get("paused", False),
        "account": config.X_USERNAME,
        "wallet": config.POLYMARKET_WALLET[:12] + "...",
        "ref_code": config.POLYMARKET_REF_CODE,
        "tweets_posted": tweet_count,
        "upcoming_jobs": jobs,
        "server_time": datetime.utcnow().isoformat(),
    }


@app.get("/api/settings")
async def api_get_settings():
    return bot_settings.get()


@app.post("/api/settings")
async def api_update_settings(request: Request):
    body = await request.json()
    updated = bot_settings.update(body)

    # Reschedule if schedule changed
    if "schedule" in body:
        global scheduler
        if scheduler:
            scheduler.shutdown(wait=False)
        scheduler = create_scheduler()
        scheduler.start()
        logger.info("Scheduler rescheduled with new times")

    return {"status": "ok", "settings": updated}


@app.get("/api/tweets")
async def api_tweets():
    if not os.path.exists(config.TWEET_HISTORY_FILE):
        return []
    try:
        with open(config.TWEET_HISTORY_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)
        history.reverse()  # newest first
        return history[:100]
    except Exception:
        return []


@app.post("/api/bot/pause")
async def api_pause():
    bot_settings.update({"paused": True})
    await telegram_notifier.send_message("⏸ Bot paused from dashboard")
    return {"status": "paused"}


@app.post("/api/bot/resume")
async def api_resume():
    bot_settings.update({"paused": False})
    await telegram_notifier.send_message("▶️ Bot resumed from dashboard")
    return {"status": "running"}


@app.post("/api/tweet/preview")
async def api_preview(request: Request):
    body = await request.json()
    module = body.get("module", "trending")

    # Get real data for preview
    try:
        if module == "portfolio":
            activity = await get_user_activity(config.POLYMARKET_WALLET, limit=15)
            lines = []
            for a in activity[:8]:
                t = a.get("type", "")
                title = a.get("title", "Unknown")
                usdc = a.get("usdcSize", 0)
                lines.append(f"  {t}: {title} | ${usdc:.2f}")
            context = "Recent activity:\n" + "\n".join(lines)
        else:
            markets = await get_trending_markets(10)
            lines = []
            for i, m in enumerate(markets[:8], 1):
                s = format_market_summary(m)
                lines.append(f"{i}. {s['question']} | YES: {s['yes_pct']}% | Vol: ${s['volume_24h']:,.0f}")
            context = "Trending markets:\n" + "\n".join(lines)

            if module == "viral":
                context += "\n\nWrite something viral and engagement-worthy."
    except Exception as e:
        context = f"Error fetching data: {e}"

    tweet = preview_tweet(module, context)
    return {"tweet": tweet, "module": module, "chars": len(tweet)}


@app.post("/api/tweet/post")
async def api_post_tweet(request: Request):
    body = await request.json()
    text = body.get("text", "").strip()
    module = body.get("module", "manual")

    if not text:
        return JSONResponse(status_code=400, content={"error": "Tweet text is empty"})

    from twitter_client import post_tweet_with_ref
    tweet_id = await post_tweet_with_ref(text, module)

    if tweet_id:
        return {"status": "posted", "tweet_id": tweet_id}
    else:
        return JSONResponse(status_code=500, content={"error": "Failed to post tweet"})


@app.post("/api/tweet/run-module")
async def api_run_module(request: Request):
    body = await request.json()
    module = body.get("module", "trending")

    modules = {
        "trending": trending.run,
        "portfolio": portfolio.run,
        "viral": viral.run,
    }
    fn = modules.get(module)
    if not fn:
        return JSONResponse(status_code=400, content={"error": f"Unknown module: {module}"})

    # Run in background
    asyncio.create_task(fn())
    return {"status": "triggered", "module": module}
