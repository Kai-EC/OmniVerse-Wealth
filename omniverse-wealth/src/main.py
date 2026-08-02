"""OmniVerse Wealth - Main entry point.

Usage:
    python -m src.main "我最近 BTC 的持倉表現如何？現在適合加碼嗎？"
"""

import asyncio
import sys

from src.agents.base import OmniVerseState
from src.graph import omniverse_graph


async def run_query(user_query: str) -> str:
    """Run a user query through the OmniVerse Wealth multi-agent system.

    Args:
        user_query: Natural language investment question or command.

    Returns:
        Final synthesized response from Zeus.
    """
    initial_state = OmniVerseState(user_query=user_query)

    # Execute the graph
    final_state = await omniverse_graph.ainvoke(initial_state)

    return final_state["final_response"]


async def main():
    """CLI entry point."""
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = "我最近 BTC 的持倉表現如何？現在適合加碼嗎？"

    print(f"\n{'='*60}")
    print(f"🌌 OmniVerse Wealth - 全域多元宇宙投資特助")
    print(f"{'='*60}")
    print(f"\n📝 用戶問題: {query}\n")
    print(f"{'─'*60}")
    print("⏳ 正在調度 Agent 團隊進行分析...\n")

    response = await run_query(query)

    print(f"{'─'*60}")
    print(f"\n🎯 最終建議:\n")
    print(response)
    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(main())
