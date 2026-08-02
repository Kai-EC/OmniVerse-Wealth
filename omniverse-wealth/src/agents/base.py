"""Base agent class and shared state definitions for OmniVerse Wealth."""

from enum import Enum
from typing import Any, Annotated

from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages


class AgentRole(str, Enum):
    """Agent role identifiers."""

    ZEUS = "zeus"
    STARK = "stark"
    MINERVA = "minerva"
    MORPHEUS = "morpheus"
    THEMIS = "themis"
    HERMES = "hermes"


class TradeIntent(BaseModel):
    """Structured trade intent extracted by Zeus for downstream processing."""

    market: str = Field(description="Trading pair, e.g., 'btctwd'")
    side: str = Field(description="'buy' or 'sell'")
    volume: str = Field(description="Amount to trade as string")
    ord_type: str = Field(default="limit", description="Order type")
    price: str | None = Field(default=None, description="Limit price")
    reasoning: str = Field(default="", description="Why this trade is suggested")


class RiskVerdict(BaseModel):
    """Risk assessment result from Themis."""

    approved: bool = Field(description="Whether the trade passes risk checks")
    checks_passed: list[str] = Field(default_factory=list)
    checks_failed: list[str] = Field(default_factory=list)
    risk_score: float = Field(default=0.0, description="0.0 (safe) to 1.0 (max risk)")
    reason: str = Field(default="", description="Human-readable explanation")


class AgentReport(BaseModel):
    """Standardized report from any specialist agent."""

    agent: AgentRole
    summary: str = Field(description="Brief summary of findings")
    data: dict[str, Any] = Field(default_factory=dict, description="Structured data payload")
    confidence: float = Field(default=0.8, description="0.0 to 1.0 confidence score")


class OmniVerseState(BaseModel):
    """Shared state flowing through the LangGraph multi-agent workflow.

    This is the central state object that all agents read from and write to.
    """

    # User interaction
    messages: Annotated[list[BaseMessage], add_messages] = Field(default_factory=list)
    user_query: str = Field(default="", description="Original user input")

    # Zeus orchestration
    intent: str = Field(default="", description="Parsed user intent category")
    required_agents: list[AgentRole] = Field(
        default_factory=list, description="Agents Zeus decides to invoke"
    )

    # Agent reports (collected during parallel consultation)
    reports: list[AgentReport] = Field(
        default_factory=list, description="Reports from specialist agents"
    )

    # Trade flow
    trade_intent: TradeIntent | None = Field(
        default=None, description="Proposed trade if applicable"
    )
    risk_verdict: RiskVerdict | None = Field(
        default=None, description="Themis risk assessment"
    )
    trade_approved: bool = Field(default=False, description="Final approval status")
    trade_result: dict[str, Any] | None = Field(
        default=None, description="Execution result from Hermes"
    )

    # Final output
    final_response: str = Field(default="", description="Final response to present to user")

    class Config:
        arbitrary_types_allowed = True
