"""Provider-aware text generation. Provider credentials stay server-side and are never logged."""
import json
from typing import Any
import httpx
from app.core.config import secret_value, settings
from app.core.exceptions import SakshamException


class AIProviderError(Exception):
    pass


def _provider_key(provider: str) -> str:
    names = {"openai": "OPENAI_API_KEY", "groq": "GROQ_API_KEY", "anthropic": "ANTHROPIC_API_KEY", "gemini": "GEMINI_API_KEY"}
    return secret_value(getattr(settings, names.get(provider, ""), ""))


def ensure_ai_available() -> str:
    provider = settings.AI_PROVIDER.strip().lower()
    if provider == "mock":
        if settings.APP_ENV.lower() in {"production", "prod"}:
            raise SakshamException(503, "AI provider is not configured for production")
        return provider
    if provider not in {"openai", "groq", "anthropic", "gemini"} or not _provider_key(provider):
        raise SakshamException(503, "AI provider is not configured")
    return provider


async def generate_text(prompt: str, *, system: str = "You are a helpful interview coach.", max_tokens: int = 800) -> str:
    provider = ensure_ai_available()
    if provider == "mock":
        return "Tell me about a project you are proud of. What was your contribution, and what would you improve next time?"
    key = _provider_key(provider)
    headers: dict[str, str] = {"content-type": "application/json"}
    if provider in {"openai", "groq"}:
        base = "https://api.openai.com/v1/chat/completions" if provider == "openai" else "https://api.groq.com/openai/v1/chat/completions"
        headers["authorization"] = f"Bearer {key}"
        payload = {"model": settings.AI_MODEL or ("gpt-4o-mini" if provider == "openai" else "llama-3.3-70b-versatile"), "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}], "max_tokens": max_tokens}
    elif provider == "anthropic":
        base = "https://api.anthropic.com/v1/messages"
        headers.update({"x-api-key": key, "anthropic-version": "2023-06-01"})
        payload = {"model": settings.AI_MODEL or "claude-3-5-haiku-latest", "system": system, "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens}
    else:
        base = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.AI_MODEL or 'gemini-2.0-flash'}:generateContent"
        headers["x-goog-api-key"] = key
        payload = {"systemInstruction": {"parts": [{"text": system}]}, "contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"maxOutputTokens": max_tokens}}
    try:
        async with httpx.AsyncClient(timeout=settings.AI_REQUEST_TIMEOUT_SECONDS) as client:
            response = await client.post(base, headers=headers, json=payload)
            response.raise_for_status()
            data: dict[str, Any] = response.json()
        if provider in {"openai", "groq"}:
            text = data["choices"][0]["message"]["content"]
        elif provider == "anthropic":
            text = "".join(part.get("text", "") for part in data.get("content", []) if part.get("type") == "text")
        else:
            text = "".join(part.get("text", "") for part in data["candidates"][0]["content"]["parts"])
        if not isinstance(text, str) or not text.strip():
            raise ValueError("empty provider response")
        return text.strip()
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
        # Never include request URLs, prompts, response bodies, or provider tokens in client errors/logs.
        raise SakshamException(503, "AI service is temporarily unavailable") from exc
