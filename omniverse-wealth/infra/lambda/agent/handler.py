"""Lambda handler for Multi-Agent query processing.

Entry point for REST API POST /query requests.
Invokes the LangGraph multi-agent workflow and returns the final response.
"""

import json
import os
import traceback


def main(event, context):
    """Handle incoming agent query requests.

    Expected body: {"user_query": "我最近 BTC 的持倉表現如何？"}
    Returns: {"status": "ok", "response": "...", "agents_invoked": [...]}
    """
    try:
        # Parse request
        body = json.loads(event.get("body", "{}"))
        user_query = body.get("user_query", "")

        if not user_query:
            return _response(400, {"error": "user_query is required"})

        # TODO: Import and invoke the LangGraph workflow
        # In production, this would be:
        # from src.graph import omniverse_graph
        # from src.agents.base import OmniVerseState
        # state = OmniVerseState(user_query=user_query)
        # result = await omniverse_graph.ainvoke(state)

        # For now, return structured mock response
        response = {
            "status": "ok",
            "user_query": user_query,
            "intent": "query_market",
            "agents_invoked": ["zeus", "stark", "morpheus"],
            "response": f"已收到您的問題：「{user_query}」。Multi-Agent 系統正在處理中。",
            "trade_suggestion": None,
        }

        return _response(200, response)

    except Exception as e:
        return _response(500, {
            "error": "Internal server error",
            "detail": str(e),
            "trace": traceback.format_exc(),
        })


def health(event, context):
    """Simple health check endpoint."""
    return _response(200, {
        "status": "healthy",
        "service": "OmniVerse Wealth",
        "model": os.environ.get("BEDROCK_MODEL_ID", "not-configured"),
    })


def _response(status_code: int, body: dict) -> dict:
    """Build API Gateway proxy response."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
        },
        "body": json.dumps(body, ensure_ascii=False),
    }
