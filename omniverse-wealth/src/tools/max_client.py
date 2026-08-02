"""MAX Exchange V3 REST API Client.

Implements HMAC-SHA256 authentication and provides async methods
for all public and private endpoints used by OmniVerse Wealth agents.

Authentication flow:
1. Build params dict with nonce (ms timestamp) + request-specific params
2. Add path to create paramsToBeSigned
3. payload = base64(json(paramsToBeSigned))
4. signature = HMAC-SHA256(secret_key, payload)
5. Send with headers: X-MAX-ACCESSKEY, X-MAX-PAYLOAD, X-MAX-SIGNATURE
"""

import hashlib
import hmac
import json
import time
from base64 import b64encode
from decimal import Decimal
from typing import Any
from urllib.parse import urlencode

import httpx

from src.config import settings


class MaxAPIError(Exception):
    """Raised when MAX API returns an error response."""

    def __init__(self, status_code: int, code: int | None = None, message: str = ""):
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(f"MAX API Error [{status_code}]: {code} - {message}")


class MaxClient:
    """Async HTTP client for MAX Exchange V3 REST API.

    All prices, volumes, fees, and balances are returned as strings (Decimal-safe).
    """

    def __init__(
        self,
        api_key: str | None = None,
        api_secret: str | None = None,
        base_url: str | None = None,
    ):
        self.api_key = api_key or settings.max_api_key
        self.api_secret = api_secret or settings.max_api_secret
        self.base_url = (base_url or settings.max_api_base_url).rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=30.0,
            headers={"Content-Type": "application/json"},
        )

    async def close(self):
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

    # ─── Authentication ─────────────────────────────────────────────────────────

    def _generate_nonce(self) -> int:
        """Generate millisecond-precision nonce."""
        return int(time.time() * 1000)

    def _sign(self, path: str, params: dict[str, Any]) -> dict[str, str]:
        """Generate authentication headers for a private API request.

        Args:
            path: API path (e.g., '/api/v3/info')
            params: Request parameters (must include nonce)

        Returns:
            Dict with X-MAX-ACCESSKEY, X-MAX-PAYLOAD, X-MAX-SIGNATURE headers
        """
        params_to_sign = {**params, "path": path}
        payload = b64encode(json.dumps(params_to_sign).encode()).decode()
        signature = hmac.new(
            self.api_secret.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()

        return {
            "X-MAX-ACCESSKEY": self.api_key,
            "X-MAX-PAYLOAD": payload,
            "X-MAX-SIGNATURE": signature,
        }

    # ─── Request Helpers ────────────────────────────────────────────────────────

    async def _public_get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Execute a public GET request (no auth required)."""
        response = await self._client.get(path, params=params)
        return self._handle_response(response)

    async def _private_get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Execute an authenticated GET request."""
        params = params or {}
        params["nonce"] = self._generate_nonce()
        headers = self._sign(path, params)
        response = await self._client.get(path, params=params, headers=headers)
        return self._handle_response(response)

    async def _private_post(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Execute an authenticated POST request."""
        params = params or {}
        params["nonce"] = self._generate_nonce()
        headers = self._sign(path, params)
        response = await self._client.post(path, json=params, headers=headers)
        return self._handle_response(response)

    async def _private_delete(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Execute an authenticated DELETE request."""
        params = params or {}
        params["nonce"] = self._generate_nonce()
        headers = self._sign(path, params)
        response = await self._client.request("DELETE", path, json=params, headers=headers)
        return self._handle_response(response)

    def _handle_response(self, response: httpx.Response) -> Any:
        """Parse response, raise MaxAPIError on failure."""
        if response.status_code >= 400:
            try:
                data = response.json()
                error = data.get("error", {})
                raise MaxAPIError(
                    status_code=response.status_code,
                    code=error.get("code"),
                    message=error.get("message", "Unknown error"),
                )
            except (json.JSONDecodeError, KeyError):
                raise MaxAPIError(
                    status_code=response.status_code,
                    message=response.text,
                )
        return response.json()

    # ─── Public Market Data Endpoints ───────────────────────────────────────────

    async def get_markets(self) -> list[dict]:
        """Get all available markets."""
        return await self._public_get("/api/v3/markets")

    async def get_ticker(self, market: str) -> dict:
        """Get ticker for a specific market (e.g., 'btctwd')."""
        return await self._public_get("/api/v3/ticker", params={"market": market})

    async def get_tickers(self) -> dict:
        """Get tickers for all markets."""
        return await self._public_get("/api/v3/tickers", params={"markets[]": "btctwd"})

    async def get_order_book(self, market: str, limit: int = 20) -> dict:
        """Get order book depth for a market.

        Args:
            market: Market pair (e.g., 'btctwd')
            limit: Number of price levels (default 20)
        """
        return await self._public_get(
            "/api/v3/depth", params={"market": market, "limit": limit}
        )

    async def get_klines(
        self,
        market: str,
        period: int = 1,
        limit: int = 100,
        timestamp: int | None = None,
    ) -> list[list]:
        """Get K-line (candlestick) data.

        Args:
            market: Market pair
            period: Candle period in minutes (1, 5, 15, 30, 60, 120, 240, 360, 720, 1440, 4320, 10080)
            limit: Number of candles (max 10000)
            timestamp: Start timestamp in seconds

        Returns:
            List of [timestamp, open, high, low, close, volume] arrays
        """
        params: dict[str, Any] = {"market": market, "period": period, "limit": limit}
        if timestamp:
            params["timestamp"] = timestamp
        return await self._public_get("/api/v3/k", params=params)

    async def get_public_trades(self, market: str, limit: int = 50) -> list[dict]:
        """Get recent public trades for a market."""
        return await self._public_get(
            "/api/v3/trades", params={"market": market, "limit": limit}
        )

    async def get_server_timestamp(self) -> dict:
        """Get server timestamp for clock synchronization."""
        return await self._public_get("/api/v3/timestamp")

    async def get_index_prices(self) -> list[dict]:
        """Get index prices for all available assets."""
        return await self._public_get("/api/v3/index_prices")

    # ─── Private Account Endpoints (Read-Only) ──────────────────────────────────

    async def get_user_info(self) -> dict:
        """Get authenticated user account info."""
        return await self._private_get("/api/v3/info")

    async def get_accounts(self) -> list[dict]:
        """Get all wallet balances."""
        return await self._private_get("/api/v3/wallet/spot/accounts")

    async def get_account(self, currency: str) -> dict:
        """Get balance for a specific currency."""
        return await self._private_get(f"/api/v3/wallet/spot/account/{currency}")

    async def get_open_orders(self, market: str) -> list[dict]:
        """Get all open orders for a market."""
        return await self._private_get("/api/v3/wallet/spot/orders", params={"market": market})

    async def get_order(self, order_id: int) -> dict:
        """Get a specific order by ID."""
        return await self._private_get("/api/v3/wallet/spot/order", params={"id": order_id})

    async def get_order_history(
        self,
        market: str,
        limit: int = 100,
        from_id: int | None = None,
    ) -> list[dict]:
        """Get closed order history for a market."""
        params: dict[str, Any] = {"market": market, "limit": limit}
        if from_id:
            params["from_id"] = from_id
        return await self._private_get("/api/v3/wallet/spot/order_history", params=params)

    async def get_my_trades(
        self,
        market: str,
        limit: int = 100,
        from_id: int | None = None,
    ) -> list[dict]:
        """Get personal trade history for a market."""
        params: dict[str, Any] = {"market": market, "limit": limit}
        if from_id:
            params["from_id"] = from_id
        return await self._private_get("/api/v3/wallet/spot/trades", params=params)

    async def get_deposits(self, currency: str | None = None, limit: int = 50) -> list[dict]:
        """Get deposit history."""
        params: dict[str, Any] = {"limit": limit}
        if currency:
            params["currency"] = currency
        return await self._private_get("/api/v3/wallet/spot/deposits", params=params)

    async def get_withdrawals(self, currency: str | None = None, limit: int = 50) -> list[dict]:
        """Get withdrawal history."""
        params: dict[str, Any] = {"limit": limit}
        if currency:
            params["currency"] = currency
        return await self._private_get("/api/v3/wallet/spot/withdrawals", params=params)

    # ─── Trading Endpoints (Write - Hermes Agent Only) ──────────────────────────

    async def create_order(
        self,
        market: str,
        side: str,
        volume: str,
        ord_type: str = "limit",
        price: str | None = None,
    ) -> dict:
        """Create a new order.

        Args:
            market: Market pair (e.g., 'btctwd')
            side: 'buy' or 'sell'
            volume: Order volume as string (decimal safe)
            ord_type: 'limit', 'market', 'stop_limit', 'stop_market'
            price: Limit price as string (required for limit orders)

        Returns:
            Created order details

        Raises:
            MaxAPIError: If trading is disabled or order is rejected
        """
        if not settings.max_enable_trading:
            raise MaxAPIError(
                status_code=403,
                code=0,
                message="Trading is disabled. Set MAX_ENABLE_TRADING=1 to enable.",
            )

        params: dict[str, Any] = {
            "market": market,
            "side": side,
            "volume": volume,
            "ord_type": ord_type,
        }
        if price:
            params["price"] = price

        return await self._private_post("/api/v3/wallet/spot/order", params=params)

    async def cancel_order(self, order_id: int) -> dict:
        """Cancel a specific order by ID."""
        if not settings.max_enable_trading:
            raise MaxAPIError(
                status_code=403,
                code=0,
                message="Trading is disabled. Set MAX_ENABLE_TRADING=1 to enable.",
            )
        return await self._private_delete(
            "/api/v3/wallet/spot/order", params={"id": order_id}
        )

    async def cancel_all_orders(self, market: str) -> list[dict]:
        """Cancel all open orders for a market."""
        if not settings.max_enable_trading:
            raise MaxAPIError(
                status_code=403,
                code=0,
                message="Trading is disabled. Set MAX_ENABLE_TRADING=1 to enable.",
            )
        return await self._private_delete(
            "/api/v3/wallet/spot/orders", params={"market": market}
        )
