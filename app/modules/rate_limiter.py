"""
Rate limiting service for protecting API endpoints.

Provides configurable rate limiting with support for:
- In-memory storage (single instance)
- Redis storage (distributed, multiple instances)

Supports different rate limit strategies:
- Per IP address
- Per user (email)
- Per endpoint
- Combined (IP + endpoint)
"""

import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from threading import Lock
from typing import Optional, Dict, Tuple, TYPE_CHECKING, Any

if TYPE_CHECKING:
    import redis as redis_module


class RateLimitStrategy(str, Enum):
    """Rate limiting strategies."""
    IP = "ip"
    USER = "user"
    ENDPOINT = "endpoint"
    IP_ENDPOINT = "ip_endpoint"


@dataclass
class RateLimitConfig:
    """Configuration for a rate limit rule."""
    requests: int  # Number of requests allowed
    window_seconds: int  # Time window in seconds
    block_seconds: int = 0  # How long to block after limit exceeded (0 = just reject)
    strategy: RateLimitStrategy = RateLimitStrategy.IP


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""
    allowed: bool
    remaining: int
    reset_time: float
    retry_after: Optional[int] = None


class RateLimitBackend(ABC):
    """Abstract backend for rate limit storage."""

    @abstractmethod
    def check_and_increment(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
        block_seconds: int = 0
    ) -> RateLimitResult:
        """
        Check if request is allowed and increment counter.

        Args:
            key: Unique identifier for the rate limit (e.g., IP:endpoint)
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
            block_seconds: Additional block time after limit exceeded

        Returns:
            RateLimitResult with allowed status and metadata
        """
        pass

    @abstractmethod
    def reset(self, key: str) -> None:
        """Reset the rate limit for a key."""
        pass

    @abstractmethod
    def is_blocked(self, key: str) -> Tuple[bool, Optional[int]]:
        """Check if a key is currently blocked. Returns (is_blocked, retry_after)."""
        pass


class InMemoryRateLimitBackend(RateLimitBackend):
    """
    In-memory rate limit storage using sliding window algorithm.

    Suitable for single-instance deployments.
    Thread-safe implementation.
    """

    def __init__(self):
        self._requests: Dict[str, list] = defaultdict(list)
        self._blocks: Dict[str, float] = {}
        self._lock = Lock()

    def check_and_increment(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
        block_seconds: int = 0
    ) -> RateLimitResult:
        current_time = time.time()
        window_start = current_time - window_seconds

        with self._lock:
            # Check if blocked
            if key in self._blocks:
                block_until = self._blocks[key]
                if current_time < block_until:
                    retry_after = int(block_until - current_time) + 1
                    return RateLimitResult(
                        allowed=False,
                        remaining=0,
                        reset_time=block_until,
                        retry_after=retry_after
                    )
                else:
                    # Block expired, remove it
                    del self._blocks[key]

            # Clean old requests outside the window
            self._requests[key] = [
                ts for ts in self._requests[key]
                if ts > window_start
            ]

            request_count = len(self._requests[key])

            if request_count >= max_requests:
                # Rate limit exceeded
                if block_seconds > 0:
                    self._blocks[key] = current_time + block_seconds
                    retry_after = block_seconds
                else:
                    # Calculate when the oldest request will expire
                    oldest = min(self._requests[key]) if self._requests[key] else current_time
                    retry_after = int(oldest + window_seconds - current_time) + 1

                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_time=current_time + retry_after,
                    retry_after=retry_after
                )

            # Allow request
            self._requests[key].append(current_time)
            remaining = max_requests - len(self._requests[key])

            # Calculate reset time (when oldest request expires)
            if self._requests[key]:
                oldest = min(self._requests[key])
                reset_time = oldest + window_seconds
            else:
                reset_time = current_time + window_seconds

            return RateLimitResult(
                allowed=True,
                remaining=remaining,
                reset_time=reset_time
            )

    def reset(self, key: str) -> None:
        with self._lock:
            if key in self._requests:
                del self._requests[key]
            if key in self._blocks:
                del self._blocks[key]

    def is_blocked(self, key: str) -> Tuple[bool, Optional[int]]:
        current_time = time.time()
        with self._lock:
            if key in self._blocks:
                block_until = self._blocks[key]
                if current_time < block_until:
                    return True, int(block_until - current_time) + 1
                else:
                    del self._blocks[key]
        return False, None

    def cleanup(self) -> int:
        """Remove expired entries. Returns number of entries cleaned."""
        current_time = time.time()
        cleaned = 0

        with self._lock:
            # Clean expired blocks
            expired_blocks = [
                k for k, v in self._blocks.items()
                if current_time >= v
            ]
            for key in expired_blocks:
                del self._blocks[key]
                cleaned += 1

            # Clean empty request lists
            empty_keys = [
                k for k, v in self._requests.items()
                if not v
            ]
            for key in empty_keys:
                del self._requests[key]
                cleaned += 1

        return cleaned


class RedisRateLimitBackend(RateLimitBackend):
    """
    Redis-based rate limit storage using sliding window algorithm.

    Suitable for distributed deployments with multiple instances.
    Uses Redis sorted sets for efficient window management.
    """

    def __init__(self, redis_client: Any, key_prefix: str = "ratelimit"):
        """
        Initialize Redis rate limit backend.

        Args:
            redis_client: A redis.Redis client instance
            key_prefix: Prefix for all rate limit keys in Redis
        """
        self._redis = redis_client
        self._prefix = key_prefix

    def _make_key(self, key: str, suffix: str = "") -> str:
        if suffix:
            return f"{self._prefix}:{key}:{suffix}"
        return f"{self._prefix}:{key}"

    def check_and_increment(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
        block_seconds: int = 0
    ) -> RateLimitResult:
        current_time = time.time()
        window_start = current_time - window_seconds

        requests_key = self._make_key(key, "requests")
        block_key = self._make_key(key, "block")

        # Check if blocked
        block_until = self._redis.get(block_key)
        if block_until:
            block_until = float(block_until)
            if current_time < block_until:
                retry_after = int(block_until - current_time) + 1
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_time=block_until,
                    retry_after=retry_after
                )

        # Use pipeline for atomic operations
        pipe = self._redis.pipeline()

        # Remove old entries outside window
        pipe.zremrangebyscore(requests_key, 0, window_start)

        # Count current requests in window
        pipe.zcard(requests_key)

        results = pipe.execute()
        request_count = results[1]

        if request_count >= max_requests:
            # Rate limit exceeded
            if block_seconds > 0:
                self._redis.setex(block_key, block_seconds, str(current_time + block_seconds))
                retry_after = block_seconds
            else:
                # Get oldest request timestamp
                oldest_entries = self._redis.zrange(requests_key, 0, 0, withscores=True)
                if oldest_entries:
                    oldest = oldest_entries[0][1]
                    retry_after = int(oldest + window_seconds - current_time) + 1
                else:
                    retry_after = window_seconds

            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_time=current_time + retry_after,
                retry_after=retry_after
            )

        # Allow request - add to sorted set with timestamp as score
        pipe = self._redis.pipeline()
        pipe.zadd(requests_key, {f"{current_time}:{id(current_time)}": current_time})
        pipe.expire(requests_key, window_seconds + 1)  # Auto-expire
        pipe.execute()

        remaining = max_requests - request_count - 1

        # Calculate reset time
        oldest_entries = self._redis.zrange(requests_key, 0, 0, withscores=True)
        if oldest_entries:
            reset_time = oldest_entries[0][1] + window_seconds
        else:
            reset_time = current_time + window_seconds

        return RateLimitResult(
            allowed=True,
            remaining=remaining,
            reset_time=reset_time
        )

    def reset(self, key: str) -> None:
        requests_key = self._make_key(key, "requests")
        block_key = self._make_key(key, "block")
        self._redis.delete(requests_key, block_key)

    def is_blocked(self, key: str) -> Tuple[bool, Optional[int]]:
        block_key = self._make_key(key, "block")
        block_until = self._redis.get(block_key)

        if block_until:
            block_until = float(block_until)
            current_time = time.time()
            if current_time < block_until:
                return True, int(block_until - current_time) + 1

        return False, None


class RateLimiter:
    """
    Rate limiter service with configurable rules per endpoint.
    """

    def __init__(self, backend: RateLimitBackend):
        self._backend = backend
        self._rules: Dict[str, RateLimitConfig] = {}
        self._default_rule = RateLimitConfig(
            requests=100,
            window_seconds=60,
            strategy=RateLimitStrategy.IP
        )

    def configure_endpoint(self, endpoint: str, config: RateLimitConfig) -> None:
        """Configure rate limit for a specific endpoint."""
        self._rules[endpoint] = config

    def set_default_rule(self, config: RateLimitConfig) -> None:
        """Set the default rate limit rule."""
        self._default_rule = config

    def _build_key(
        self,
        strategy: RateLimitStrategy,
        endpoint: str,
        ip: Optional[str] = None,
        user: Optional[str] = None
    ) -> str:
        """Build the rate limit key based on strategy."""
        parts = []

        if strategy == RateLimitStrategy.IP:
            parts.append(f"ip:{ip or 'unknown'}")
        elif strategy == RateLimitStrategy.USER:
            parts.append(f"user:{user or 'anonymous'}")
        elif strategy == RateLimitStrategy.ENDPOINT:
            parts.append(f"endpoint:{endpoint}")
        elif strategy == RateLimitStrategy.IP_ENDPOINT:
            parts.append(f"ip:{ip or 'unknown'}")
            parts.append(f"endpoint:{endpoint}")

        return ":".join(parts)

    def check(
        self,
        endpoint: str,
        ip: Optional[str] = None,
        user: Optional[str] = None
    ) -> RateLimitResult:
        """
        Check if a request should be allowed.

        Args:
            endpoint: The API endpoint being accessed
            ip: Client IP address
            user: User identifier (email)

        Returns:
            RateLimitResult with decision and metadata
        """
        config = self._rules.get(endpoint, self._default_rule)
        key = self._build_key(config.strategy, endpoint, ip, user)

        return self._backend.check_and_increment(
            key=key,
            max_requests=config.requests,
            window_seconds=config.window_seconds,
            block_seconds=config.block_seconds
        )

    def reset(
        self,
        endpoint: str,
        ip: Optional[str] = None,
        user: Optional[str] = None
    ) -> None:
        """Reset rate limit for a specific key."""
        config = self._rules.get(endpoint, self._default_rule)
        key = self._build_key(config.strategy, endpoint, ip, user)
        self._backend.reset(key)


# Predefined rate limit configurations for common use cases
RATE_LIMITS = {
    # Very strict - for authentication endpoints
    "login": RateLimitConfig(
        requests=5,
        window_seconds=60,  # 5 attempts per minute
        block_seconds=300,  # 5 minute block after exceeded
        strategy=RateLimitStrategy.IP
    ),
    "login_strict": RateLimitConfig(
        requests=10,
        window_seconds=3600,  # 10 attempts per hour
        block_seconds=3600,  # 1 hour block
        strategy=RateLimitStrategy.IP
    ),

    # Strict - for account creation/reset
    "registration": RateLimitConfig(
        requests=3,
        window_seconds=3600,  # 3 registrations per hour per IP
        block_seconds=3600,
        strategy=RateLimitStrategy.IP
    ),
    "password_reset": RateLimitConfig(
        requests=3,
        window_seconds=3600,  # 3 reset requests per hour
        block_seconds=1800,
        strategy=RateLimitStrategy.IP
    ),
    "verification_email": RateLimitConfig(
        requests=5,
        window_seconds=3600,  # 5 verification emails per hour
        block_seconds=1800,
        strategy=RateLimitStrategy.IP
    ),

    # Moderate - for expensive operations
    "ai_connection_test": RateLimitConfig(
        requests=10,
        window_seconds=60,  # 10 tests per minute
        block_seconds=60,
        strategy=RateLimitStrategy.IP_ENDPOINT
    ),
    "test_execution": RateLimitConfig(
        requests=30,
        window_seconds=60,  # 30 executions per minute
        block_seconds=30,
        strategy=RateLimitStrategy.IP_ENDPOINT
    ),

    # Standard - for regular API operations
    "standard": RateLimitConfig(
        requests=100,
        window_seconds=60,  # 100 requests per minute
        strategy=RateLimitStrategy.IP
    ),

    # Relaxed - for read operations
    "read_heavy": RateLimitConfig(
        requests=200,
        window_seconds=60,  # 200 requests per minute
        strategy=RateLimitStrategy.IP
    ),
}
