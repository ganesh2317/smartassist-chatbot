import hashlib
import threading
import time
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse

from app.config import get_settings

settings = get_settings()


class SlidingWindowRateLimiter:
    def __init__(self):
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allowed(self, key: str, limit: int, window_seconds: int = 60) -> bool:
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            events = self._events[key]
            while events and events[0] < cutoff:
                events.popleft()
            if len(events) >= limit:
                return False
            events.append(now)
            if not events:
                self._events.pop(key, None)
            return True


limiter = SlidingWindowRateLimiter()


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
    host = forwarded or (request.client.host if request.client else "unknown")
    auth = request.headers.get("authorization", "")
    if auth:
        token_fingerprint = hashlib.sha256(auth.encode("utf-8")).hexdigest()[:16]
        return f"{host}:{token_fingerprint}"
    return host


async def rate_limit_middleware(request: Request, call_next):
    path = request.url.path
    if path in {"/auth/login", "/auth/register"}:
        limit, bucket = settings.auth_rate_limit_per_minute, "auth"
    elif path == "/chat":
        limit, bucket = settings.chat_rate_limit_per_minute, "chat"
    elif path == "/documents" and request.method == "POST":
        limit, bucket = settings.upload_rate_limit_per_minute, "upload"
    else:
        return await call_next(request)

    key = f"{bucket}:{_client_key(request)}"
    if not limiter.allowed(key, limit):
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests. Please wait a moment and try again."},
            headers={"Retry-After": "60"},
        )
    return await call_next(request)
