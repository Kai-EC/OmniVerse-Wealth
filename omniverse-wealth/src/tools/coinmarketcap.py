"""CoinMarketCap API Client.

Provides global cryptocurrency ranking, market cap, volume,
and price data for Minerva agent's analysis.

API Docs: https://coinmarketcap.com/api/documentation/v1/
Free tier: 10,000 calls/month, basic endpoints
"""

import httpx

from src.config import settings


class CoinMarketCapClient:
    """Async client for CoinMarketCap API."""

    BASE_URL = "https://pro-api.coinmarketcap.com/v1"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.coinmarketcap_api_key
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=15.0,
            headers={
                "X-CMC_PRO_API_KEY": self.api_key,
                "Accept": "application/json",
            },
        )

    async def close(self):
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

    async def get_listings(
        self,
        limit: int = 20,
        convert: str = "USD",
    ) -> list[dict]:
        """Get latest cryptocurrency listings ranked by market cap.

        Args:
            limit: Number of results (max 5000).
            convert: Quote currency for price data.

        Returns:
            List of crypto assets with price, market cap, volume.
        """
        response = await self._client.get(
            "/cryptocurrency/listings/latest",
            params={"limit": limit, "convert": convert},
        )
        data = response.json()
        return data.get("data", [])

    async def get_quotes(
        self,
        symbols: list[str],
        convert: str = "USD",
    ) -> dict:
        """Get current quotes for specific cryptocurrencies.

        Args:
            symbols: List of symbols (e.g., ["BTC", "ETH"]).
            convert: Quote currency.

        Returns:
            Dict mapping symbol to quote data.
        """
        response = await self._client.get(
            "/cryptocurrency/quotes/latest",
            params={"symbol": ",".join(symbols), "convert": convert},
        )
        data = response.json()
        return data.get("data", {})

    async def get_global_metrics(self) -> dict:
        """Get global cryptocurrency market metrics.

        Returns:
            Global metrics including total market cap, BTC dominance, etc.
        """
        response = await self._client.get("/global-metrics/quotes/latest")
        data = response.json()
        return data.get("data", {})

    async def get_fear_greed_latest(self) -> dict:
        """Get latest Fear & Greed Index from CMC.

        Note: This requires a paid plan. For free alternatives,
        use Alternative.me API (integrated in social_sentiment.py).

        Returns:
            Fear & Greed Index data.
        """
        response = await self._client.get(
            "/global-metrics/quotes/latest",
        )
        return response.json().get("data", {})
