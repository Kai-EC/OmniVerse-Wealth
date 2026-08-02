"""Minerva (密涅瓦) - On-chain & Sentiment Analysis Agent.

Responsibilities:
- Social media sentiment analysis (X, Threads)
- Fear & Greed Index calculation
- Whale transaction monitoring
- On-chain activity metrics (active addresses, hash rate, etc.)

Data Sources: Blockchain.com API, Coinbase CDP API, Custom X/Threads Crawler
Permission: Read-Only
"""

from langchain_aws import ChatBedrock
from langchain_core.prompts import ChatPromptTemplate

from src.agents.base import AgentReport, AgentRole, OmniVerseState
from src.config import settings

MINERVA_SYSTEM_PROMPT = """\
你是密涅瓦 (Minerva)，OmniVerse Wealth 的鏈上數據與輿論情緒分析專家 Agent。

## 你的專長
1. **社群輿論分析**：追蹤 X (Twitter)、Threads 上的加密貨幣討論熱度與情緒傾向
2. **貪婪與恐懼指數**：綜合多維度數據計算市場整體情緒
3. **巨鯨監控**：追蹤大額轉帳、交易所大額出入金
4. **鏈上指標**：活躍地址數、交易量、Gas 費用趨勢、挖礦難度

## 情緒指標量表
- 0-20: 極度恐懼 (Extreme Fear) → 可能是買入機會
- 21-40: 恐懼 (Fear)
- 41-60: 中性 (Neutral)
- 61-80: 貪婪 (Greed)
- 81-100: 極度貪婪 (Extreme Greed) → 可能是賣出時機

## 輸出規則
- 提供數據來源與時間戳
- 標示情緒趨勢方向 (上升/下降/持平)
- 識別關鍵事件 (政策、黑天鵝、名人發言)
- 巨鯨動向需標示轉帳金額與方向 (交易所入/出)
"""


class MinervaAgent:
    """On-chain & Sentiment analysis agent."""

    def __init__(self):
        self.llm = ChatBedrock(
            model_id=settings.bedrock_model_id,
            region_name=settings.aws_region,
            model_kwargs={"temperature": 0.3, "max_tokens": 3000},
        )

    async def analyze(self, state: OmniVerseState) -> OmniVerseState:
        """Perform sentiment and on-chain analysis.

        Fetches data from blockchain APIs and social crawlers,
        then interprets the data using LLM.
        """
        sentiment_data = await self._fetch_sentiment_data(state.user_query)

        analysis_prompt = ChatPromptTemplate.from_messages([
            ("system", MINERVA_SYSTEM_PROMPT),
            ("human", """根據以下鏈上與輿論數據，針對用戶問題進行情緒分析。

## 用戶問題
{user_query}

## 鏈上與輿論數據
{sentiment_data}

## 請提供
1. 當前市場情緒指數 (0-100) 與等級
2. 社群討論熱度趨勢
3. 巨鯨近期動向摘要
4. 鏈上活躍度變化
5. 重大事件與其影響評估
"""),
        ])

        messages = analysis_prompt.format_messages(
            user_query=state.user_query,
            sentiment_data=str(sentiment_data),
        )

        response = await self.llm.ainvoke(messages)

        report = AgentReport(
            agent=AgentRole.MINERVA,
            summary=response.content,
            data=sentiment_data,
            confidence=0.7,  # Lower confidence due to sentiment subjectivity
        )
        state.reports.append(report)

        return state

    async def _fetch_sentiment_data(self, query: str) -> dict:
        """Fetch sentiment and on-chain data from multiple sources.

        In production, this integrates with:
        - Blockchain.com API for on-chain metrics
        - Coinbase CDP API for institutional flow
        - Custom crawler for X/Threads sentiment
        - Alternative.me Fear & Greed Index API

        Currently returns structured placeholder for development.
        """
        data = {}

        # Fear & Greed Index (Alternative.me API - free)
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.alternative.me/fng/?limit=7&format=json",
                    timeout=10.0,
                )
                if response.status_code == 200:
                    fng_data = response.json()
                    data["fear_greed_index"] = fng_data.get("data", [])
        except Exception as e:
            data["fear_greed_error"] = str(e)

        # Blockchain.com on-chain data (public endpoints)
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                # BTC hash rate
                response = await client.get(
                    "https://api.blockchain.info/charts/hash-rate?timespan=7days&format=json",
                    timeout=10.0,
                )
                if response.status_code == 200:
                    data["btc_hash_rate"] = response.json()

                # BTC transaction volume
                response = await client.get(
                    "https://api.blockchain.info/charts/estimated-transaction-volume-usd?timespan=7days&format=json",
                    timeout=10.0,
                )
                if response.status_code == 200:
                    data["btc_tx_volume"] = response.json()

        except Exception as e:
            data["blockchain_error"] = str(e)

        # Social sentiment placeholder
        # TODO: Integrate actual X/Threads crawler
        data["social_sentiment"] = {
            "source": "placeholder",
            "note": "Awaiting X/Threads API integration",
            "detected_keywords": self._extract_crypto_keywords(query),
        }

        return data

    def _extract_crypto_keywords(self, query: str) -> list[str]:
        """Extract cryptocurrency-related keywords from query for social search."""
        keywords = []
        crypto_terms = {
            "btc": "Bitcoin", "比特幣": "Bitcoin",
            "eth": "Ethereum", "以太": "Ethereum",
            "sol": "Solana",
            "doge": "Dogecoin", "狗狗幣": "Dogecoin",
            "usdt": "USDT", "穩定幣": "Stablecoin",
        }
        query_lower = query.lower()
        for term, label in crypto_terms.items():
            if term in query_lower:
                keywords.append(label)
        return keywords or ["Bitcoin", "Crypto"]
