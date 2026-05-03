"""Groq-powered tweet content generator."""

import logging
from groq import Groq
import config

logger = logging.getLogger(__name__)

_client = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=config.GROQ_API_KEY)
    return _client


def generate_tweet(system_prompt: str, user_context: str) -> str:
    """Generate a single tweet using Groq LLM."""
    client = _get_client()
    try:
        completion = client.chat.completions.create(
            model=config.GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_context},
            ],
            temperature=0.9,
            max_tokens=300,
        )
        text = completion.choices[0].message.content.strip()
        # Remove surrounding quotes if AI wraps in quotes
        if text.startswith('"') and text.endswith('"'):
            text = text[1:-1]
        # Ensure under tweet limit
        if len(text) > config.MAX_TWEET_LENGTH:
            text = text[: config.MAX_TWEET_LENGTH - 3] + "..."
        return text
    except Exception as e:
        logger.error(f"Groq generation failed: {e}")
        return ""


def generate_thread(system_prompt: str, user_context: str) -> list[str]:
    """Generate a thread (multiple tweets) using Groq LLM."""
    client = _get_client()
    try:
        completion = client.chat.completions.create(
            model=config.GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_context},
            ],
            temperature=0.9,
            max_tokens=800,
        )
        raw = completion.choices[0].message.content.strip()
        tweets = [t.strip() for t in raw.split("|||") if t.strip()]
        # Trim each tweet
        result = []
        for t in tweets:
            if t.startswith('"') and t.endswith('"'):
                t = t[1:-1]
            if len(t) > config.MAX_TWEET_LENGTH:
                t = t[: config.MAX_TWEET_LENGTH - 3] + "..."
            result.append(t)
        return result
    except Exception as e:
        logger.error(f"Groq thread generation failed: {e}")
        return []
