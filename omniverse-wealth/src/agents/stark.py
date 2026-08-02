"""Stark (史塔克) - Market & Technical Analysis Agent.

Responsibilities:
- Real-time price and ticker analysis via MAX API
- K-line pattern recognition (candlestick patterns)
- Order book depth analysis (buy/sell wall detection)
- Technical indicators (MA, RSI, MACD concepts)

Data Sources: MAX API (Public: Ticker, Depth, Trades, K-lines), CoinMarketCap API
Permission: Read-Only
"""

from langchain_aws import ChatBedrock
from langchain_core.prompts import ChatPromptTemplate

from src.agents.base import AgentReport, AgentRole, OmniVerseState
from src.config import settings
from src.tools.max_client import MaxClient

STARK_SYSTEM_PROMPT = """\
你是史塔克 (Stark)，OmniVerse Wealth 的市場與技術分析專家 Agent。

## 你的專長
1. **即時行情分析**：解讀 ticker 數據，判斷市場動能
2. **K 線形態識別**：從 K 線數據中識別技術形態 (錘子線、吞噬、十字星等)
3. **深度圖分析**：分析買賣掛單深度，識別支撐壓力位與大單
4. **技術指標解讀**：計算並解讀 MA、RSI、布林帶等指標含義

## 分析框架
- 短期 (1H-4H): 適合日內交易判斷
- 中期 (1D-1W): 適合波段操作
- 長期 (1M+): 適合定投與配置調整

## 輸出規則
- 所有價格保留原始精度 (字串格式)
- 明確標示時間框架
- 給出支撐/壓力價位
- 量化買賣力道比率
"""


class StarkAgent:
    """Market & Technical Analysis agent using MAX API public endpoints."""

    def __init__(self):
        self.llm = ChatBedrock(
            model_id=settings.bedrock_model_id,
            region_name=settings.aws_region,
            model_kwargs={"temperature": 0.2, "max_tokens": 3000},
        )
        self.max_client = MaxClient()

    async def analyze(self, state: OmniVerseState) -> OmniVerseState:
        """Perform market and technical analysis based on the user query.

        Fetches real-time data from MAX API and interprets it using LLM.
        """
        # Determine which market(s) to analyze from the query
        market_data = await self._fetch_market_data(state.user_query)

        analysis_prompt = ChatPromptTemplate.from_messages([
            ("system", STARK_SYSTEM_PROMPT),
            ("human", """根據以下 MAX 交易所即時數據，針對用戶問題進行技術分析。

## 用戶問題
{user_query}

## 即時行情數據
{market_data}

## 請提供
1. 當前價格趨勢判斷 (多/空/盤整)
2. 關鍵支撐與壓力價位
3. 買賣力道分析 (從深度圖)
4. 技術指標訊號
5. 短期操作建議方向
"""),
        ])

        messages = analysis_prompt.format_messages(
            user_query=state.user_query,
            market_data=str(market_data),
        )

        response = await self.llm.ainvoke(messages)

        report = AgentReport(
            agent=AgentRole.STARK,
            summary=response.content,
            data=market_data,
            confidence=0.85,
        )
        state.reports.append(report)

        return state

    async def _fetch_market_data(self, query: str) -> dict:
        """Fetch relevant market data from MAX API based on user query.

        Intelligently determines which markets and data points to fetch.
        """
        data = {}

        # Detect mentioned currencies from query
        currency_map = {
            "btc": "btctwd",
            "比特幣": "btctwd",
            "eth": "ethtwd",
            "以太": "ethtwd",
            "sol": "soltwd",
            "doge": "dogetwd",
            "usdt": "usdttwd",
        }

        target_markets = []
        query_lower = query.lower()
        for keyword, market in currency_map.items():
            if keyword in query_lower:
                target_markets.append(market)

        # Default to BTC if no specific market mentioned
        if not target_markets:
            target_markets = ["btctwd"]

        async with MaxClient() as client:
            for market in target_markets:
                try:
                    # Fetch ticker
                    ticker = await client.get_ticker(market)
                    data[f"{market}_ticker"] = ticker

                    # Fetch order book depth
                    depth = await client.get_order_book(market, limit=20)
                    data[f"{market}_depth"] = depth

                    # Fetch recent K-lines (1H candles, last 24)
                    klines = await client.get_klines(market, period=60, limit=24)
                    data[f"{market}_klines_1h"] = klines

                    # Fetch recent trades
                    trades = await client.get_public_trades(market, limit=30)
                    data[f"{market}_recent_trades"] = trades

                except Exception as e:
                    data[f"{market}_error"] = str(e)

        return data
