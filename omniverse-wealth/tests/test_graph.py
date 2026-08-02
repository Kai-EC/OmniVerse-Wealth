"""Integration tests for LangGraph Multi-Agent workflow.

Tests the graph structure, routing logic, and state flow
WITHOUT requiring actual Bedrock/API connections (mocked).
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.agents.base import AgentRole, OmniVerseState, TradeIntent, RiskVerdict
from src.graph import (
    build_omniverse_graph,
    route_after_intent,
    should_evaluate_trade,
    trade_gate,
)


class TestGraphRouting:
    """Test conditional routing logic."""

    def test_route_after_intent_with_stark(self):
        state = OmniVerseState(
            user_query="BTC 現在行情如何",
            required_agents=[AgentRole.STARK],
        )
        result = route_after_intent(state)
        assert "stark_analyze" in result

    def test_route_after_intent_multiple_agents(self):
        state = OmniVerseState(
            user_query="分析 BTC",
            required_agents=[AgentRole.STARK, AgentRole.MINERVA, AgentRole.MORPHEUS],
        )
        result = route_after_intent(state)
        assert "stark_analyze" in result
        assert "minerva_analyze" in result
        assert "morpheus_analyze" in result

    def test_route_after_intent_defaults_to_stark(self):
        state = OmniVerseState(
            user_query="hello",
            required_agents=[],
        )
        result = route_after_intent(state)
        assert "stark_analyze" in result

    def test_should_evaluate_trade_with_intent(self):
        state = OmniVerseState(
            user_query="買 BTC",
            trade_intent=TradeIntent(
                market="btctwd", side="buy", volume="0.01", price="3400000"
            ),
        )
        result = should_evaluate_trade(state)
        assert result == "themis_evaluate"

    def test_should_evaluate_trade_without_intent(self):
        state = OmniVerseState(user_query="BTC 行情")
        result = should_evaluate_trade(state)
        assert result == "zeus_synthesize"

    def test_trade_gate_approved(self):
        state = OmniVerseState(
            user_query="買 BTC",
            trade_approved=True,
            risk_verdict=RiskVerdict(approved=True, risk_score=0.1),
        )
        result = trade_gate(state)
        assert result == "hermes_execute"

    def test_trade_gate_rejected(self):
        state = OmniVerseState(
            user_query="買 BTC",
            trade_approved=False,
            risk_verdict=RiskVerdict(approved=False, risk_score=0.8, reason="Too risky"),
        )
        result = trade_gate(state)
        assert result == "zeus_synthesize"

    def test_trade_gate_no_verdict(self):
        state = OmniVerseState(user_query="買 BTC", trade_approved=False)
        result = trade_gate(state)
        assert result == "zeus_synthesize"


class TestGraphStructure:
    """Test graph compilation and node existence."""

    def test_graph_compiles(self):
        graph = build_omniverse_graph()
        assert graph is not None

    def test_graph_has_all_nodes(self):
        graph = build_omniverse_graph()
        node_names = list(graph.nodes.keys())
        assert "zeus_parse_intent" in node_names
        assert "stark_analyze" in node_names
        assert "minerva_analyze" in node_names
        assert "morpheus_analyze" in node_names
        assert "themis_evaluate" in node_names
        assert "hermes_execute" in node_names
        assert "zeus_synthesize" in node_names

    def test_graph_has_start_node(self):
        graph = build_omniverse_graph()
        assert "__start__" in graph.nodes
