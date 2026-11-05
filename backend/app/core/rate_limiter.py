"""In-memory rate limiter for authentication endpoints (Phase 4).

Protects sensitive routes (specifically POST /api/auth/login) against
brute-force password guessing attacks without requiring external dependencies like Redis.

Features:
- Sliding-window tracking of failed login attempts per client IP.
- Automatic lockout (HTTP 429) after MAX_FAILED_ATTEMPTS within WINDOW_SECONDS.
- Immediate reset on successful authentication.
- Thread-safe storage with automatic stale entry cleanup.
"""

from collections import defaultdict
from datetime import datetime, timezone
import logging
import threading
from typing import Dict, List, Tuple

logger = logging.getLogger("app.core.rate_limiter")


class LoginRateLimiter:
    """Thread-safe sliding-window rate limiter for login attempts."""

    def __init__(
        self,
        max_attempts: int = 5,
        window_seconds: int = 60,
    ):
        """Initialize the rate limiter.

        Args:
            max_attempts: Number of failed attempts permitted within the window (default 5).
            window_seconds: Duration of the lockout window in seconds (default 60).
        """
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        # Stores list of failure Unix timestamps per IP: { "127.0.0.1": [1698000000, 1698000010, ...] }
        self._failures: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def _now(self) -> float:
        return datetime.now(timezone.utc).timestamp()

    def _clean_stale(self, client_ip: str, now: float) -> None:
        """Remove timestamps older than the sliding window."""
        cutoff = now - self.window_seconds
        self._failures[client_ip] = [ts for ts in self._failures[client_ip] if ts > cutoff]
        if not self._failures[client_ip]:
            del self._failures[client_ip]

    def is_blocked(self, client_ip: str) -> Tuple[bool, int]:
        """Check if an IP address is currently blocked due to repeated failures.

        Args:
            client_ip: The IP address of the incoming request.

        Returns:
            Tuple of (is_blocked: bool, seconds_remaining: int).
        """
        now = self._now()
        with self._lock:
            self._clean_stale(client_ip, now)
            attempts = self._failures.get(client_ip, [])
            if len(attempts) >= self.max_attempts:
                oldest_in_window = attempts[0]
                seconds_remaining = max(1, int(self.window_seconds - (now - oldest_in_window)))
                return True, seconds_remaining
            return False, 0

    def record_failure(self, client_ip: str) -> int:
        """Record a failed login attempt for an IP.

        Args:
            client_ip: The IP address that made the failed attempt.

        Returns:
            Current count of recent failures in the active window.
        """
        now = self._now()
        with self._lock:
            self._clean_stale(client_ip, now)
            self._failures[client_ip].append(now)
            count = len(self._failures[client_ip])
            logger.warning(
                f"[RateLimiter] Recorded failed login from IP '{client_ip}'. "
                f"Count: {count}/{self.max_attempts}"
            )
            return count

    def reset(self, client_ip: str) -> None:
        """Reset the failure counter on successful login.

        Args:
            client_ip: The IP address to clear.
        """
        with self._lock:
            if client_ip in self._failures:
                del self._failures[client_ip]
                logger.debug(f"[RateLimiter] Cleared failure counter for IP '{client_ip}'.")


# Singleton instance shared across requests
login_rate_limiter = LoginRateLimiter(max_attempts=5, window_seconds=60)

