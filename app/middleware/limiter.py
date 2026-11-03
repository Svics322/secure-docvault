from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict, deque

logger = logging.getLogger("middleware.limiter")


class SlidingWindowRateLimiter:
    def __init__(self, max_keys: int = 50_000, cleanup_interval: float = 60.0) -> None:
        self._history: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()
        self._max_keys = max_keys
        self._cleanup_interval = cleanup_interval
        self._last_cleanup = 0.0

    def _cleanup(self, now: float, window_seconds: int) -> None:
        if now - self._last_cleanup < self._cleanup_interval:
            return
        self._last_cleanup = now

        stale_keys = []
        for key, timestamps in self._history.items():
            while timestamps and now - timestamps[0] >= window_seconds:
                timestamps.popleft()
            if not timestamps:
                stale_keys.append(key)

        for key in stale_keys:
            self._history.pop(key, None)

        if len(self._history) > self._max_keys:
            overflow = len(self._history) - self._max_keys
            for key in list(self._history.keys())[:overflow]:
                self._history.pop(key, None)
            logger.warning(
                "Rate limiter: досягнуто ліміт ключів, видалено %s найстаріших", overflow
            )

    def is_rate_limited(
        self,
        client_ip: str,
        endpoint_type: str,
        limit: int,
        window_seconds: int = 60,
    ) -> tuple[bool, int]:
        key = f"{client_ip}:{endpoint_type}"
        now = time.monotonic()

        with self._lock:
            self._cleanup(now, window_seconds)
            timestamps = self._history[key]

            while timestamps and now - timestamps[0] >= window_seconds:
                timestamps.popleft()

            if len(timestamps) >= limit:
                retry_after = int(window_seconds - (now - timestamps[0])) + 1
                logger.warning(
                    "[RATE LIMIT] IP: %s | Endpoint: '%s' | Exceeded limit (%s/%ss) "
                    "| Retry-After: %ss",
                    client_ip,
                    endpoint_type,
                    limit,
                    window_seconds,
                    max(1, retry_after),
                )
                return True, max(1, retry_after)

            timestamps.append(now)
            return False, 0

    def reset(self) -> None:
        with self._lock:
            self._history.clear()
            self._last_cleanup = 0.0


rate_limiter = SlidingWindowRateLimiter()
