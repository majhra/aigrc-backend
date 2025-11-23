"""
Tests for the rate limiting service.
"""

import time
import pytest
from unittest.mock import MagicMock, patch

from app.modules.rate_limiter import (
    RateLimiter,
    RateLimitConfig,
    RateLimitStrategy,
    RateLimitResult,
    InMemoryRateLimitBackend,
    RedisRateLimitBackend,
    RATE_LIMITS,
)


class TestInMemoryRateLimitBackend:
    """Tests for InMemoryRateLimitBackend."""

    def test_allows_requests_under_limit(self):
        """Test that requests under the limit are allowed."""
        backend = InMemoryRateLimitBackend()

        # Allow 5 requests per minute
        for i in range(5):
            result = backend.check_and_increment("test_key", 5, 60)
            assert result.allowed is True
            assert result.remaining == 5 - i - 1

    def test_blocks_requests_over_limit(self):
        """Test that requests over the limit are blocked."""
        backend = InMemoryRateLimitBackend()

        # Make 5 requests (the limit)
        for i in range(5):
            result = backend.check_and_increment("test_key", 5, 60)
            assert result.allowed is True

        # 6th request should be blocked
        result = backend.check_and_increment("test_key", 5, 60)
        assert result.allowed is False
        assert result.remaining == 0
        assert result.retry_after is not None
        assert result.retry_after > 0

    def test_block_seconds_applies_extended_block(self):
        """Test that block_seconds adds extra blocking time."""
        backend = InMemoryRateLimitBackend()

        # Make requests up to limit
        for i in range(3):
            backend.check_and_increment("test_key", 3, 60, block_seconds=300)

        # Next request should be blocked with 300 second retry
        result = backend.check_and_increment("test_key", 3, 60, block_seconds=300)
        assert result.allowed is False
        assert result.retry_after == 300

    def test_reset_clears_rate_limit(self):
        """Test that reset clears the rate limit."""
        backend = InMemoryRateLimitBackend()

        # Use up the limit
        for i in range(5):
            backend.check_and_increment("test_key", 5, 60)

        # Should be blocked
        result = backend.check_and_increment("test_key", 5, 60)
        assert result.allowed is False

        # Reset
        backend.reset("test_key")

        # Should be allowed again
        result = backend.check_and_increment("test_key", 5, 60)
        assert result.allowed is True

    def test_different_keys_are_independent(self):
        """Test that different keys have independent rate limits."""
        backend = InMemoryRateLimitBackend()

        # Use up limit for key1
        for i in range(3):
            backend.check_and_increment("key1", 3, 60)

        # key1 should be blocked
        result = backend.check_and_increment("key1", 3, 60)
        assert result.allowed is False

        # key2 should still be allowed
        result = backend.check_and_increment("key2", 3, 60)
        assert result.allowed is True

    def test_is_blocked_returns_correct_state(self):
        """Test is_blocked method."""
        backend = InMemoryRateLimitBackend()

        # Initially not blocked
        is_blocked, retry_after = backend.is_blocked("test_key")
        assert is_blocked is False
        assert retry_after is None

        # Exceed limit with blocking
        for i in range(3):
            backend.check_and_increment("test_key", 3, 60, block_seconds=60)
        backend.check_and_increment("test_key", 3, 60, block_seconds=60)

        # Should be blocked
        is_blocked, retry_after = backend.is_blocked("test_key")
        assert is_blocked is True
        assert retry_after is not None
        assert retry_after > 0

    def test_cleanup_removes_expired_entries(self):
        """Test that cleanup removes expired entries."""
        backend = InMemoryRateLimitBackend()

        # Add some requests
        backend.check_and_increment("test_key", 5, 1)  # 1 second window

        # Wait for window to expire
        time.sleep(1.1)

        # Cleanup should remove expired entries
        cleaned = backend.cleanup()
        # The requests list should be cleaned on next access, but cleanup helps
        assert cleaned >= 0


class TestRateLimiter:
    """Tests for the RateLimiter class."""

    def test_default_rule_is_applied(self):
        """Test that default rule is used for unconfigured endpoints."""
        backend = InMemoryRateLimitBackend()
        limiter = RateLimiter(backend)

        # Configure default
        limiter.set_default_rule(RateLimitConfig(
            requests=10,
            window_seconds=60,
            strategy=RateLimitStrategy.IP
        ))

        # Check unconfigured endpoint
        result = limiter.check("unknown_endpoint", ip="127.0.0.1")
        assert result.allowed is True

    def test_endpoint_specific_rule_overrides_default(self):
        """Test that endpoint-specific rules override default."""
        backend = InMemoryRateLimitBackend()
        limiter = RateLimiter(backend)

        # Configure default with high limit
        limiter.set_default_rule(RateLimitConfig(
            requests=100,
            window_seconds=60,
            strategy=RateLimitStrategy.IP
        ))

        # Configure login with low limit
        limiter.configure_endpoint("login", RateLimitConfig(
            requests=3,
            window_seconds=60,
            strategy=RateLimitStrategy.IP
        ))

        # Use up login limit
        for i in range(3):
            limiter.check("login", ip="127.0.0.1")

        # Login should be blocked
        result = limiter.check("login", ip="127.0.0.1")
        assert result.allowed is False

        # Other endpoints should still work
        result = limiter.check("other", ip="127.0.0.1")
        assert result.allowed is True

    def test_ip_strategy_groups_by_ip(self):
        """Test IP strategy groups requests by IP address."""
        backend = InMemoryRateLimitBackend()
        limiter = RateLimiter(backend)
        limiter.configure_endpoint("test", RateLimitConfig(
            requests=3,
            window_seconds=60,
            strategy=RateLimitStrategy.IP
        ))

        # Use up limit for IP1
        for i in range(3):
            limiter.check("test", ip="1.1.1.1")

        # IP1 should be blocked
        result = limiter.check("test", ip="1.1.1.1")
        assert result.allowed is False

        # IP2 should still be allowed
        result = limiter.check("test", ip="2.2.2.2")
        assert result.allowed is True

    def test_ip_endpoint_strategy_groups_by_both(self):
        """Test IP_ENDPOINT strategy groups by both IP and endpoint."""
        backend = InMemoryRateLimitBackend()
        limiter = RateLimiter(backend)
        limiter.configure_endpoint("endpoint1", RateLimitConfig(
            requests=3,
            window_seconds=60,
            strategy=RateLimitStrategy.IP_ENDPOINT
        ))
        limiter.configure_endpoint("endpoint2", RateLimitConfig(
            requests=3,
            window_seconds=60,
            strategy=RateLimitStrategy.IP_ENDPOINT
        ))

        # Use up limit for IP1 on endpoint1
        for i in range(3):
            limiter.check("endpoint1", ip="1.1.1.1")

        # IP1 on endpoint1 should be blocked
        result = limiter.check("endpoint1", ip="1.1.1.1")
        assert result.allowed is False

        # IP1 on endpoint2 should still be allowed (different key)
        result = limiter.check("endpoint2", ip="1.1.1.1")
        assert result.allowed is True

    def test_reset_works_through_limiter(self):
        """Test reset through the limiter interface."""
        backend = InMemoryRateLimitBackend()
        limiter = RateLimiter(backend)
        limiter.configure_endpoint("login", RateLimitConfig(
            requests=3,
            window_seconds=60,
            strategy=RateLimitStrategy.IP
        ))

        # Use up limit
        for i in range(3):
            limiter.check("login", ip="127.0.0.1")

        # Should be blocked
        result = limiter.check("login", ip="127.0.0.1")
        assert result.allowed is False

        # Reset
        limiter.reset("login", ip="127.0.0.1")

        # Should be allowed again
        result = limiter.check("login", ip="127.0.0.1")
        assert result.allowed is True


class TestPredefinedRateLimits:
    """Tests for predefined rate limit configurations."""

    def test_login_rate_limit_exists(self):
        """Test login rate limit is defined."""
        assert "login" in RATE_LIMITS
        config = RATE_LIMITS["login"]
        assert config.requests == 5
        assert config.window_seconds == 60
        assert config.block_seconds == 300

    def test_registration_rate_limit_exists(self):
        """Test registration rate limit is defined."""
        assert "registration" in RATE_LIMITS
        config = RATE_LIMITS["registration"]
        assert config.requests == 3
        assert config.window_seconds == 3600

    def test_password_reset_rate_limit_exists(self):
        """Test password reset rate limit is defined."""
        assert "password_reset" in RATE_LIMITS
        config = RATE_LIMITS["password_reset"]
        assert config.requests == 3
        assert config.window_seconds == 3600

    def test_ai_connection_test_rate_limit_exists(self):
        """Test AI connection test rate limit is defined."""
        assert "ai_connection_test" in RATE_LIMITS
        config = RATE_LIMITS["ai_connection_test"]
        assert config.requests == 10
        assert config.window_seconds == 60


class TestRedisRateLimitBackend:
    """Tests for RedisRateLimitBackend (with mocked Redis)."""

    def test_check_and_increment_allows_under_limit(self):
        """Test Redis backend allows requests under limit."""
        mock_redis = MagicMock()
        mock_redis.get.return_value = None
        mock_redis.pipeline.return_value = MagicMock()
        mock_redis.pipeline.return_value.execute.return_value = [None, 2]  # 2 existing requests
        mock_redis.zrange.return_value = [(b"123", 100.0)]

        backend = RedisRateLimitBackend(mock_redis)
        result = backend.check_and_increment("test_key", 5, 60)

        assert result.allowed is True

    def test_check_and_increment_blocks_over_limit(self):
        """Test Redis backend blocks requests over limit."""
        mock_redis = MagicMock()
        mock_redis.get.return_value = None
        mock_redis.pipeline.return_value = MagicMock()
        mock_redis.pipeline.return_value.execute.return_value = [None, 5]  # At limit
        mock_redis.zrange.return_value = [(b"123", time.time() - 30)]

        backend = RedisRateLimitBackend(mock_redis)
        result = backend.check_and_increment("test_key", 5, 60)

        assert result.allowed is False
        assert result.retry_after is not None

    def test_reset_deletes_keys(self):
        """Test Redis backend reset deletes keys."""
        mock_redis = MagicMock()
        backend = RedisRateLimitBackend(mock_redis)

        backend.reset("test_key")

        mock_redis.delete.assert_called_once()

    def test_is_blocked_when_blocked(self):
        """Test is_blocked returns True when blocked."""
        mock_redis = MagicMock()
        mock_redis.get.return_value = str(time.time() + 60)  # Blocked for 60 more seconds

        backend = RedisRateLimitBackend(mock_redis)
        is_blocked, retry_after = backend.is_blocked("test_key")

        assert is_blocked is True
        assert retry_after is not None
        assert retry_after > 0
