"""LangGraph Multi-Agent Workflow for OmniVerse Wealth.

This module defines the core workflow graph that orchestrates all 6 agents:

Flow:
1. Zeus parses intent → determines which agents to invoke
2. Specialist agents run in parallel (Stark, Minerva, Morpheus)
3. If trade intent exists → Themis evaluates risk
4. If risk approved → Hermes executes trade
5. Zeus synthesizes all reports → final response

Graph Structure:
    [START]
       │
       ▼
    [zeus_parse_intent]
       │
       ▼
    [route_to_agents] ─── conditional branching
       │
       ├──► [stark_analyze]    (parallel)
       ├──► [minerva_analyze]  (parallel)
       ├──► [morpheus_analyze] (parallel)
       │
       ▼
    [collect_reports]
       │
       ▼
    [should_trade?] ─── conditional
       │          │
       │ Yes      │ No
       ▼          │
    [themis_eval]  │
       │          │
       ▼          │
    [trade_gate?]  │
       │      │   │
       │ Pass │Fail│
       ▼      │   │
    [hermes]  │   │
       │      │   │
       ▼      ▼   ▼
    [zeus_synthesize]
       │
       ▼
    [END]
"""

from typing import Literal

from langgraph.graph import END, StateGraph

from src.agents.base import AgentRole, OmniVerseState
from src.agents.hermes import HermesAgent
from src.agents.minerva import MinervaAgent
from src.agents.morpheus import MorpheusAgent
from src.agents.stark import StarkAgent
from src.agents.themis import ThemisAgent
from src.agents.zeus import ZeusAgent


# ─── Agent Instances ────────────────────────────────────────────────────────

zeus = ZeusAgent()
stark = StarkAgent()
minerva = MinervaAgent()
morpheus = MorpheusAgent()
themis = ThemisAgent()
hermes = HermesAgent()


# ─── Node Functions ─────────────────────────────────────────────────────────
# Each node function wraps an agent method and operates on OmniVerseState.


async def zeus_parse_intent(state: OmniVerseState) -> OmniVerseState:
    """Entry node: Zeus parses user intent and decides routing."""
    return await zeus.parse_intent(state)


async def stark_analyze(state: OmniVerseState) -> OmniVerseState:
    """Stark performs market & technical analysis."""
    return await stark.analyze(state)


async def minerva_analyze(state: OmniVerseState) -> OmniVerseState:
    """Minerva performs sentiment & on-chain analysis."""
    return await minerva.analyze(state)


async def morpheus_analyze(state: OmniVerseState) -> OmniVerseState:
    """Morpheus performs personal history RAG analysis."""
    return await morpheus.analyze(state)


async def themis_evaluate(state: OmniVerseState) -> OmniVerseState:
    """Themis evaluates trade risk with deterministic guardrails."""
    return await themis.evaluate(state)


async def hermes_execute(state: OmniVerseState) -> OmniVerseState:
    """Hermes executes the approved trade via MAX API."""
    return await hermes.execute(state)


async def zeus_synthesize(state: OmniVerseState) -> OmniVerseState:
    """Final node: Zeus synthesizes all reports into user response."""
    return await zeus.synthesize(state)


# ─── Routing Logic ──────────────────────────────────────────────────────────


def route_after_intent(state: OmniVerseState) -> list[str]:
    """Determine which specialist agents to invoke based on Zeus's routing.

    Returns a list of next node names for parallel execution.
    """
    nodes = []
    for agent in state.required_agents:
        if agent == AgentRole.STARK:
            nodes.append("stark_analyze")
        elif agent == AgentRole.MINERVA:
            nodes.append("minerva_analyze")
        elif agent == AgentRole.MORPHEUS:
            nodes.append("morpheus_analyze")

    # Always invoke at least Stark for market context
    if not nodes:
        nodes.append("stark_analyze")

    return nodes


def should_evaluate_trade(state: OmniVerseState) -> Literal["themis_evaluate", "zeus_synthesize"]:
    """Determine if trade evaluation is needed.

    Routes to Themis if there's a trade intent, otherwise skips to synthesis.
    """
    if state.trade_intent is not None:
        return "themis_evaluate"
    return "zeus_synthesize"


def trade_gate(state: OmniVerseState) -> Literal["hermes_execute", "zeus_synthesize"]:
    """Gate after Themis evaluation.

    Only allows Hermes execution if Themis explicitly approved.
    """
    if state.trade_approved and state.risk_verdict and state.risk_verdict.approved:
        return "hermes_execute"
    return "zeus_synthesize"


# ─── Graph Construction ─────────────────────────────────────────────────────


def build_omniverse_graph() -> StateGraph:
    """Construct the OmniVerse Wealth multi-agent workflow graph.

    Returns:
        Compiled LangGraph StateGraph ready for invocation.
    """
    # Initialize graph with shared state schema
    workflow = StateGraph(OmniVerseState)

    # ── Add Nodes ──
    workflow.add_node("zeus_parse_intent", zeus_parse_intent)
    workflow.add_node("stark_analyze", stark_analyze)
    workflow.add_node("minerva_analyze", minerva_analyze)
    workflow.add_node("morpheus_analyze", morpheus_analyze)
    workflow.add_node("themis_evaluate", themis_evaluate)
    workflow.add_node("hermes_execute", hermes_execute)
    workflow.add_node("zeus_synthesize", zeus_synthesize)

    # ── Set Entry Point ──
    workflow.set_entry_point("zeus_parse_intent")

    # ── Conditional Routing: Zeus → Specialist Agents ──
    # After intent parsing, route to the relevant specialist agents
    workflow.add_conditional_edges(
        "zeus_parse_intent",
        route_after_intent,
        {
            "stark_analyze": "stark_analyze",
            "minerva_analyze": "minerva_analyze",
            "morpheus_analyze": "morpheus_analyze",
        },
    )

    # ── Specialist Agents → Trade Decision ──
    # After each specialist finishes, check if we need trade evaluation
    workflow.add_conditional_edges(
        "stark_analyze",
        should_evaluate_trade,
        {
            "themis_evaluate": "themis_evaluate",
            "zeus_synthesize": "zeus_synthesize",
        },
    )
    workflow.add_conditional_edges(
        "minerva_analyze",
        should_evaluate_trade,
        {
            "themis_evaluate": "themis_evaluate",
            "zeus_synthesize": "zeus_synthesize",
        },
    )
    workflow.add_conditional_edges(
        "morpheus_analyze",
        should_evaluate_trade,
        {
            "themis_evaluate": "themis_evaluate",
            "zeus_synthesize": "zeus_synthesize",
        },
    )

    # ── Themis → Trade Gate ──
    workflow.add_conditional_edges(
        "themis_evaluate",
        trade_gate,
        {
            "hermes_execute": "hermes_execute",
            "zeus_synthesize": "zeus_synthesize",
        },
    )

    # ── Hermes → Final Synthesis ──
    workflow.add_edge("hermes_execute", "zeus_synthesize")

    # ── Zeus Synthesize → END ──
    workflow.add_edge("zeus_synthesize", END)

    return workflow.compile()


# Pre-built graph instance for import
omniverse_graph = build_omniverse_graph()
