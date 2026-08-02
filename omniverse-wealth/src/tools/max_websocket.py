"""MAX Exchange WebSocket Client (Framework).

Provides real-time market data streaming from MAX Exchange.
Full implementation pending WebSocket docs upload.

Expected channels (based on MAX WebSocket documentation):
- orderbook: Real-time order book updates
- trade: Real-time trade stream
- ticker: Ticker updates
- kline: K-line/candlestick updates

Reference: https://maicoin.github.io/max-websocket-docs
"""

import asyncio
import json
from typing import Any, Callable, Coroutine

import websockets


# MAX WebSocket endpoint (to be confirmed with docs)
MAX_WS_PUBLIC_URL = "wss://max-stream.maicoin.com/ws"
MAX_WS_PRIVATE_URL = "wss://max-stream.maicoin.com/ws"


class MaxWebSocketClient:
    """WebSocket client for MAX Exchange real-time data.

    NOTE: This is a framework skeleton. Full implementation
    will be completed once WebSocket documentation is provided.

    Usage:
        async with MaxWebSocketClient() as ws:
            await ws.subscribe_trades("btctwd")
            async for message in ws.listen():
                process(message)
    """

    def __init__(self, url: str = MAX_WS_PUBLIC_URL):
        self.url = url
        self._ws = None
        self._subscriptions: list[dict] = []
        self._handlers: dict[str, list[Callable]] = {}
        self._running = False

    async def connect(self):
        """Establish WebSocket connection."""
        self._ws = await websockets.connect(self.url)
        self._running = True

    async def disconnect(self):
        """Close WebSocket connection."""
        self._running = False
        if self._ws:
            await self._ws.close()
            self._ws = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, *args):
        await self.disconnect()

    # ─── Subscription Methods ───────────────────────────────────────────────

    async def subscribe_trades(self, market: str):
        """Subscribe to real-time trade stream for a market.

        Args:
            market: Market pair (e.g., 'btctwd')
        """
        await self._subscribe("trade", market)

    async def subscribe_orderbook(self, market: str, depth: int = 20):
        """Subscribe to order book updates.

        Args:
            market: Market pair
            depth: Order book depth level
        """
        await self._subscribe("orderbook", market, {"depth": depth})

    async def subscribe_ticker(self, market: str):
        """Subscribe to ticker updates.

        Args:
            market: Market pair
        """
        await self._subscribe("ticker", market)

    async def subscribe_kline(self, market: str, resolution: str = "1m"):
        """Subscribe to K-line updates.

        Args:
            market: Market pair
            resolution: Candle resolution (1m, 5m, 15m, 1h, etc.)
        """
        await self._subscribe("kline", market, {"resolution": resolution})

    async def _subscribe(
        self, channel: str, market: str, params: dict | None = None
    ):
        """Send subscription message.

        TODO: Adjust message format based on actual WebSocket docs.
        """
        subscription = {
            "action": "sub",
            "subscriptions": [
                {
                    "channel": channel,
                    "market": market,
                    **(params or {}),
                }
            ],
        }
        self._subscriptions.append(subscription)

        if self._ws:
            await self._ws.send(json.dumps(subscription))

    # ─── Event Handling ─────────────────────────────────────────────────────

    def on(self, event: str, handler: Callable):
        """Register an event handler.

        Args:
            event: Event type (trade, orderbook, ticker, kline)
            handler: Async callback function
        """
        self._handlers.setdefault(event, []).append(handler)

    async def listen(self):
        """Listen for incoming messages and dispatch to handlers.

        Yields:
            Parsed message dicts from WebSocket.
        """
        if not self._ws:
            raise RuntimeError("Not connected. Call connect() first.")

        while self._running:
            try:
                raw = await asyncio.wait_for(self._ws.recv(), timeout=30.0)
                message = json.loads(raw)

                # Dispatch to handlers
                event_type = message.get("e") or message.get("channel", "")
                if event_type in self._handlers:
                    for handler in self._handlers[event_type]:
                        await handler(message)

                yield message

            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                if self._ws:
                    await self._ws.ping()
            except websockets.ConnectionClosed:
                self._running = False
                break
            except json.JSONDecodeError:
                continue

    # ─── Utility Methods ────────────────────────────────────────────────────

    async def get_snapshot(self, market: str, channel: str = "trade") -> list[dict]:
        """Get initial snapshot when subscribing.

        Some channels provide an initial data dump on subscription.

        Args:
            market: Market pair
            channel: Channel type

        Returns:
            List of initial snapshot messages.
        """
        messages = []
        await self._subscribe(channel, market)

        if self._ws:
            # Collect messages for a short window
            try:
                while True:
                    raw = await asyncio.wait_for(self._ws.recv(), timeout=2.0)
                    msg = json.loads(raw)
                    messages.append(msg)
                    # Stop after receiving snapshot type
                    if msg.get("e") == "snapshot":
                        break
            except asyncio.TimeoutError:
                pass

        return messages
