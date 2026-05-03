# Poly Twitter Bot 🐦

Automated Polymarket content bot for X (Twitter). Posts trending markets, portfolio updates, and viral content with auto-reply referral links.

## Features

- **Trending Markets** — Fetches hot Polymarket events and tweets about them
- **Portfolio Sharing** — Pulls real trade data from your wallet and shares wins
- **Viral Content** — Rotates through 10+ viral tweet formats for max engagement
- **Auto-Reply Ref Link** — Every tweet gets an automatic reply with your Polymarket referral link + Telegram
- **No API Key Needed** — Uses Twikit (Twitter's internal API), no developer account required
- **AI-Powered** — Groq (LLaMA 3.3 70B) generates natural, engaging tweets
- **Railway Ready** — Deploy as a worker process on Railway

## Schedule (8 tweets/day)

| Time (UTC) | Time (TR) | Module | Description |
|------------|-----------|--------|-------------|
| 06:00 | 09:00 | Trending | Morning trend report |
| 08:00 | 11:00 | Viral | Viral attempt #1 |
| 10:00 | 13:00 | Portfolio | Trade sharing |
| 12:00 | 15:00 | Trending | Afternoon update |
| 14:00 | 17:00 | Viral | Viral attempt #2 |
| 16:00 | 19:00 | Portfolio | Evening portfolio |
| 18:00 | 21:00 | Viral | Evening viral |
| 20:00 | 23:00 | Trending | Night trend |

Each tweet has 5-25 min random jitter + 30-90s delay before ref reply.

## Setup

### 1. Install
```bash
pip install -r requirements.txt
```

### 2. Configure `.env`
```env
X_USERNAME=your_twitter_handle
X_EMAIL=your_email@example.com
X_PASSWORD=your_password

GROQ_API_KEY=gsk_...

POLYMARKET_WALLET=0x...
POLYMARKET_REF_LINK=https://polymarket.com/?r=your_code
POLYMARKET_REF_CODE=your_code
TELEGRAM_LINK=https://t.me/your_channel
```

### 3. Run Locally
```bash
python main.py
```

### 4. Deploy to Railway
1. Push to GitHub
2. Create new project on Railway
3. Add environment variables from `.env`
4. Railway auto-detects `Procfile` and runs as worker

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.11+ |
| Twitter | Twikit (no API key) |
| AI | Groq (LLaMA 3.3 70B) |
| Scheduler | APScheduler |
| HTTP | httpx (async) |
| Deploy | Railway (worker) |
