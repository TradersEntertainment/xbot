import httpx
import logging

logger = logging.getLogger(__name__)

GAMMA_BASE = "https://gamma-api.polymarket.com"


async def get_trending_markets(limit: int = 20) -> list[dict]:
    """Fetch active markets sorted by volume (most traded = trending)."""
    url = f"{GAMMA_BASE}/markets"
    params = {
        "active": "true",
        "closed": "false",
        "limit": limit,
        "order": "volume24hr",
        "ascending": "false",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        markets = resp.json()

    # Filter out micro-markets (5min up/down etc) for tweet content
    filtered = []
    for m in markets:
        slug = m.get("slug", "")
        # Skip very short-term binary markets
        if any(x in slug for x in ["updown-5m", "updown-1m", "updown-15m"]):
            continue
        filtered.append(m)

    return filtered[:limit]


async def get_hot_events(limit: int = 10) -> list[dict]:
    """Fetch events with highest recent volume."""
    url = f"{GAMMA_BASE}/events"
    params = {
        "active": "true",
        "closed": "false",
        "limit": limit,
        "order": "volume24hr",
        "ascending": "false",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()


async def get_events_by_tag(tag: str, limit: int = 10) -> list[dict]:
    """Fetch events by tag/category slug."""
    url = f"{GAMMA_BASE}/events"
    params = {
        "active": "true",
        "closed": "false",
        "tag": tag,
        "limit": limit,
        "order": "volume",
        "ascending": "false",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()


async def get_market_by_slug(slug: str) -> dict | None:
    """Fetch a single market by slug."""
    url = f"{GAMMA_BASE}/markets"
    params = {"slug": slug}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        return data[0] if data else None


def format_market_summary(market: dict) -> dict:
    """Extract the useful fields from a raw market object."""
    outcomes = market.get("outcomes", "[]")
    prices = market.get("outcomePrices", "[]")

    # Parse JSON strings if needed
    if isinstance(outcomes, str):
        import json
        try:
            outcomes = json.loads(outcomes)
            prices = json.loads(prices)
        except Exception:
            outcomes = []
            prices = []

    yes_price = None
    no_price = None
    if len(prices) >= 2:
        try:
            yes_price = round(float(prices[0]) * 100, 1)
            no_price = round(float(prices[1]) * 100, 1)
        except (ValueError, TypeError):
            pass

    volume_24h = market.get("volume24hr", 0)
    volume_total = market.get("volumeNum", market.get("volume", 0))

    return {
        "question": market.get("question", market.get("title", "Unknown")),
        "slug": market.get("slug", ""),
        "yes_pct": yes_price,
        "no_pct": no_price,
        "volume_24h": volume_24h,
        "volume_total": volume_total,
        "one_day_change": market.get("oneDayPriceChange"),
        "one_week_change": market.get("oneWeekPriceChange"),
        "image": market.get("image", ""),
        "end_date": market.get("endDate", ""),
        "url": f"https://polymarket.com/event/{market.get('slug', '')}",
    }
