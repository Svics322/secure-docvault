import time
import logging
from collections import defaultdict

logger = logging.getLogger("rate_limiter")

class SlidingWindowRateLimiter:
    def __init__(self):
        self.request_history = defaultdict(list)

    def is_rate_limited(self, client_ip: str, endpoint_type: str, limit: int, window_seconds: int = 60) -> tuple[bool, int]:
        key = f"{client_ip}:{endpoint_type}"
        current_time = time.time()
        
        # Очищення міток запитів, що вийшли за межі часового вікна
        self.request_history[key] = [
            t for t in self.request_history[key] if current_time - t < window_seconds
        ]
        
        if len(self.request_history[key]) >= limit:
            oldest_request = self.request_history[key][0]
            retry_after = int(window_seconds - (current_time - oldest_request)) + 1
            logger.warning(f"[RATE LIMIT] IP: {client_ip} | Endpoint: '{endpoint_type}' | Exceeded limit ({limit}/{window_seconds}s) | Retry-After: {retry_after}s")
            return True, max(1, retry_after)
        
        self.request_history[key].append(current_time)
        return False, 0

rate_limiter = SlidingWindowRateLimiter()