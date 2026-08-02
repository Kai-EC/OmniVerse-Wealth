"""Hermes (赫密士) - Trade Execution Agent.

Responsibilities:
- Generate and submit trade payloads via MAX API
- Call MAX Skill / MCP Server for order execution
- Handle order lifecycle (submit, confirm, cancel)
- Report execution results back to Zeus

Data Sources: MAX Skill, MAX MCP Server, MAX Private API (Trade/Order)
Permission: Write (Execute Trade) - ONLY after Themis approval
"""

from langchain_aws import ChatBedrock
from langchain_core.prompts import ChatPromptTemplate

from src.agents.base import (
    AgentReport,
    AgentRole,
    OmniVerseState,
    TradeIntent,
)
from src.config import settings
from src.tools.max_client import MaxClient, MaxAPIError

HERMES_SYSTEM_PROMPT = """\
你是赫密士 (Hermes)，OmniVerse Wealth 的交易執行專家 Agent。

## 你的職責
1. 接收經風控驗證通過的交易指令
2. 生成正確的交易 Payload
3. 透過 MAX API / MCP Server 執行下單
4. 監控訂單狀態並回報結果

## 安全規則 (不可違反)
- ⚠️ 只有在提彌斯 (Themis) 明確核准後才能執行交易
- ⚠️ 絕不自行發起未經授權的交易
- ⚠️ 所有交易參數必須與風控核准的完全一致
- ⚠️ 執行失敗時立即回報，不得重試未經授權的操作

## 執行流程
1. 確認 trade_approved == True
2. 驗證交易參數完整性
3. 呼叫 MAX API 下單
4. 回傳訂單 ID 與狀態
"""


class HermesAgent:
    """Trade Execution agent - the only agent with write permissions.

    CRITICAL: This agent ONLY executes trades that have been explicitly
    approved by Themis (risk_verdict.approved == True).
    """

    def __init__(self):
        self.llm = ChatBedrock(
            model_id=settings.bedrock_model_id,
            region_name=settings.aws_region,
            model_kwargs={"temperature": 0.0, "max_tokens": 1000},
        )
        self.max_client = MaxClient()

    async def execute(self, state: OmniVerseState) -> OmniVerseState:
        """Execute an approved trade via MAX API.

        This method REFUSES to execute if:
        - trade_approved is False
        - risk_verdict is None or not approved
        - trade_intent is missing required fields
        """
        # Safety gate: MUST have Themis approval
        if not state.trade_approved:
            report = AgentReport(
                agent=AgentRole.HERMES,
                summary="❌ 交易執行被拒絕：未獲得提彌斯風控核准。",
                data={"status": "rejected", "reason": "not_approved"},
                confidence=1.0,
            )
            state.reports.append(report)
            return state

        if not state.risk_verdict or not state.risk_verdict.approved:
            report = AgentReport(
                agent=AgentRole.HERMES,
                summary="❌ 交易執行被拒絕：風控審查未通過。",
                data={"status": "rejected", "reason": "risk_check_failed"},
                confidence=1.0,
            )
            state.reports.append(report)
            return state

        if not state.trade_intent:
            report = AgentReport(
                agent=AgentRole.HERMES,
                summary="❌ 交易執行被拒絕：缺少交易意圖資訊。",
                data={"status": "rejected", "reason": "no_trade_intent"},
                confidence=1.0,
            )
            state.reports.append(report)
            return state

        # Execute the trade
        trade = state.trade_intent
        try:
            result = await self._submit_order(trade)
            state.trade_result = result

            report = AgentReport(
                agent=AgentRole.HERMES,
                summary=(
                    f"✅ 訂單已提交成功！\n"
                    f"- 市場: {trade.market}\n"
                    f"- 方向: {trade.side}\n"
                    f"- 數量: {trade.volume}\n"
                    f"- 訂單ID: {result.get('id', 'N/A')}\n"
                    f"- 狀態: {result.get('state', 'N/A')}"
                ),
                data=result,
                confidence=1.0,
            )

        except MaxAPIError as e:
            state.trade_result = {
                "status": "error",
                "error_code": e.code,
                "error_message": e.message,
            }
            report = AgentReport(
                agent=AgentRole.HERMES,
                summary=f"❌ 下單失敗：{e.message} (錯誤碼: {e.code})",
                data={"status": "error", "error": str(e)},
                confidence=1.0,
            )

        except Exception as e:
            state.trade_result = {
                "status": "error",
                "error_message": str(e),
            }
            report = AgentReport(
                agent=AgentRole.HERMES,
                summary=f"❌ 下單過程中發生未預期錯誤：{str(e)}",
                data={"status": "error", "error": str(e)},
                confidence=1.0,
            )

        state.reports.append(report)
        return state

    async def _submit_order(self, trade: TradeIntent) -> dict:
        """Submit order to MAX Exchange via REST API.

        Args:
            trade: Validated and approved trade intent

        Returns:
            Order response from MAX API
        """
        async with MaxClient() as client:
            result = await client.create_order(
                market=trade.market,
                side=trade.side,
                volume=trade.volume,
                ord_type=trade.ord_type,
                price=trade.price,
            )
        return result

    async def check_order_status(self, order_id: int) -> dict:
        """Check the status of a submitted order.

        Args:
            order_id: The MAX order ID to check

        Returns:
            Order status details
        """
        async with MaxClient() as client:
            return await client.get_order(order_id)

    async def cancel_order(self, order_id: int) -> dict:
        """Cancel an active order.

        Args:
            order_id: The MAX order ID to cancel

        Returns:
            Cancellation result
        """
        async with MaxClient() as client:
            return await client.cancel_order(order_id)
