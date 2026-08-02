"""Local WebSocket development server.

Provides real-time ticker updates and Agent CoT streaming
for frontend development without AWS deployment.

Usage:
    uv run python -m src.ws_server

Connects to MAX REST API every 3 seconds and broadcasts ticker_update
events to all connected clients following the WebSocket API spec.
"""

import asyncio
import json
import time
from typing import Set

import httpx
import websockets
from websockets.server import WebSocketServerProtocol

# Connected clients
clients: Set[WebSocketServerProtocol] = set()

MAX_MARKETS = ["btctwd", "ethtwd", "soltwd", "dogetwd"]


async def handler(websocket: WebSocketServerProtocol):
    """Handle a new WebSocket connection."""
    clients.add(websocket)
    print(f"[+] Client connected ({len(clients)} total)")

    try:
        async for raw in websocket:
            try:
                msg = json.loads(raw)
                event = msg.get("event", "")
                data = msg.get("data", {})
                request_id = msg.get("requestId", "")

                if event == "ping":
                    await websocket.send(json.dumps({
                        "event": "pong",
                        "timestamp": int(time.time() * 1000),
                    }))

                elif event == "subscribe":
                    channel = data.get("channel", "")
                    await websocket.send(json.dumps({
                        "event": "subscribed",
                        "data": {"channel": channel, "status": "success"},
                        "requestId": request_id,
                    }))
                    print(f"  Subscribed to: {channel}")

                elif event == "query":
                    await handle_query(websocket, data, request_id)

                else:
                    await websocket.send(json.dumps({
                        "event": "error",
                        "data": {"code": 4002, "message": f"Unknown event: {event}"},
                        "requestId": request_id,
                    }))

            except json.JSONDecodeError:
                await websocket.send(json.dumps({
                    "event": "error",
                    "data": {"code": 4002, "message": "Invalid JSON"},
                }))
    except websockets.ConnectionClosed:
        pass
    finally:
        clients.discard(websocket)
        print(f"[-] Client disconnected ({len(clients)} total)")


async def handle_query(ws: WebSocketServerProtocol, data: dict, request_id: str):
    """Simulate Agent CoT streaming for a query."""
    message = data.get("message", "")

    # Stream agent thinking steps
    agents = [
        ("zeus", "正在解析您的問題意圖..."),
        ("stark", "正在查詢 MAX 即時行情..."),
        ("morpheus", "正在分析個人交易歷史..."),
        ("minerva", "正在評估市場情緒指數..."),
    ]

    for agent, thought in agents:
        await ws.send(json.dumps({
            "event": "agent_thinking",
            "data": {"agent": agent, "status": "active", "thought": thought},
            "timestamp": int(time.time() * 1000),
            "requestId": request_id,
        }))
        await asyncio.sleep(0.5)  # Simulate processing time

    # Final response
    await ws.send(json.dumps({
        "event": "agent_response",
        "data": {
            "message": f"Multi-Agent 分析完成：「{message}」",
            "agents_completed": ["zeus", "stark", "morpheus", "minerva"],
        },
        "timestamp": int(time.time() * 1000),
        "requestId": request_id,
    }))

    # All agents done
    await ws.send(json.dumps({
        "event": "agent_thinking",
        "data": {"agent": "all", "status": "done"},
        "timestamp": int(time.time() * 1000),
        "requestId": request_id,
    }))


async def ticker_broadcaster():
    """Fetch MAX tickers every 3 seconds and broadcast to all clients."""
    async with httpx.AsyncClient(timeout=5.0) as http:
        while True:
            if clients:
                tickers = {}
                for market in MAX_MARKETS:
                    try:
                        resp = await http.get(
                            f"https://max-api.maicoin.com/api/v3/ticker?market={market}"
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                            tickers[market] = {
                                "market": market,
                                "last": data.get("last"),
                                "buy": data.get("buy"),
                                "sell": data.get("sell"),
                                "high": data.get("high"),
                                "low": data.get("low"),
                                "vol": data.get("vol"),
                                "open": data.get("open"),
                                "timestamp": int(time.time() * 1000),
                            }
                    except Exception:
                        pass

                if tickers:
                    message = json.dumps({
                        "event": "ticker_update",
                        "data": tickers,
                        "timestamp": int(time.time() * 1000),
                    })

                    # Broadcast to all
                    disconnected = set()
                    for client in clients:
                        try:
                            await client.send(message)
                        except websockets.ConnectionClosed:
                            disconnected.add(client)
                    clients.difference_update(disconnected)

            await asyncio.sleep(3)


async def main():
    """Start WebSocket server + ticker broadcaster."""
    print("=" * 50)
    print("  OmniVerse Wealth — WebSocket Dev Server")
    print("  ws://localhost:8080")
    print("=" * 50)
    print("\nFeatures:")
    print("  • Ticker broadcast every 3s (MAX real-time)")
    print("  • Agent CoT streaming simulation")
    print("  • Ping/Pong heartbeat")
    print()

    # Start ticker broadcaster in background
    asyncio.create_task(ticker_broadcaster())

    # Start WebSocket server
    async with websockets.serve(handler, "0.0.0.0", 8080):
        print("[Server] Listening on ws://0.0.0.0:8080")
        await asyncio.Future()  # Run forever


if __name__ == "__main__":
    asyncio.run(main())
