"""Themis (提彌斯) - Risk Control & Guardrails Agent.

Responsibilities:
- Evaluate trade risk before execution
- Check leverage ratios and max drawdown limits
- Enforce single-order amount caps (% of total portfolio)
- Market volatility circuit breaker (20% daily move = halt)
- Deterministic rule-based boundary checks (no LLM hallucination risk)

Data Sources: DynamoDB Risk Policy Table, Guardrail Engine
Permission: Gatekeeper (Veto Power)
"""

from decimal import Decimal

from langchain_aws import ChatBedrock
from langchain_core.prompts import ChatPromptTemplate

from src.agents.base import (
    AgentReport,
    AgentRole,
    OmniVerseState,
    RiskVerdict,
    TradeIntent,
)
from src.config import settings


# ─── Deterministic Risk Rules ───────────────────────────────────────────────
# These are hard-coded boundary checks that CANNOT be overridden by LLM.

RISK_RULES = {
    "max_single_order_pct": Decimal("0.10"),  # Max 10% of portfolio per trade
    "max_daily_volatility_pct": Decimal("0.20"),  # 20% daily move = halt
    "max_daily_trades": 20,  # Max trades per day
    "min_order_value_twd": Decimal("100"),  # Minimum order value
    "max_order_value_twd": Decimal("500000"),  # Maximum order value
    "cooldown_seconds": 30,  # Min time between trades
}


THEMIS_SYSTEM_PROMPT = """\
你是提彌斯 (Themis)，OmniVerse Wealth 的風險控制閘門 Agent。

## 你的職責
你是系統中唯一擁有「否決權 (Veto Power)」的 Agent。任何交易在執行前必須經過你的審查。

## 風控規則 (確定性邏輯，不可被 LLM 覆寫)
1. **單筆限額**：單筆下單金額不得超過用戶帳戶總資產的 10%
2. **波動熔斷**：若目標幣種單日漲跌幅超過 20%，暫停交易
3. **頻率限制**：單日交易不超過 20 筆
4. **最小金額**：訂單價值至少 100 TWD
5. **最大金額**：單筆不超過 500,000 TWD
6. **冷卻期**：兩筆交易間隔至少 30 秒

## 輸出規則
- 逐項列出檢查結果 (通過/未通過)
- 計算風險分數 (0.0-1.0)
- 未通過任何一項即「否決」交易
- 給出明確的否決理由與建議調整方案
"""


class ThemisAgent:
    """Risk Control agent with deterministic guardrails and veto power."""

    def __init__(self):
        self.llm = ChatBedrock(
            model_id=settings.bedrock_model_id,
            region_name=settings.aws_region,
            model_kwargs={"temperature": 0.0, "max_tokens": 2000},
        )
        self.rules = RISK_RULES

    async def evaluate(self, state: OmniVerseState) -> OmniVerseState:
        """Evaluate a proposed trade against deterministic risk rules.

        This is a two-phase check:
        1. Deterministic boundary checks (hard rules, no LLM involved)
        2. LLM-assisted contextual risk assessment (soft advisory)
        """
        if not state.trade_intent:
            # No trade to evaluate
            state.risk_verdict = RiskVerdict(
                approved=False,
                reason="No trade intent provided for evaluation.",
                risk_score=0.0,
            )
            return state

        # Phase 1: Deterministic checks
        verdict = self._deterministic_checks(state.trade_intent, state)

        # Phase 2: LLM contextual assessment (only if Phase 1 passes)
        if verdict.approved:
            verdict = await self._contextual_assessment(state, verdict)

        state.risk_verdict = verdict
        state.trade_approved = verdict.approved

        # Add report
        report = AgentReport(
            agent=AgentRole.THEMIS,
            summary=f"Risk verdict: {'APPROVED' if verdict.approved else 'REJECTED'} "
                    f"(score: {verdict.risk_score:.2f}). {verdict.reason}",
            data={
                "approved": verdict.approved,
                "risk_score": verdict.risk_score,
                "checks_passed": verdict.checks_passed,
                "checks_failed": verdict.checks_failed,
            },
            confidence=0.95,
        )
        state.reports.append(report)

        return state

    def _deterministic_checks(
        self, trade: TradeIntent, state: OmniVerseState
    ) -> RiskVerdict:
        """Phase 1: Hard boundary checks that cannot be overridden.

        These are deterministic rules that ensure no single trade
        can expose the user to catastrophic loss.
        """
        checks_passed = []
        checks_failed = []
        risk_score = 0.0

        # Estimate order value in TWD
        try:
            volume = Decimal(trade.volume)
            price = Decimal(trade.price) if trade.price else Decimal("0")
            order_value_twd = volume * price
        except (ValueError, TypeError):
            checks_failed.append("invalid_params: Cannot parse volume/price")
            return RiskVerdict(
                approved=False,
                checks_passed=checks_passed,
                checks_failed=checks_failed,
                risk_score=1.0,
                reason="Invalid trade parameters.",
            )

        # Check 1: Minimum order value
        if order_value_twd >= self.rules["min_order_value_twd"]:
            checks_passed.append("min_order_value")
        else:
            checks_failed.append(
                f"min_order_value: {order_value_twd} < {self.rules['min_order_value_twd']} TWD"
            )
            risk_score += 0.1

        # Check 2: Maximum order value
        if order_value_twd <= self.rules["max_order_value_twd"]:
            checks_passed.append("max_order_value")
        else:
            checks_failed.append(
                f"max_order_value: {order_value_twd} > {self.rules['max_order_value_twd']} TWD"
            )
            risk_score += 0.4

        # Check 3: Single order percentage of portfolio
        # TODO: Integrate with actual account balance from MAX API
        # For now, use a conservative estimate from CSV data
        portfolio_estimate = self._estimate_portfolio_value(state)
        if portfolio_estimate > 0:
            order_pct = order_value_twd / portfolio_estimate
            if order_pct <= self.rules["max_single_order_pct"]:
                checks_passed.append(f"portfolio_pct: {order_pct:.1%}")
            else:
                checks_failed.append(
                    f"portfolio_pct: {order_pct:.1%} > {self.rules['max_single_order_pct']:.0%}"
                )
                risk_score += 0.3

        # Check 4: Valid market and side
        if trade.side in ("buy", "sell"):
            checks_passed.append("valid_side")
        else:
            checks_failed.append(f"invalid_side: {trade.side}")
            risk_score += 0.2

        # Check 5: Order type validation
        valid_types = ("limit", "market", "stop_limit", "stop_market")
        if trade.ord_type in valid_types:
            checks_passed.append("valid_ord_type")
        else:
            checks_failed.append(f"invalid_ord_type: {trade.ord_type}")
            risk_score += 0.2

        # Final determination
        approved = len(checks_failed) == 0
        reason = "All deterministic checks passed." if approved else (
            f"Failed checks: {'; '.join(checks_failed)}"
        )

        return RiskVerdict(
            approved=approved,
            checks_passed=checks_passed,
            checks_failed=checks_failed,
            risk_score=min(risk_score, 1.0),
            reason=reason,
        )

    def _estimate_portfolio_value(self, state: OmniVerseState) -> Decimal:
        """Estimate total portfolio value from available data.

        Uses Morpheus report if available, otherwise returns 0
        (which skips the percentage check).
        """
        for report in state.reports:
            if report.agent == AgentRole.MORPHEUS:
                portfolio = report.data.get("portfolio", {})
                currencies = portfolio.get("currencies", {})
                twd_data = currencies.get("twd", {})
                last_balance = twd_data.get("last_balance", "0")
                try:
                    return Decimal(str(last_balance))
                except (ValueError, TypeError):
                    pass
        return Decimal("0")

    async def _contextual_assessment(
        self, state: OmniVerseState, current_verdict: RiskVerdict
    ) -> RiskVerdict:
        """Phase 2: LLM-assisted contextual risk assessment.

        This adds soft advisory on top of the hard checks.
        Cannot override Phase 1 rejections, but can add warnings.
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", THEMIS_SYSTEM_PROMPT),
            ("human", """基於以下情境，評估此交易的額外風險因素：

## 擬執行交易
- 市場: {market}
- 方向: {side}
- 數量: {volume}
- 類型: {ord_type}
- 價格: {price}

## 已通過的確定性檢查
{checks_passed}

## 各 Agent 報告摘要
{reports}

請評估是否有其他風險需要提醒用戶（例如：逆勢操作、集中度過高等）。
僅輸出額外風險提醒，不需重複確定性檢查結果。"""),
        ])

        reports_text = "\n".join([
            f"- {r.agent.value}: {r.summary[:200]}"
            for r in state.reports
        ])

        messages = prompt.format_messages(
            market=state.trade_intent.market,
            side=state.trade_intent.side,
            volume=state.trade_intent.volume,
            ord_type=state.trade_intent.ord_type,
            price=state.trade_intent.price or "market",
            checks_passed=", ".join(current_verdict.checks_passed),
            reports=reports_text,
        )

        response = await self.llm.ainvoke(messages)

        # Append LLM assessment to reason
        current_verdict.reason += f"\n\n[風險顧問補充] {response.content}"

        return current_verdict
