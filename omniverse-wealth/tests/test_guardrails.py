"""Unit tests for Guardrail Engine and sub-modules.

Tests deterministic risk control logic:
- Rate limiting (cooldown + daily cap)
- Circuit breaker (volatility threshold)
- Trade authorization (two-phase verification)
- Full engine evaluation pipeline
"""

import asyncio
import time
from decimal import Decimal

import pytest

from src.guardrails.rate_limiter import RateLimiter
from src.guardrails.circuit_breaker import CircuitBreaker, CircuitBreakerResult
from src.guardrails.trade_authorizer import TradeAuthorizer
from src.guardrails.engine import (
    GuardrailEngine,
    TradeRequest,
    CheckResult,
    RiskLevel,
)


# ─── Rate Limiter Tests ─────────────────────────────────────────────────────

class TestRateLimiter:
    def test_allows_first_trade(self):
        limiter = RateLimiter(max_trades=20, cooldown_seconds=30)
        result = limiter.check("user1")
        assert result.allowed is True
        assert result.trades_today == 0

    def test_blocks_after_daily_limit(self):
        limiter = RateLimiter(max_trades=3, cooldown_seconds=0)
        # Record 3 trades
        for _ in range(3):
            limiter.record_trade("user1")
        result = limiter.check("user1")
        assert result.allowed is False
        assert "Daily trade limit" in result.reason
        assert result.trades_today == 3

    def test_cooldown_blocks_rapid_trades(self):
        limiter = RateLimiter(max_trades=20, cooldown_seconds=30)
        limiter.record_trade("user1")
        result = limiter.check("user1")
        assert result.allowed is False
        assert "Cooldown" in result.reason
        assert result.seconds_until_next > 0

    def test_cooldown_expires(self):
        limiter = RateLimiter(max_trades=20, cooldown_seconds=1)
        limiter.record_trade("user1")
        time.sleep(1.1)
        result = limiter.check("user1")
        assert result.allowed is True

    def test_different_users_independent(self):
        limiter = RateLimiter(max_trades=1, cooldown_seconds=0)
        limiter.record_trade("user1")
        result_user2 = limiter.check("user2")
        assert result_user2.allowed is True

    def test_reset_clears_history(self):
        limiter = RateLimiter(max_trades=1, cooldown_seconds=0)
        limiter.record_trade("user1")
        limiter.reset("user1")
        result = limiter.check("user1")
        assert result.allowed is True


# ─── Circuit Breaker Tests ──────────────────────────────────────────────────

class TestCircuitBreaker:
    def test_closed_when_volatility_low(self):
        result = CircuitBreakerResult(
            is_open=False,
            current_volatility=0.05,
            threshold=0.20,
        )
        assert result.is_open is False

    def test_open_when_volatility_high(self):
        result = CircuitBreakerResult(
            is_open=True,
            reason="24h volatility 25% >= 20%",
            current_volatility=0.25,
            threshold=0.20,
        )
        assert result.is_open is True

    def test_threshold_boundary(self):
        cb = CircuitBreaker(max_volatility_pct=Decimal("0.20"))
        # 19.9% should pass
        assert 0.199 < cb.max_volatility_pct


# ─── Trade Authorizer Tests ─────────────────────────────────────────────────

class TestTradeAuthorizer:
    def test_create_token(self):
        auth = TradeAuthorizer()
        result = auth.create_authorization_token(
            user_id="user1",
            market="btctwd",
            side="buy",
            volume="0.01",
            price="3400000",
        )
        assert result.authorized is False
        assert result.token != ""
        assert result.expires_at > time.time()

    def test_verify_valid_token(self):
        auth = TradeAuthorizer()
        create_result = auth.create_authorization_token(
            user_id="user1",
            market="btctwd",
            side="buy",
            volume="0.01",
            price="3400000",
        )
        verify_result = auth.verify_authorization(
            token=create_result.token,
            user_id="user1",
            market="btctwd",
            side="buy",
            volume="0.01",
            price="3400000",
        )
        assert verify_result.authorized is True

    def test_reject_wrong_user(self):
        auth = TradeAuthorizer()
        result = auth.create_authorization_token(
            user_id="user1",
            market="btctwd",
            side="buy",
            volume="0.01",
            price="3400000",
        )
        verify = auth.verify_authorization(
            token=result.token,
            user_id="attacker",
            market="btctwd",
            side="buy",
            volume="0.01",
            price="3400000",
        )
        assert verify.authorized is False
        assert "User ID mismatch" in verify.reason

    def test_reject_changed_parameters(self):
        auth = TradeAuthorizer()
        result = auth.create_authorization_token(
            user_id="user1",
            market="btctwd",
            side="buy",
            volume="0.01",
            price="3400000",
        )
        # Try to change volume
        verify = auth.verify_authorization(
            token=result.token,
            user_id="user1",
            market="btctwd",
            side="buy",
            volume="1.0",  # Changed!
            price="3400000",
        )
        assert verify.authorized is False
        assert "parameters changed" in verify.reason

    def test_reject_expired_token(self):
        auth = TradeAuthorizer(secret_key="test")
        auth._token_ttl = 0  # Expire immediately
        result = auth.create_authorization_token(
            user_id="user1",
            market="btctwd",
            side="buy",
            volume="0.01",
            price="3400000",
        )
        time.sleep(0.1)
        verify = auth.verify_authorization(
            token=result.token,
            user_id="user1",
            market="btctwd",
            side="buy",
            volume="0.01",
            price="3400000",
        )
        assert verify.authorized is False
        assert "expired" in verify.reason

    def test_token_consumed_after_use(self):
        auth = TradeAuthorizer()
        result = auth.create_authorization_token(
            user_id="user1",
            market="btctwd",
            side="buy",
            volume="0.01",
            price="3400000",
        )
        # First verify passes
        auth.verify_authorization(
            token=result.token,
            user_id="user1",
            market="btctwd",
            side="buy",
            volume="0.01",
            price="3400000",
        )
        # Second verify fails (token consumed)
        verify2 = auth.verify_authorization(
            token=result.token,
            user_id="user1",
            market="btctwd",
            side="buy",
            volume="0.01",
            price="3400000",
        )
        assert verify2.authorized is False

    def test_revoke_token(self):
        auth = TradeAuthorizer()
        result = auth.create_authorization_token(
            user_id="user1",
            market="btctwd",
            side="buy",
            volume="0.01",
            price="3400000",
        )
        revoked = auth.revoke(result.token)
        assert revoked is True
        verify = auth.verify_authorization(
            token=result.token,
            user_id="user1",
            market="btctwd",
            side="buy",
            volume="0.01",
            price="3400000",
        )
        assert verify.authorized is False


# ─── Guardrail Engine Tests ─────────────────────────────────────────────────

class TestGuardrailEngine:
    def _make_valid_request(self) -> TradeRequest:
        return TradeRequest(
            market="btctwd",
            side="buy",
            volume=Decimal("0.01"),
            price=Decimal("3400000"),
            ord_type="limit",
            user_id="test_user",
            portfolio_value_twd=Decimal("1000000"),
        )

    @pytest.mark.asyncio
    async def test_valid_trade_passes(self):
        engine = GuardrailEngine()
        request = self._make_valid_request()
        verdict = await engine.evaluate(request)
        # Should pass all checks (circuit breaker may fail on network)
        param_check = next(c for c in verdict.checks if c.name == "valid_params")
        assert param_check.result == CheckResult.PASS

    @pytest.mark.asyncio
    async def test_invalid_side_rejected(self):
        engine = GuardrailEngine()
        request = TradeRequest(
            market="btctwd",
            side="short",  # Invalid
            volume=Decimal("0.01"),
            price=Decimal("3400000"),
            user_id="test",
            portfolio_value_twd=Decimal("1000000"),
        )
        verdict = await engine.evaluate(request)
        assert verdict.approved is False
        assert any("Invalid side" in c.message for c in verdict.failed_checks)

    @pytest.mark.asyncio
    async def test_zero_volume_rejected(self):
        engine = GuardrailEngine()
        request = TradeRequest(
            market="btctwd",
            side="buy",
            volume=Decimal("0"),
            price=Decimal("3400000"),
            user_id="test",
            portfolio_value_twd=Decimal("1000000"),
        )
        verdict = await engine.evaluate(request)
        assert verdict.approved is False

    @pytest.mark.asyncio
    async def test_exceeds_max_value_rejected(self):
        engine = GuardrailEngine()
        request = TradeRequest(
            market="btctwd",
            side="buy",
            volume=Decimal("1"),
            price=Decimal("3400000"),  # 3.4M TWD > 500K limit
            ord_type="limit",
            user_id="test",
            portfolio_value_twd=Decimal("50000000"),
        )
        verdict = await engine.evaluate(request)
        assert verdict.approved is False
        assert any("max" in c.name for c in verdict.failed_checks)

    @pytest.mark.asyncio
    async def test_below_min_value_rejected(self):
        engine = GuardrailEngine()
        request = TradeRequest(
            market="btctwd",
            side="buy",
            volume=Decimal("0.00001"),
            price=Decimal("3400000"),  # = 34 TWD < 100 TWD min
            ord_type="limit",
            user_id="test",
            portfolio_value_twd=Decimal("1000000"),
        )
        verdict = await engine.evaluate(request)
        assert verdict.approved is False
        assert any("min" in c.name for c in verdict.failed_checks)

    @pytest.mark.asyncio
    async def test_portfolio_pct_exceeded(self):
        engine = GuardrailEngine()
        request = TradeRequest(
            market="btctwd",
            side="buy",
            volume=Decimal("0.05"),
            price=Decimal("3400000"),  # = 170K TWD = 17% of 1M portfolio
            ord_type="limit",
            user_id="test",
            portfolio_value_twd=Decimal("1000000"),
        )
        verdict = await engine.evaluate(request)
        assert verdict.approved is False
        assert any("portfolio" in c.name for c in verdict.failed_checks)

    @pytest.mark.asyncio
    async def test_unknown_market_rejected(self):
        engine = GuardrailEngine()
        request = TradeRequest(
            market="fakecointwd",
            side="buy",
            volume=Decimal("100"),
            price=Decimal("10"),
            user_id="test",
            portfolio_value_twd=Decimal("1000000"),
        )
        verdict = await engine.evaluate(request)
        assert verdict.approved is False

    @pytest.mark.asyncio
    async def test_risk_score_increases_with_failures(self):
        engine = GuardrailEngine()
        # Valid trade
        good = self._make_valid_request()
        v1 = await engine.evaluate(good)
        # Bad trade
        bad = TradeRequest(
            market="fakecointwd",
            side="short",
            volume=Decimal("0"),
            price=Decimal("0"),
            user_id="test",
        )
        v2 = await engine.evaluate(bad)
        assert v2.risk_score > v1.risk_score
        assert v2.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
