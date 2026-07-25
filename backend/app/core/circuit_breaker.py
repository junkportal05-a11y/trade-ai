"""Circuit breaker with exponential backoff for AngelOne API calls."""
import time
import logging
from functools import wraps

logger = logging.getLogger(__name__)

# Global degraded flag visible to external monitors (e.g., n8n)
DEGRADED = False

class CircuitBreaker:
    """Circuit breaker that retries up to max_failures with exponential backoff.
    After max_failures consecutive failures, sets DEGRADED flag and propagates the exception.
    """
    def __init__(self, max_failures: int = 5, base_delay: float = 1.0):
        self.max_failures = max_failures
        self.base_delay = base_delay
        self._failure_count = 0

    def call(self, func, *args, **kwargs):
        """Execute func with circuit breaker logic."""
        for attempt in range(1, self.max_failures + 1):
            try:
                result = func(*args, **kwargs)
                # Success: reset failure count and return
                self._failure_count = 0
                return result
            except Exception as e:
                if attempt == self.max_failures:
                    # Max failures reached
                    self._failure_count = self.max_failures
                    global DEGRADED
                    DEGRADED = True
                    logger.error(
                        f"Circuit breaker tripped after {self._failure_count} failures; "
                        f"setting DEGRADED flag"
                    )
                    raise e  # propagate the exception
                else:
                    # Exponential backoff before retry
                    delay = self.base_delay * (2 ** (attempt - 1))
                    logger.warning(
                        f"Attempt {attempt}/{self.max_failures} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.1f}s"
                    )
                    time.sleep(delay)
        # Should not reach here
        raise RuntimeError("Unexpected state in circuit breaker")

    # Optional decorator usage
    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return self.call(func, *args, **kwargs)
        return wrapper