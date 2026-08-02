"""Blockchain.com API Client.

Provides on-chain data for Bitcoin network analysis,
used by Minerva agent for on-chain activity monitoring.

Public API (no auth required): https://www.blockchain.com/explorer/api
"""

import httpx


class BlockchainClient:
    """Async client for Blockchain.com public APIs."""

    CHARTS_URL = "https://api.blockchain.info/charts"
    STATS_URL = "https://api.blockchain.info/stats"

    def __init__(self):
        self._client = httpx.AsyncClient(timeout=15.0)

    async def close(self):
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

    async def get_stats(self) -> dict:
        """Get Bitcoin network statistics.

        Returns:
            Dict with market_price_usd, hash_rate, difficulty,
            miners_revenue, n_tx, n_blocks_mined, etc.
        """
        response = await self._client.get(self.STATS_URL)
        return response.json()

    async def get_hash_rate(self, timespan: str = "7days") -> dict:
        """Get Bitcoin hash rate chart data.

        Args:
            timespan: Duration (e.g., '7days', '30days', '1year').

        Returns:
            Chart data with timestamps and values.
        """
        response = await self._client.get(
            f"{self.CHARTS_URL}/hash-rate",
            params={"timespan": timespan, "format": "json"},
        )
        return response.json()

    async def get_transaction_volume(self, timespan: str = "7days") -> dict:
        """Get estimated Bitcoin transaction volume in USD.

        Args:
            timespan: Duration.

        Returns:
            Chart data with daily transaction volumes.
        """
        response = await self._client.get(
            f"{self.CHARTS_URL}/estimated-transaction-volume-usd",
            params={"timespan": timespan, "format": "json"},
        )
        return response.json()

    async def get_mempool_size(self, timespan: str = "7days") -> dict:
        """Get Bitcoin mempool size (unconfirmed transactions).

        Args:
            timespan: Duration.

        Returns:
            Chart data showing mempool congestion over time.
        """
        response = await self._client.get(
            f"{self.CHARTS_URL}/mempool-size",
            params={"timespan": timespan, "format": "json"},
        )
        return response.json()

    async def get_active_addresses(self, timespan: str = "7days") -> dict:
        """Get number of unique active Bitcoin addresses.

        Args:
            timespan: Duration.

        Returns:
            Chart data with daily active address counts.
        """
        response = await self._client.get(
            f"{self.CHARTS_URL}/n-unique-addresses",
            params={"timespan": timespan, "format": "json"},
        )
        return response.json()

    async def get_difficulty(self, timespan: str = "60days") -> dict:
        """Get Bitcoin mining difficulty history.

        Args:
            timespan: Duration.

        Returns:
            Chart data with difficulty adjustments.
        """
        response = await self._client.get(
            f"{self.CHARTS_URL}/difficulty",
            params={"timespan": timespan, "format": "json"},
        )
        return response.json()

    async def get_market_price(self, timespan: str = "30days") -> dict:
        """Get Bitcoin market price in USD.

        Args:
            timespan: Duration.

        Returns:
            Chart data with daily average prices.
        """
        response = await self._client.get(
            f"{self.CHARTS_URL}/market-price",
            params={"timespan": timespan, "format": "json"},
        )
        return response.json()

    async def get_comprehensive_metrics(self) -> dict:
        """Fetch all key on-chain metrics in one call.

        Aggregates multiple data points for Minerva agent.

        Returns:
            Dict with all major on-chain indicators.
        """
        stats = await self.get_stats()

        return {
            "btc_price_usd": stats.get("market_price_usd"),
            "hash_rate_th": stats.get("hash_rate", 0) / 1e12,  # Convert to TH/s
            "difficulty": stats.get("difficulty"),
            "total_tx_24h": stats.get("n_tx"),
            "blocks_mined_24h": stats.get("n_blocks_mined"),
            "minutes_between_blocks": stats.get("minutes_between_blocks"),
            "total_btc_sent_24h": stats.get("total_btc_sent", 0) / 1e8,
            "miners_revenue_usd": stats.get("miners_revenue_usd"),
            "trade_volume_usd": stats.get("trade_volume_usd"),
        }
