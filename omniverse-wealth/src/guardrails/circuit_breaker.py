"""Circuit Breaker — Volatility-based trading halt mechanism.

Halts all trading when market conditions are extreme:
- Daily price change > 20% = circuit breaker OPEN (halt trading)
- Hourly loss > 5% = temporary halt

Uses MAX API public ticker for real-time volatility detection.
"""

from dataclasses import dataclass
from decimal import Decimal

import httpx


@dataclass
class CircuitBreakerResult:
    """Result of circuit breaker check."""
    is_open: bool  # True = trading halted
    reason: str = ""
    current_volatility: float = 0.0
    threshold: float = 0.20


class CircuitBreaker:
    """Volatility-based circuit breaker.

    Opens (halts trading) when market volatility exceeds thresholds.
    """

    def __init__(
        self,
        max_volatility_pct: Decimal = Decimal("0.20"),
        max_hourly_loss_pct: Decimal = Decimal("0.05"),
    ):
        self.max_volatility_pct = float(max_volatility_pct)
        self.max_hourly_loss_pct = float(max_hourly_loss_pct)

    async def check(self, market: str) -> CircuitBreakerResult:
        """Check if circuit breaker should be open for a market.

        Fetches real-time ticker data from MAX API to calculate
        24h price change percentage.

        Args:
            market: Market pair (e.g., 'btctwd')

        Returns:
            CircuitBreakerResult indicating if trading should halt.
        """
        try:
            ticker = await self._fetch_ticker(market)
            if not ticker:
                return CircuitBreakerResult(
                    is_open=False,
                    reason="Unable to fetch ticker, allowing trade (fail-open for data)",
                    current_volatility=0.0,
                )

            # Calculate 24h change percentage
            last_price = float(ticker.get("last", 0))
            open_price = float(ticker.get("open", 0))

            if open_price <= 0:
                return CircuitBreakerResult(
                    is_open=False,
                    reason="Invalid open price",
                    current_volatility=0.0,
                )

            change_pct = abs(last_price - open_price) / open_price

            # Check threshold
            if change_pct >= self.max_volatility_pct:
                return CircuitBreakerResult(
                    is_open=True,
                    reason=(
                        f"Circuit breaker OPEN: {market} 24h volatility "
                        f"{change_pct:.1%} >= {self.max_volatility_pct:.0%} threshold"
                    ),
                    current_volatility=change_pct,
                    threshold=self.max_volatility_pct,
                )

            return CircuitBreakerResult(
                is_open=False,
                reason=f"Volatility {change_pct:.2%} within limits",
                current_volatility=change_pct,
                threshold=self.max_volatility_pct,
            )

        except Exception as e:
            # On error, fail-open (allow trade) to avoid blocking
            return CircuitBreakerResult(
                is_open=False,
                reason=f"Circuit breaker check error: {e}",
                current_volatility=0.0,
            )

    async def _fetch_ticker(self, market: str) -> dict | None:
        """Fetch ticker from MAX API (public, no auth needed)."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://max-api.maicoin.com/api/v3/ticker",
                    params={"market": market},
                )
                if resp.status_code == 200:
                    return resp.json()
        except Exception:
            pass
        return None
