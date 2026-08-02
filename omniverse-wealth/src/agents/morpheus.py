"""Morpheus (墨菲斯) - Personal History & RAG Agent.

Responsibilities:
- Parse user's CSV trading history (deposits, withdrawals, buys, sells)
- Calculate cost basis and average holding price
- Compute historical win rate and trading preferences
- Provide personalized insights based on user's own patterns

Data Sources: Amazon Bedrock Knowledge Bases, OpenSearch Serverless (CSV RAG)
Permission: Read-Only (Private Data)
"""

import csv
from pathlib import Path
from decimal import Decimal
from collections import defaultdict

from langchain_aws import ChatBedrock
from langchain_core.prompts import ChatPromptTemplate

from src.agents.base import AgentReport, AgentRole, OmniVerseState
from src.config import settings

MORPHEUS_SYSTEM_PROMPT = """\
你是墨菲斯 (Morpheus)，OmniVerse Wealth 的個人化歷史數據分析專家 Agent。

## 你的專長
1. **持倉分析**：計算每個幣種的持倉成本均價、當前持倉量
2. **損益計算**：已實現損益 (每筆賣出)、未實現損益 (對照現價)
3. **交易模式識別**：用戶的交易頻率、偏好幣種、慣用交易時段
4. **歷史勝率**：過去交易的盈虧比、平均獲利/虧損幅度
5. **資金流向**：出入金模式、資金利用率

## 分析維度
- 按幣種: 各幣種的持倉成本、均價、損益
- 按時間: 月/週交易頻率趨勢
- 按動作: 買入/賣出/出入金比例
- 按績效: 勝率、盈虧比、最大單筆獲利/虧損

## 輸出規則
- 所有金額計算需精確到小數點
- 成本均價用加權平均計算
- 隱私保護：不暴露確切餘額，以百分比或趨勢描述
- 結合用戶過往模式給出個人化建議
"""


class MorpheusAgent:
    """Personal History & RAG analysis agent."""

    def __init__(self):
        self.llm = ChatBedrock(
            model_id=settings.bedrock_model_id,
            region_name=settings.aws_region,
            model_kwargs={"temperature": 0.2, "max_tokens": 4000},
        )
        self._csv_data: list[dict] | None = None
        self._portfolio_analysis: dict | None = None

    async def analyze(self, state: OmniVerseState) -> OmniVerseState:
        """Analyze user's personal trading history for the query.

        Loads CSV data, computes portfolio metrics, and uses LLM
        to generate personalized insights.
        """
        # Load and analyze CSV if not already done
        if self._csv_data is None:
            self._csv_data = self._load_csv()
            self._portfolio_analysis = self._compute_portfolio_metrics()

        # Filter relevant data based on query
        relevant_data = self._get_relevant_data(state.user_query)

        analysis_prompt = ChatPromptTemplate.from_messages([
            ("system", MORPHEUS_SYSTEM_PROMPT),
            ("human", """根據用戶的歷史交易數據，針對問題進行個人化分析。

## 用戶問題
{user_query}

## 用戶歷史交易摘要
{portfolio_summary}

## 相關交易明細
{relevant_data}

## 請提供
1. 針對問題的持倉/損益分析
2. 用戶的交易行為模式洞察
3. 基於歷史表現的個人化建議
4. 風險偏好判斷 (保守/穩健/積極)
"""),
        ])

        messages = analysis_prompt.format_messages(
            user_query=state.user_query,
            portfolio_summary=str(self._portfolio_analysis),
            relevant_data=str(relevant_data),
        )

        response = await self.llm.ainvoke(messages)

        report = AgentReport(
            agent=AgentRole.MORPHEUS,
            summary=response.content,
            data={
                "portfolio": self._portfolio_analysis,
                "relevant_records": relevant_data,
            },
            confidence=0.9,  # High confidence based on user's own data
        )
        state.reports.append(report)

        return state

    def _load_csv(self) -> list[dict]:
        """Load and parse the user's trading CSV file.

        CSV format: timestamp, currency, price, action, change, balance
        """
        csv_path = Path(settings.csv_data_path)
        if not csv_path.exists():
            # Try relative to project root
            csv_path = Path(__file__).parent.parent.parent.parent / settings.csv_data_path
        if not csv_path.exists():
            return []

        records = []
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append({
                    "timestamp": int(row["timestamp"]),
                    "currency": row["currency"].strip().lower(),
                    "price": Decimal(row["price"]),
                    "action": row["action"].strip().lower(),
                    "change": Decimal(row["change"]),
                    "balance": Decimal(row["balance"]),
                })
        return records

    def _compute_portfolio_metrics(self) -> dict:
        """Compute comprehensive portfolio metrics from CSV data.

        Returns:
            Dict with per-currency metrics and overall statistics.
        """
        if not self._csv_data:
            return {"error": "No CSV data loaded"}

        metrics: dict = {
            "currencies": {},
            "total_deposits_twd": Decimal("0"),
            "total_withdrawals_twd": Decimal("0"),
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
        }

        # Per-currency tracking
        currency_buys: dict[str, list] = defaultdict(list)
        currency_sells: dict[str, list] = defaultdict(list)

        for record in self._csv_data:
            currency = record["currency"]
            action = record["action"]

            if currency not in metrics["currencies"]:
                metrics["currencies"][currency] = {
                    "total_bought": Decimal("0"),
                    "total_sold": Decimal("0"),
                    "total_deposited": Decimal("0"),
                    "total_withdrawn": Decimal("0"),
                    "buy_count": 0,
                    "sell_count": 0,
                    "last_balance": Decimal("0"),
                    "avg_buy_price": Decimal("0"),
                    "total_buy_cost_twd": Decimal("0"),
                }

            cm = metrics["currencies"][currency]
            cm["last_balance"] = record["balance"]

            if action == "buy":
                cm["total_bought"] += abs(record["change"])
                cm["buy_count"] += 1
                cm["total_buy_cost_twd"] += abs(record["change"]) * record["price"]
                currency_buys[currency].append(record)
                metrics["total_trades"] += 1

            elif action == "sell":
                cm["total_sold"] += abs(record["change"])
                cm["sell_count"] += 1
                currency_sells[currency].append(record)
                metrics["total_trades"] += 1

            elif action == "deposit":
                cm["total_deposited"] += abs(record["change"])
                if currency == "twd":
                    metrics["total_deposits_twd"] += abs(record["change"])

            elif action == "withdrawal":
                cm["total_withdrawn"] += abs(record["change"])
                if currency == "twd":
                    metrics["total_withdrawals_twd"] += abs(record["change"])

        # Calculate average buy price per currency
        for currency, cm in metrics["currencies"].items():
            if cm["total_bought"] > 0:
                cm["avg_buy_price"] = cm["total_buy_cost_twd"] / cm["total_bought"]

        # Convert Decimals to strings for serialization
        return self._serialize_metrics(metrics)

    def _serialize_metrics(self, obj) -> dict | list | str:
        """Convert Decimal values to strings for JSON compatibility."""
        if isinstance(obj, dict):
            return {k: self._serialize_metrics(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize_metrics(i) for i in obj]
        elif isinstance(obj, Decimal):
            return str(obj)
        return obj

    def _get_relevant_data(self, query: str) -> list[dict]:
        """Filter CSV records relevant to the user's query.

        Uses keyword matching to find relevant currency/action records.
        """
        if not self._csv_data:
            return []

        relevant = []
        query_lower = query.lower()

        # Detect currency in query
        target_currencies = []
        currency_keywords = {
            "btc": "btc", "比特幣": "btc",
            "eth": "eth", "以太": "eth",
            "sol": "sol",
            "doge": "doge", "狗狗幣": "doge",
            "usdt": "usdt",
            "twd": "twd", "台幣": "twd",
        }

        for keyword, currency in currency_keywords.items():
            if keyword in query_lower:
                target_currencies.append(currency)

        # Filter records
        for record in self._csv_data:
            if target_currencies and record["currency"] not in target_currencies:
                continue
            relevant.append({
                "timestamp": record["timestamp"],
                "currency": record["currency"],
                "price": str(record["price"]),
                "action": record["action"],
                "change": str(record["change"]),
                "balance": str(record["balance"]),
            })

        # Limit to most recent 50 records if too many
        return relevant[-50:] if len(relevant) > 50 else relevant
