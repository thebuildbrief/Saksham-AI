"""Distributed execution concurrency and per-user request quotas."""
import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass
from redis.asyncio import Redis
from app.core.config import secret_value, settings


class QuotaStoreUnavailable(Exception):
    """The production shared quota store could not be reached."""


@dataclass
class Lease:
    backend: str
    token: str
    redis: Redis | None = None


_client: Redis | None = None
_client_url: str | None = None
_local_lock = threading.Lock()
_local_requests = defaultdict(deque)
_LOCAL_SLOTS = threading.BoundedSemaphore(max(1, settings.CODE_MAX_CONCURRENT))


async def acquire_execution_lease(user_id: str) -> Lease | None:
    """Limit a user to N requests/minute and cap global simultaneous executions."""
    global _client, _client_url
    redis_url = secret_value(settings.REDIS_URL)
    if not redis_url:
        if settings.APP_ENV.lower() in {"production", "prod"}:
            raise QuotaStoreUnavailable
        now = time.monotonic()
        with _local_lock:
            requests = _local_requests[user_id]
            while requests and now - requests[0] >= 60:
                requests.popleft()
            if len(requests) >= settings.CODE_MAX_REQUESTS_PER_MINUTE:
                return None
            requests.append(now)
            if not _LOCAL_SLOTS.acquire(blocking=False):
                return None
        return Lease("local", user_id)
    try:
        if _client is None or _client_url != redis_url:
            if _client is not None:
                await _client.aclose()
            _client = Redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=2, socket_timeout=2, health_check_interval=30)
            _client_url = redis_url
        count = await _client.eval(
            "local n=redis.call('INCR',KEYS[1]); if n==1 then redis.call('EXPIRE',KEYS[1],60) end; return n",
            1, f"saksham:code:rate:{user_id}",
        )
        if int(count) > settings.CODE_MAX_REQUESTS_PER_MINUTE:
            return None
        token = uuid.uuid4().hex
        ttl_ms = int((settings.CODE_REQUEST_TIMEOUT_SECONDS + 10) * 1000)
        acquired = await _client.eval(
            "local tm=redis.call('TIME'); local now=tm[1]*1000+math.floor(tm[2]/1000); "
            "redis.call('ZREMRANGEBYSCORE',KEYS[1],'-inf',now); "
            "if redis.call('ZCARD',KEYS[1])>=tonumber(ARGV[1]) then return 0 end; "
            "redis.call('ZADD',KEYS[1],now+tonumber(ARGV[2]),ARGV[3]); "
            "redis.call('PEXPIRE',KEYS[1],tonumber(ARGV[2])+1000); return 1",
            1, "saksham:code:active", settings.CODE_MAX_CONCURRENT, ttl_ms, token,
        )
        if not int(acquired):
            return None
        return Lease("redis", token, _client)
    except Exception as exc:
        raise QuotaStoreUnavailable from exc


async def release_execution_lease(lease: Lease) -> None:
    if lease.backend == "local":
        _LOCAL_SLOTS.release()
        return
    if lease.redis is not None:
        try:
            await lease.redis.zrem("saksham:code:active", lease.token)
        except Exception as exc:
            raise QuotaStoreUnavailable from exc
