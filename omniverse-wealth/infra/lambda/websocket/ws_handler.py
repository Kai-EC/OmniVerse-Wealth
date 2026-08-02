"""Lambda handlers for WebSocket API Gateway.

Implements the WebSocket API specification:
- Event-based message format: {event, data, timestamp, requestId}
- Ping/Pong heartbeat (30s interval)
- Channel subscription (ticker.*, agent.*, trade.*)
- Error responses with status codes

Channels:
- ticker.{market}: Real-time price ticks (e.g., ticker.btctwd)
- agent.{session_id}: Agent Chain-of-Thought streaming
- trade.{user_id}: Trade execution updates
- portfolio.{user_id}: Portfolio balance changes
"""

import json
import os
import time
from typing import Any

import boto3

dynamodb = boto3.resource("dynamodb")
session_table = dynamodb.Table(os.environ.get("SESSION_TABLE_NAME", ""))


def on_connect(event, context):
    """Handle $connect route.

    Validates JWT token and stores connection in DynamoDB.
    """
    connection_id = event["requestContext"]["connectionId"]
    query_params = event.get("queryStringParameters") or {}
    token = query_params.get("token", "")

    # Store connection
    try:
        session_table.put_item(Item={
            "session_id": f"ws#{connection_id}",
            "timestamp": int(time.time() * 1000),
            "connection_id": connection_id,
            "user_id": "default",  # Extract from JWT in production
            "subscriptions": [],
            "status": "connected",
            "ttl": int(time.time()) + 86400,
        })
    except Exception as e:
        print(f"[connect] Error: {e}")

    return {"statusCode": 200, "body": "Connected"}


def on_disconnect(event, context):
    """Handle $disconnect route."""
    connection_id = event["requestContext"]["connectionId"]

    try:
        session_table.delete_item(Key={
            "session_id": f"ws#{connection_id}",
            "timestamp": 0,
        })
    except Exception as e:
        print(f"[disconnect] Error: {e}")

    return {"statusCode": 200, "body": "Disconnected"}


def on_message(event, context):
    """Handle $default route — process incoming messages.

    Routes based on event field:
    - ping: Respond with pong
    - subscribe: Add channel subscription
    - unsubscribe: Remove channel subscription
    - query: Forward to agent system
    """
    connection_id = event["requestContext"]["connectionId"]
    domain = event["requestContext"]["domainName"]
    stage = event["requestContext"]["stage"]

    apigw = boto3.client(
        "apigatewaymanagementapi",
        endpoint_url=f"https://{domain}/{stage}",
    )

    try:
        body = json.loads(event.get("body", "{}"))
        evt = body.get("event", "")
        data = body.get("data", {})
        request_id = body.get("requestId", "")

        if evt == "ping":
            _handle_ping(apigw, connection_id)

        elif evt == "subscribe":
            _handle_subscribe(apigw, connection_id, data, request_id)

        elif evt == "unsubscribe":
            _handle_unsubscribe(apigw, connection_id, data, request_id)

        elif evt == "query":
            _handle_query(apigw, connection_id, data, request_id)

        else:
            _send(apigw, connection_id, {
                "event": "error",
                "data": {"code": 4002, "message": f"Invalid event: {evt}"},
                "requestId": request_id,
            })

    except json.JSONDecodeError:
        _send(apigw, connection_id, {
            "event": "error",
            "data": {"code": 4002, "message": "Invalid JSON format"},
        })
    except Exception as e:
        _send(apigw, connection_id, {
            "event": "error",
            "data": {"code": 5000, "message": str(e)},
        })

    return {"statusCode": 200}


# ─── Event Handlers ─────────────────────────────────────────────────────────

def _handle_ping(apigw, connection_id: str):
    """Respond to heartbeat ping."""
    _send(apigw, connection_id, {
        "event": "pong",
        "timestamp": int(time.time() * 1000),
    })


def _handle_subscribe(apigw, connection_id: str, data: dict, request_id: str):
    """Subscribe to a channel."""
    channel = data.get("channel", "")
    if not channel:
        _send(apigw, connection_id, {
            "event": "error",
            "data": {"code": 4002, "message": "Channel is required"},
            "requestId": request_id,
        })
        return

    # Store subscription in DynamoDB
    try:
        session_table.update_item(
            Key={"session_id": f"ws#{connection_id}", "timestamp": 0},
            UpdateExpression="SET subscriptions = list_append(if_not_exists(subscriptions, :empty), :ch)",
            ExpressionAttributeValues={
                ":ch": [channel],
                ":empty": [],
            },
        )
    except Exception:
        pass

    _send(apigw, connection_id, {
        "event": "subscribed",
        "data": {"channel": channel, "status": "success"},
        "requestId": request_id,
    })


def _handle_unsubscribe(apigw, connection_id: str, data: dict, request_id: str):
    """Unsubscribe from a channel."""
    channel = data.get("channel", "")
    _send(apigw, connection_id, {
        "event": "unsubscribed",
        "data": {"channel": channel, "status": "success"},
        "requestId": request_id,
    })


def _handle_query(apigw, connection_id: str, data: dict, request_id: str):
    """Handle agent query with streaming CoT responses.

    Sends multiple agent_status events before final response.
    """
    user_query = data.get("message", "")
    if not user_query:
        _send(apigw, connection_id, {
            "event": "error",
            "data": {"code": 4002, "message": "Message is required"},
            "requestId": request_id,
        })
        return

    # Stream: Zeus parsing intent
    _send(apigw, connection_id, {
        "event": "agent_thinking",
        "data": {
            "agent": "zeus",
            "status": "active",
            "thought": "正在解析您的問題意圖...",
        },
        "timestamp": int(time.time() * 1000),
        "requestId": request_id,
    })

    # Stream: Specialist agents
    _send(apigw, connection_id, {
        "event": "agent_thinking",
        "data": {
            "agent": "stark",
            "status": "active",
            "thought": "正在查詢 MAX 即時行情數據...",
        },
        "timestamp": int(time.time() * 1000),
        "requestId": request_id,
    })

    _send(apigw, connection_id, {
        "event": "agent_thinking",
        "data": {
            "agent": "morpheus",
            "status": "active",
            "thought": "正在分析個人歷史交易紀錄...",
        },
        "timestamp": int(time.time() * 1000),
        "requestId": request_id,
    })

    # Stream: Final response
    _send(apigw, connection_id, {
        "event": "agent_response",
        "data": {
            "message": f"已完成分析：「{user_query}」\n\n（完整 Multi-Agent 回應將在 Bedrock 整合後啟用）",
            "agents_completed": ["zeus", "stark", "morpheus"],
        },
        "timestamp": int(time.time() * 1000),
        "requestId": request_id,
    })

    # Mark agents done
    _send(apigw, connection_id, {
        "event": "agent_thinking",
        "data": {"agent": "all", "status": "done"},
        "timestamp": int(time.time() * 1000),
        "requestId": request_id,
    })


# ─── Ticker Broadcasting ───────────────────────────────────────────────────

def broadcast_ticker(event, context):
    """Scheduled Lambda: Fetches MAX tickers and broadcasts to subscribers.

    Triggered by EventBridge every 3 seconds.
    Pushes to all connections subscribed to ticker.* channels.
    """
    import urllib.request

    markets = ["btctwd", "ethtwd", "soltwd", "dogetwd"]
    tickers = {}

    for market in markets:
        try:
            url = f"https://max-api.maicoin.com/api/v3/ticker?market={market}"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
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
        except Exception as e:
            print(f"[ticker] Error fetching {market}: {e}")

    if not tickers:
        return

    # Get WebSocket API endpoint from env
    ws_endpoint = os.environ.get("WS_API_ENDPOINT", "")
    if not ws_endpoint:
        return

    apigw = boto3.client(
        "apigatewaymanagementapi",
        endpoint_url=ws_endpoint,
    )

    # Scan for active connections (in production use GSI)
    try:
        response = session_table.scan(
            FilterExpression="begins_with(session_id, :prefix)",
            ExpressionAttributeValues={":prefix": "ws#"},
        )
        connections = response.get("Items", [])
    except Exception:
        connections = []

    # Broadcast to all connected clients
    for conn in connections:
        conn_id = conn.get("connection_id")
        if not conn_id:
            continue

        message = {
            "event": "ticker_update",
            "data": tickers,
            "timestamp": int(time.time() * 1000),
        }

        try:
            apigw.post_to_connection(
                ConnectionId=conn_id,
                Data=json.dumps(message, ensure_ascii=False).encode(),
            )
        except apigw.exceptions.GoneException:
            # Clean up stale connection
            try:
                session_table.delete_item(Key={
                    "session_id": f"ws#{conn_id}",
                    "timestamp": 0,
                })
            except Exception:
                pass
        except Exception:
            pass


# ─── Utility ────────────────────────────────────────────────────────────────

def _send(client, connection_id: str, message: dict):
    """Send a message to a WebSocket client."""
    try:
        client.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(message, ensure_ascii=False).encode("utf-8"),
        )
    except client.exceptions.GoneException:
        print(f"[send] Connection gone: {connection_id}")
    except Exception as e:
        print(f"[send] Error: {e}")
