"""Simple in-process rate limiting for expensive endpoints (e.g. /api/chat).

This is a per-key fixed-window limiter. It is intentionally minimal and does not
depend on Redis; for multi-replica deployments it only bounds per-instance rate,
which is acceptable for a V1 guard against runaway LLM calls.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque


class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: float):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            events = self._events[key]
            while events and now - events[0] > self.window_seconds:
                events.popleft()
            if len(events) >= self.max_requests:
                return False
            events.append(now)
            return True


# 20 requests per minute per key by default.
chat_limiter = RateLimiter(max_requests=20, window_seconds=60)
