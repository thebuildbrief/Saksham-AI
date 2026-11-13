"""HTTP-only client for the externally isolated Judge0 execution service."""
import json
from urllib.parse import urlsplit
from typing import Any, Dict
import httpx
from app.core.config import settings

JUDGE0_LANG_IDS = {"python": 71, "javascript": 63, "cpp": 54, "java": 62}
MAX_PROVIDER_RESPONSE_BYTES = 64 * 1024


class ExecutionProviderError(Exception):
    """Remote execution provider failed or has unsafe configuration."""


class ExecutionOutputLimitExceeded(Exception):
    """Remote provider response exceeded the configured response bound."""


class Judge0Adapter:
    def __init__(self, api_url: str, api_key: str):
        parts = urlsplit(api_url)
        local_http = parts.scheme == "http" and parts.hostname in {"localhost", "127.0.0.1", "::1"} and settings.APP_ENV.lower() not in {"production", "prod"}
        if not parts.hostname or (parts.scheme != "https" and not local_http) or parts.username or parts.password:
            raise ExecutionProviderError("Execution provider URL must use HTTPS")
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key

    async def execute(self, language: str, source_code: str, stdin: str = "") -> Dict[str, Any]:
        language_id = JUDGE0_LANG_IDS.get(language.lower())
        if language_id is None:
            raise ValueError("Unsupported execution language")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-RapidAPI-Key"] = self.api_key
            headers["X-RapidAPI-Host"] = urlsplit(self.api_url).hostname or ""
        payload = {
            "source_code": source_code, "language_id": language_id, "stdin": stdin,
            "cpu_time_limit": settings.CODE_CPU_TIME_LIMIT, "cpu_extra_time": 1.0,
            "wall_time_limit": settings.CODE_WALL_TIME_LIMIT, "memory_limit": settings.CODE_MEMORY_LIMIT_KB,
        }
        endpoint = f"{self.api_url}/submissions?base64_encoded=false&wait=true"
        try:
            async with httpx.AsyncClient(timeout=settings.CODE_PROVIDER_TIMEOUT_SECONDS) as client:
                async with client.stream("POST", endpoint, json=payload, headers=headers) as response:
                    if response.status_code not in (200, 201):
                        raise ExecutionProviderError("Execution provider returned an error")
                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        if len(body) + len(chunk) > MAX_PROVIDER_RESPONSE_BYTES:
                            raise ExecutionOutputLimitExceeded
                        body.extend(chunk)
        except (ExecutionProviderError, ExecutionOutputLimitExceeded):
            raise
        except httpx.HTTPError as exc:
            raise ExecutionProviderError("Execution provider is unavailable") from exc
        try:
            data = json.loads(body)
            return {
                "stdout": data.get("stdout") or "", "stderr": data.get("stderr") or "",
                "compile_output": data.get("compile_output") or "",
                "time_ms": int(float(data.get("time") or 0.0) * 1000),
                "memory_kb": int(data.get("memory") or 0),
                "status_desc": data.get("status", {}).get("description", "Runtime Error"),
            }
        except (ValueError, TypeError, AttributeError, KeyError) as exc:
            raise ExecutionProviderError("Execution provider returned an invalid response") from exc
