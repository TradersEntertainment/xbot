import httpx
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

DATA_BASE = "https://data-api.polymarket.com"


async def get_user_trades(wallet: str, limit: int = 20) -> list[dict]:
    """Fetch recent trades for a wallet address."""
    url = f"{DATA_BASE}/activity"
    params = {
        "user": wallet,
        "type": "TRADE",
        "limit": limit,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()


async def get_user_activity(wallet: str, limit: int = 20) -> list[dict]:
    """Fetch all activity (trades, redeems, rebates) for a wallet."""
    url = f"{DATA_BASE}/activity"
    params = {
        "user": wallet,
        "limit": limit,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()


async def get_user_positions(wallet: str, limit: int = 20) -> list[dict]:
    """Fetch current open positions."""
    url = f"{DATA_BASE}/positions"
    params = {
        "user": wallet,
        "limit": limit,
        "sizeThreshold": "0.1",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()


def format_trade(trade: dict) -> dict:
    """Format a raw trade into a human-readable summary."""
    ts = trade.get("timestamp", 0)
    dt = datetime.utcfromtimestamp(ts) if ts else None

    return {
        "title": trade.get("title", "Unknown Market"),
        "slug": trade.get("slug", ""),
        "side": trade.get("side", ""),
        "outcome": trade.get("outcome", ""),
        "size": round(trade.get("size", 0), 2),
        "usdc_size": round(trade.get("usdcSize", 0), 2),
        "price": round(trade.get("price", 0), 4),
        "type": trade.get("type", ""),
        "time": dt.strftime("%Y-%m-%d %H:%M UTC") if dt else "",
        "icon": trade.get("icon", ""),
        "event_slug": trade.get("eventSlug", ""),
    }


def calculate_trade_pnl(trades: list[dict]) -> dict:
    """Calculate simple P&L from a list of trades on the same market."""
    total_buy = 0.0
    total_sell = 0.0
    total_redeem = 0.0

    for t in trades:
        ttype = t.get("type", "")
        usdc = t.get("usdcSize", 0)
        if ttype == "TRADE":
            if t.get("side") == "BUY":
                total_buy += usdc
            elif t.get("side") == "SELL":
                total_sell += usdc
        elif ttype == "REDEEM":
            total_redeem += usdc

    pnl = (total_sell + total_redeem) - total_buy
    return {
        "total_buy": round(total_buy, 2),
        "total_sell": round(total_sell, 2),
        "total_redeem": round(total_redeem, 2),
        "pnl": round(pnl, 2),
    }
