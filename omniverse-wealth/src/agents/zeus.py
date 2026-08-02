"""Zeus (宙斯) - Commander / Orchestrator Agent.

Responsibilities:
- Parse user intent from natural language input
- Decompose complex queries into sub-tasks
- Route tasks to appropriate specialist agents
- Aggregate and synthesize reports into final response
- Generate actionable investment suggestions

LLM: Amazon Bedrock (Claude 3.5 Sonnet)
Permission: Orchestrator (no direct data access)
"""

from langchain_aws import ChatBedrock
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from src.agents.base import AgentReport, AgentRole, OmniVerseState, TradeIntent
from src.config import settings

ZEUS_SYSTEM_PROMPT = """\
你是宙斯 (Zeus)，OmniVerse Wealth 全域多元宇宙投資特助系統的總指揮官 Agent。

## 你的職責
1. **意圖解析**：精準理解用戶的投資相關問題或指令
2. **任務拆解**：判斷需要調動哪些專家 Agent 來回答用戶問題
3. **結果編排**：彙整各 Agent 的分析報告，產生連貫且有洞察的最終建議
4. **風險意識**：當涉及交易時，確保走完完整的風控流程

## 可調度的專家 Agent
- **stark** (史塔克): 即時行情分析、K線形態識別、深度圖分析、技術指標
- **minerva** (密涅瓦): 社群輿論熱度、貪婪恐懼指數、巨鯨轉帳、鏈上活躍度
- **morpheus** (墨菲斯): 個人歷史交易分析、持倉均價、歷史勝率、交易偏好
- **themis** (提彌斯): 風險評估、下單金額檢查、波動熔斷判斷
- **hermes** (赫密士): 實際下單執行（僅在風控通過後觸發）

## 意圖分類
- **query_portfolio**: 用戶詢問自己的持倉、損益、歷史表現
- **query_market**: 用戶詢問市場行情、某幣種走勢
- **query_sentiment**: 用戶詢問市場情緒、社群看法
- **trade_suggestion**: 用戶詢問是否應該買入/賣出/加碼
- **execute_trade**: 用戶明確要求下單交易
- **general**: 一般性加密貨幣或投資問題

## 輸出規則
- 永遠使用繁體中文回覆用戶
- 涉及金額時保留精確小數位
- 建議應具體可行，包含幣種、方向、數量建議
- 明確標示風險等級與免責聲明
"""


class ZeusAgent:
    """Zeus orchestrator agent - parses intent and coordinates sub-agents."""

    def __init__(self):
        self.llm = ChatBedrock(
            model_id=settings.bedrock_model_id,
            region_name=settings.aws_region,
            model_kwargs={"temperature": 0.3, "max_tokens": 4096},
        )

    async def parse_intent(self, state: OmniVerseState) -> OmniVerseState:
        """Parse user query and determine which agents to invoke.

        This is the first node in the graph - it analyzes the user's message
        and decides the routing strategy.
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", ZEUS_SYSTEM_PROMPT),
            ("human", """分析以下用戶輸入，回傳 JSON 格式：
{{
    "intent": "<意圖分類>",
    "required_agents": ["<需要調度的agent列表>"],
    "trade_intent": null 或 {{"market": "...", "side": "...", "volume": "...", "ord_type": "...", "price": null, "reasoning": "..."}},
    "brief_plan": "<你的執行計畫簡述>"
}}

用戶輸入: {user_query}"""),
        ])

        messages = prompt.format_messages(user_query=state.user_query)
        response = await self.llm.ainvoke(messages)

        # Parse the structured response
        import json
        try:
            content = response.content
            # Extract JSON from potential markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            parsed = json.loads(content.strip())

            state.intent = parsed.get("intent", "general")
            state.required_agents = [
                AgentRole(a) for a in parsed.get("required_agents", [])
            ]

            if parsed.get("trade_intent"):
                state.trade_intent = TradeIntent(**parsed["trade_intent"])

        except (json.JSONDecodeError, ValueError, KeyError):
            # Fallback: conservative routing
            state.intent = "general"
            state.required_agents = [AgentRole.STARK, AgentRole.MORPHEUS]

        return state

    async def synthesize(self, state: OmniVerseState) -> OmniVerseState:
        """Synthesize all agent reports into a final coherent response.

        This is the final node - it combines insights from all specialist agents
        and generates the user-facing response.
        """
        reports_text = "\n\n".join([
            f"### {report.agent.value.upper()} 報告 (信心度: {report.confidence:.0%})\n{report.summary}\n數據: {report.data}"
            for report in state.reports
        ])

        risk_info = ""
        if state.risk_verdict:
            risk_info = f"""
### 風控審查結果
- 審查通過: {'✅ 是' if state.risk_verdict.approved else '❌ 否'}
- 風險分數: {state.risk_verdict.risk_score:.2f}
- 通過項目: {', '.join(state.risk_verdict.checks_passed)}
- 未通過項目: {', '.join(state.risk_verdict.checks_failed)}
- 說明: {state.risk_verdict.reason}
"""

        trade_result = ""
        if state.trade_result:
            trade_result = f"""
### 交易執行結果
{state.trade_result}
"""

        synthesis_prompt = ChatPromptTemplate.from_messages([
            ("system", ZEUS_SYSTEM_PROMPT),
            ("human", """根據以下各專家 Agent 的分析報告，為用戶生成最終的投資建議回覆。

## 用戶原始問題
{user_query}

## 各 Agent 報告
{reports}

{risk_info}

{trade_result}

## 要求
- 整合所有 Agent 的觀點，給出全面且易懂的回覆
- 如果有交易建議，明確列出幣種、方向、數量、理由
- 附上風險提示
- 使用繁體中文
"""),
        ])

        messages = synthesis_prompt.format_messages(
            user_query=state.user_query,
            reports=reports_text,
            risk_info=risk_info,
            trade_result=trade_result,
        )

        response = await self.llm.ainvoke(messages)
        state.final_response = response.content

        return state
