"""Guardrail Engine — Deterministic Risk Control System.

This is the core deterministic safety layer that CANNOT be overridden
by any LLM output. All trade requests must pass through this engine
before execution.

Design principles:
- Pure logic, no LLM dependency
- Fail-closed: any uncertainty = reject
- Composable checks: each rule is independent
- Auditable: every decision is logged with reasoning
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any

from src.guardrails.rate_limiter import RateLimiter, RateLimitResult
from src.guardrails.circuit_breaker import CircuitBreaker, CircuitBreakerResult
from src.guardrails.trade_authorizer import TradeAuthorizer, AuthorizationResult


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CheckResult(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"


@dataclass
class RiskCheck:
    """Result of a single risk check."""
    name: str
    result: CheckResult
    message: str
    data: dict = field(default_factory=dict)


@dataclass
class GuardrailVerdict:
    """Final verdict from the Guardrail Engine."""
    approved: bool
    risk_level: RiskLevel
    risk_score: float  # 0.0 (safe) to 1.0 (max risk)
    checks: list[RiskCheck]
    reason: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def passed_checks(self) -> list[RiskCheck]:
        return [c for c in self.checks if c.result == CheckResult.PASS]

    @property
    def failed_checks(self) -> list[RiskCheck]:
        return [c for c in self.checks if c.result == CheckResult.FAIL]

    @property
    def warnings(self) -> list[RiskCheck]:
        return [c for c in self.checks if c.result == CheckResult.WARN]


@dataclass
class TradeRequest:
    """Structured trade request for guardrail evaluation."""
    market: str
    side: str  # "buy" or "sell"
    volume: Decimal
    price: Decimal | None = None
    ord_type: str = "limit"
    user_id: str = "default"
    portfolio_value_twd: Decimal = Decimal("0")


# ─── Default Risk Parameters ────────────────────────────────────────────────

DEFAULT_RISK_PARAMS = {
    "max_single_order_pct": Decimal("0.10"),       # 10% of portfolio
    "max_single_order_twd": Decimal("500000"),     # 500K TWD absolute cap
    "min_order_value_twd": Decimal("100"),         # Minimum 100 TWD
    "max_daily_trades": 20,
    "cooldown_seconds": 30,
    "max_daily_volatility_pct": Decimal("0.20"),   # 20% circuit breaker
    "max_hourly_loss_pct": Decimal("0.05"),        # 5% hourly loss halt
}


class GuardrailEngine:
    """Deterministic risk control engine.

    All checks are pure logic — no LLM, no probabilistic decisions.
    A single failed check = trade rejected.

    Usage:
        engine = GuardrailEngine()
        verdict = await engine.evaluate(trade_request)
        if not verdict.approved:
            # Block the trade
            raise TradeRejected(verdict.reason)
    """

    def __init__(self, params: dict | None = None):
        self.params = {**DEFAULT_RISK_PARAMS, **(params or {})}
        self.rate_limiter = RateLimiter(
            max_trades=self.params["max_daily_trades"],
            cooldown_seconds=self.params["cooldown_seconds"],
        )
        self.circuit_breaker = CircuitBreaker(
            max_volatility_pct=self.params["max_daily_volatility_pct"],
            max_hourly_loss_pct=self.params["max_hourly_loss_pct"],
        )
        self.authorizer = TradeAuthorizer()

    async def evaluate(self, request: TradeRequest) -> GuardrailVerdict:
        """Run all guardrail checks on a trade request.

        Args:
            request: Structured trade request to evaluate.

        Returns:
            GuardrailVerdict with approval status and detailed check results.
        """
        checks: list[RiskCheck] = []

        # Check 1: Valid parameters
        checks.append(self._check_valid_params(request))

        # Check 2: Minimum order value
        checks.append(self._check_min_value(request))

        # Check 3: Maximum single order value
        checks.append(self._check_max_value(request))

        # Check 4: Portfolio percentage limit
        checks.append(self._check_portfolio_pct(request))

        # Check 5: Rate limiting (cooldown + daily cap)
        rate_result = self.rate_limiter.check(request.user_id)
        checks.append(self._rate_limit_to_check(rate_result))

        # Check 6: Circuit breaker (volatility)
        cb_result = await self.circuit_breaker.check(request.market)
        checks.append(self._circuit_breaker_to_check(cb_result))

        # Compute verdict
        failed = [c for c in checks if c.result == CheckResult.FAIL]
        warnings = [c for c in checks if c.result == CheckResult.WARN]

        risk_score = self._compute_risk_score(checks)
        risk_level = self._score_to_level(risk_score)

        approved = len(failed) == 0

        if approved:
            reason = f"All {len(checks)} checks passed."
            if warnings:
                reason += f" ({len(warnings)} warnings)"
        else:
            reason = f"Rejected: {'; '.join(c.message for c in failed)}"

        return GuardrailVerdict(
            approved=approved,
            risk_level=risk_level,
            risk_score=risk_score,
            checks=checks,
            reason=reason,
        )

    # ─── Individual Checks ──────────────────────────────────────────────────

    def _check_valid_params(self, request: TradeRequest) -> RiskCheck:
        """Validate basic trade parameters."""
        issues = []

        if request.side not in ("buy", "sell"):
            issues.append(f"Invalid side: {request.side}")

        if request.volume <= 0:
            issues.append(f"Volume must be positive: {request.volume}")

        if request.ord_type not in ("limit", "market", "stop_limit", "stop_market"):
            issues.append(f"Invalid order type: {request.ord_type}")

        if request.ord_type == "limit" and (request.price is None or request.price <= 0):
            issues.append("Limit order requires a positive price")

        valid_markets = ["btctwd", "ethtwd", "soltwd", "dogetwd", "usdttwd", "usdctwd"]
        if request.market not in valid_markets:
            issues.append(f"Unknown market: {request.market}")

        if issues:
            return RiskCheck(
                name="valid_params",
                result=CheckResult.FAIL,
                message="; ".join(issues),
            )

        return RiskCheck(
            name="valid_params",
            result=CheckResult.PASS,
            message="All parameters valid",
        )

    def _check_min_value(self, request: TradeRequest) -> RiskCheck:
        """Check minimum order value threshold."""
        order_value = self._estimate_value_twd(request)
        min_val = self.params["min_order_value_twd"]

        if order_value < min_val:
            return RiskCheck(
                name="min_order_value",
                result=CheckResult.FAIL,
                message=f"Order value {order_value} TWD < minimum {min_val} TWD",
                data={"order_value": str(order_value), "minimum": str(min_val)},
            )

        return RiskCheck(
            name="min_order_value",
            result=CheckResult.PASS,
            message=f"Order value {order_value} TWD >= {min_val} TWD",
            data={"order_value": str(order_value)},
        )

    def _check_max_value(self, request: TradeRequest) -> RiskCheck:
        """Check maximum single order value cap."""
        order_value = self._estimate_value_twd(request)
        max_val = self.params["max_single_order_twd"]

        if order_value > max_val:
            return RiskCheck(
                name="max_order_value",
                result=CheckResult.FAIL,
                message=f"Order value {order_value} TWD > maximum {max_val} TWD",
                data={"order_value": str(order_value), "maximum": str(max_val)},
            )

        return RiskCheck(
            name="max_order_value",
            result=CheckResult.PASS,
            message=f"Order value {order_value} TWD <= {max_val} TWD",
            data={"order_value": str(order_value)},
        )

    def _check_portfolio_pct(self, request: TradeRequest) -> RiskCheck:
        """Check if order exceeds portfolio percentage limit."""
        if request.portfolio_value_twd <= 0:
            return RiskCheck(
                name="portfolio_pct",
                result=CheckResult.WARN,
                message="Portfolio value unknown, skipping percentage check",
            )

        order_value = self._estimate_value_twd(request)
        pct = order_value / request.portfolio_value_twd
        max_pct = self.params["max_single_order_pct"]

        if pct > max_pct:
            return RiskCheck(
                name="portfolio_pct",
                result=CheckResult.FAIL,
                message=f"Order is {pct:.1%} of portfolio, exceeds {max_pct:.0%} limit",
                data={"pct": str(pct), "max_pct": str(max_pct)},
            )

        return RiskCheck(
            name="portfolio_pct",
            result=CheckResult.PASS,
            message=f"Order is {pct:.1%} of portfolio (<= {max_pct:.0%})",
            data={"pct": str(pct)},
        )

    # ─── Helper Methods ─────────────────────────────────────────────────────

    def _estimate_value_twd(self, request: TradeRequest) -> Decimal:
        """Estimate order value in TWD."""
        if request.price and request.price > 0:
            return request.volume * request.price
        return Decimal("0")

    def _rate_limit_to_check(self, result: RateLimitResult) -> RiskCheck:
        """Convert RateLimiter result to RiskCheck."""
        if result.allowed:
            return RiskCheck(
                name="rate_limit",
                result=CheckResult.PASS,
                message=f"Rate limit OK ({result.trades_today}/{result.max_daily})",
                data={"trades_today": result.trades_today},
            )
        return RiskCheck(
            name="rate_limit",
            result=CheckResult.FAIL,
            message=result.reason,
            data={"trades_today": result.trades_today},
        )

    def _circuit_breaker_to_check(self, result: CircuitBreakerResult) -> RiskCheck:
        """Convert CircuitBreaker result to RiskCheck."""
        if result.is_open:
            return RiskCheck(
                name="circuit_breaker",
                result=CheckResult.FAIL,
                message=result.reason,
                data={"volatility": str(result.current_volatility)},
            )
        return RiskCheck(
            name="circuit_breaker",
            result=CheckResult.PASS,
            message=f"Circuit breaker closed (volatility: {result.current_volatility:.2%})",
            data={"volatility": str(result.current_volatility)},
        )

    def _compute_risk_score(self, checks: list[RiskCheck]) -> float:
        """Compute aggregate risk score from individual checks."""
        if not checks:
            return 0.0

        weights = {
            "valid_params": 0.3,
            "min_order_value": 0.1,
            "max_order_value": 0.2,
            "portfolio_pct": 0.15,
            "rate_limit": 0.1,
            "circuit_breaker": 0.15,
        }

        score = 0.0
        for check in checks:
            weight = weights.get(check.name, 0.1)
            if check.result == CheckResult.FAIL:
                score += weight
            elif check.result == CheckResult.WARN:
                score += weight * 0.3

        return min(score, 1.0)

    def _score_to_level(self, score: float) -> RiskLevel:
        """Convert risk score to risk level."""
        if score < 0.1:
            return RiskLevel.LOW
        elif score < 0.3:
            return RiskLevel.MEDIUM
        elif score < 0.6:
            return RiskLevel.HIGH
        return RiskLevel.CRITICAL
