"""Groq-powered tweet content generator with dynamic style settings."""

import logging
from groq import Groq
import config
import bot_settings

logger = logging.getLogger(__name__)

_client = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=config.GROQ_API_KEY)
    return _client


def generate_tweet(system_prompt: str, user_context: str) -> str:
    """Generate a single tweet using Groq LLM with dynamic settings."""
    client = _get_client()
    temperature = bot_settings.get_temperature()
    style_mod = bot_settings.get_style_modifier()

    # Inject style modifier into the prompt
    full_prompt = system_prompt + f"\n\nSTYLE OVERRIDE: {style_mod}"

    try:
        completion = client.chat.completions.create(
            model=config.GROQ_MODEL,
            messages=[
                {"role": "system", "content": full_prompt},
                {"role": "user", "content": user_context},
            ],
            temperature=temperature,
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
    """Generate a thread (multiple tweets) using Groq LLM with dynamic settings."""
    client = _get_client()
    temperature = bot_settings.get_temperature()
    style_mod = bot_settings.get_style_modifier()

    full_prompt = system_prompt + f"\n\nSTYLE OVERRIDE: {style_mod}"

    try:
        completion = client.chat.completions.create(
            model=config.GROQ_MODEL,
            messages=[
                {"role": "system", "content": full_prompt},
                {"role": "user", "content": user_context},
            ],
            temperature=temperature,
            max_tokens=800,
        )
        raw = completion.choices[0].message.content.strip()
        tweets = [t.strip() for t in raw.split("|||") if t.strip()]
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


def preview_tweet(module: str, context: str) -> str:
    """Generate a preview tweet (for dashboard) without posting."""
    from templates.prompts import TRENDING_PROMPT, PORTFOLIO_PROMPT, VIRAL_PROMPT

    prompts = {
        "trending": TRENDING_PROMPT,
        "portfolio": PORTFOLIO_PROMPT,
        "viral": VIRAL_PROMPT,
    }
    prompt = prompts.get(module, TRENDING_PROMPT)
    return generate_tweet(prompt, context)
