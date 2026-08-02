"""Rate Limiter — Trade frequency and cooldown enforcement.

Deterministic rules:
- Maximum N trades per day per user
- Minimum cooldown period between consecutive trades
- No exceptions, no overrides
"""

import time
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""
    allowed: bool
    reason: str = ""
    trades_today: int = 0
    max_daily: int = 20
    seconds_until_next: float = 0.0


class RateLimiter:
    """Enforces trade frequency limits.

    For production (multi-Lambda), replace in-memory dict with DynamoDB atomic counters.
    """

    def __init__(self, max_trades: int = 20, cooldown_seconds: int = 30):
        self.max_trades = max_trades
        self.cooldown_seconds = cooldown_seconds
        self._trade_timestamps: dict[str, list[float]] = defaultdict(list)

    def check(self, user_id: str) -> RateLimitResult:
        """Check if user is allowed to trade now.

        Args:
            user_id: Unique user identifier.

        Returns:
            RateLimitResult with approval status.
        """
        now = time.time()
        timestamps = self._trade_timestamps[user_id]

        # Clean old timestamps (older than 24h)
        day_ago = now - 86400
        timestamps = [t for t in timestamps if t > day_ago]
        self._trade_timestamps[user_id] = timestamps

        # Check 1: Daily trade count limit
        if len(timestamps) >= self.max_trades:
            return RateLimitResult(
                allowed=False,
                reason=f"Daily trade limit reached ({len(timestamps)}/{self.max_trades})",
                trades_today=len(timestamps),
                max_daily=self.max_trades,
            )

        # Check 2: Cooldown period since last trade
        if timestamps:
            last_trade = timestamps[-1]
            elapsed = now - last_trade
            if elapsed < self.cooldown_seconds:
                remaining = self.cooldown_seconds - elapsed
                return RateLimitResult(
                    allowed=False,
                    reason=f"Cooldown active: {remaining:.0f}s remaining (min {self.cooldown_seconds}s between trades)",
                    trades_today=len(timestamps),
                    max_daily=self.max_trades,
                    seconds_until_next=remaining,
                )

        return RateLimitResult(
            allowed=True,
            reason="Rate limit OK",
            trades_today=len(timestamps),
            max_daily=self.max_trades,
        )

    def record_trade(self, user_id: str):
        """Record a successful trade execution.

        Must be called AFTER a trade is confirmed to update counters.
        """
        self._trade_timestamps[user_id].append(time.time())

    def reset(self, user_id: str):
        """Reset rate limits for a user (admin/testing only)."""
        self._trade_timestamps[user_id] = []

    def get_status(self, user_id: str) -> dict:
        """Get current rate limit status for a user."""
        now = time.time()
        timestamps = self._trade_timestamps.get(user_id, [])
        timestamps = [t for t in timestamps if t > now - 86400]

        last_trade_ago = (now - timestamps[-1]) if timestamps else None

        return {
            "trades_today": len(timestamps),
            "max_daily": self.max_trades,
            "remaining": self.max_trades - len(timestamps),
            "cooldown_seconds": self.cooldown_seconds,
            "last_trade_seconds_ago": last_trade_ago,
            "can_trade_now": self.check(user_id).allowed,
        }
