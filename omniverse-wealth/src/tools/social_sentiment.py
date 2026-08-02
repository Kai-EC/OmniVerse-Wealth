"""Social Sentiment Analysis Module.

Aggregates sentiment data from multiple sources:
- Alternative.me Fear & Greed Index (free, no auth)
- X (Twitter) keyword analysis (placeholder for crawler)
- Threads sentiment (placeholder for crawler)

Used by Minerva agent for market sentiment evaluation.
"""

import httpx


class SentimentAnalyzer:
    """Aggregates cryptocurrency market sentiment from multiple sources."""

    def __init__(self):
        self._client = httpx.AsyncClient(timeout=15.0)

    async def close(self):
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

    # ─── Fear & Greed Index (Alternative.me) ────────────────────────────────

    async def get_fear_greed_index(self, days: int = 7) -> dict:
        """Get Crypto Fear & Greed Index from Alternative.me.

        This is a free API with no authentication required.

        Scale:
            0-24:  Extreme Fear
            25-49: Fear
            50:    Neutral
            51-74: Greed
            75-100: Extreme Greed

        Args:
            days: Number of days of history to fetch.

        Returns:
            Dict with current value, classification, and history.
        """
        try:
            response = await self._client.get(
                "https://api.alternative.me/fng/",
                params={"limit": days, "format": "json"},
            )
            data = response.json()
            entries = data.get("data", [])

            if not entries:
                return {"error": "No data available"}

            current = entries[0]
            return {
                "current_value": int(current.get("value", 50)),
                "classification": current.get("value_classification", "Neutral"),
                "timestamp": current.get("timestamp"),
                "history": [
                    {
                        "value": int(e.get("value", 50)),
                        "classification": e.get("value_classification"),
                        "timestamp": e.get("timestamp"),
                    }
                    for e in entries
                ],
                "trend": self._calculate_trend(entries),
            }
        except Exception as e:
            return {"error": str(e), "current_value": 50, "classification": "Unknown"}

    def _calculate_trend(self, entries: list[dict]) -> str:
        """Calculate sentiment trend direction from history.

        Args:
            entries: List of Fear & Greed entries (newest first).

        Returns:
            'rising', 'falling', or 'stable'
        """
        if len(entries) < 2:
            return "stable"

        values = [int(e.get("value", 50)) for e in entries[:7]]
        recent_avg = sum(values[:3]) / min(3, len(values[:3]))
        older_avg = sum(values[3:]) / max(1, len(values[3:]))

        diff = recent_avg - older_avg
        if diff > 5:
            return "rising"
        elif diff < -5:
            return "falling"
        return "stable"

    # ─── Social Media Sentiment (X / Threads) ───────────────────────────────

    async def get_social_sentiment(
        self, keywords: list[str] | None = None
    ) -> dict:
        """Get social media sentiment analysis.

        Currently uses a structured placeholder that returns
        sentiment signals based on Fear & Greed + market proxy.

        TODO: Integrate actual X API v2 and Threads API when available.

        Args:
            keywords: Crypto keywords to search for.

        Returns:
            Social sentiment analysis result.
        """
        keywords = keywords or ["Bitcoin", "BTC", "crypto"]

        # Get Fear & Greed as base signal
        fng = await self.get_fear_greed_index(days=3)

        # Derive social sentiment from Fear & Greed
        # (placeholder until real social APIs are integrated)
        fng_value = fng.get("current_value", 50)

        sentiment_score = fng_value / 100.0  # Normalize to 0-1

        if sentiment_score > 0.75:
            dominant_sentiment = "極度樂觀"
            risk_signal = "注意過熱風險"
        elif sentiment_score > 0.55:
            dominant_sentiment = "偏向樂觀"
            risk_signal = "市場情緒正面"
        elif sentiment_score > 0.45:
            dominant_sentiment = "中性觀望"
            risk_signal = "市場觀望中"
        elif sentiment_score > 0.25:
            dominant_sentiment = "偏向恐懼"
            risk_signal = "可能為買入機會"
        else:
            dominant_sentiment = "極度恐懼"
            risk_signal = "恐慌拋售中，逆向投資機會"

        return {
            "keywords_analyzed": keywords,
            "sentiment_score": round(sentiment_score, 3),
            "dominant_sentiment": dominant_sentiment,
            "risk_signal": risk_signal,
            "fear_greed": fng,
            "data_sources": {
                "fear_greed_index": "Alternative.me (active)",
                "x_twitter": "placeholder (待整合)",
                "threads": "placeholder (待整合)",
            },
        }

    # ─── Whale Alert Monitoring ─────────────────────────────────────────────

    async def get_whale_alerts(self) -> dict:
        """Get recent whale (large transaction) alerts.

        TODO: Integrate Whale Alert API or on-chain monitoring.
        Currently returns placeholder structure.

        Returns:
            Whale activity summary.
        """
        return {
            "status": "placeholder",
            "note": "Awaiting Whale Alert API integration",
            "schema": {
                "large_transfers": [
                    {
                        "currency": "BTC",
                        "amount": "example",
                        "from_type": "exchange|unknown",
                        "to_type": "exchange|unknown",
                        "timestamp": "ISO8601",
                    }
                ],
                "exchange_inflow_24h": "total BTC flowing into exchanges",
                "exchange_outflow_24h": "total BTC flowing out of exchanges",
                "signal": "accumulation|distribution|neutral",
            },
        }

    # ─── Aggregated Analysis ────────────────────────────────────────────────

    async def get_full_sentiment_report(
        self, target_assets: list[str] | None = None
    ) -> dict:
        """Generate a comprehensive sentiment report for Minerva agent.

        Combines all available data sources into a single analysis.

        Args:
            target_assets: Assets to focus on (e.g., ["BTC", "ETH"]).

        Returns:
            Comprehensive sentiment report dict.
        """
        target_assets = target_assets or ["BTC", "ETH"]

        # Gather all data
        fng = await self.get_fear_greed_index(days=7)
        social = await self.get_social_sentiment(target_assets)
        whales = await self.get_whale_alerts()

        return {
            "summary": {
                "overall_sentiment_score": social["sentiment_score"],
                "market_mood": social["dominant_sentiment"],
                "risk_advisory": social["risk_signal"],
                "trend_direction": fng.get("trend", "stable"),
            },
            "fear_greed_index": fng,
            "social_analysis": social,
            "whale_activity": whales,
            "target_assets": target_assets,
        }
