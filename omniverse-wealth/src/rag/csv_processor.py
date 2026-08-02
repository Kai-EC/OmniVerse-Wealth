"""CSV Data Processing Module for OmniVerse Wealth.

Handles loading, cleaning, validation, and structured analysis of
MaiCoin/MAX trading history CSV files.

CSV Schema:
    - timestamp: Unix milliseconds
    - currency: Asset symbol (twd, btc, eth, sol, doge, usdt, usdc)
    - price: TWD price per unit at time of action
    - action: deposit | withdrawal | buy | sell
    - change: Signed amount change (negative for sell/withdrawal)
    - balance: Running balance after action
"""

import csv
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Generator

from pydantic import BaseModel, Field, field_validator


class TradeRecord(BaseModel):
    """Single validated record from the trading CSV."""

    timestamp: int = Field(description="Unix timestamp in milliseconds")
    currency: str = Field(description="Asset symbol (lowercase)")
    price: Decimal = Field(description="TWD price per unit")
    action: str = Field(description="deposit|withdrawal|buy|sell")
    change: Decimal = Field(description="Signed amount change")
    balance: Decimal = Field(description="Balance after action")

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        valid = {"deposit", "withdrawal", "buy", "sell"}
        v = v.strip().lower()
        if v not in valid:
            raise ValueError(f"Invalid action: {v}. Must be one of {valid}")
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        return v.strip().lower()

    @property
    def datetime_utc(self) -> datetime:
        """Convert timestamp to UTC datetime."""
        return datetime.fromtimestamp(self.timestamp / 1000, tz=timezone.utc)

    @property
    def is_trade(self) -> bool:
        """Whether this record is a buy or sell (not deposit/withdrawal)."""
        return self.action in ("buy", "sell")

    @property
    def value_twd(self) -> Decimal:
        """Estimated TWD value of this transaction."""
        return abs(self.change) * self.price


class PortfolioSnapshot(BaseModel):
    """Computed portfolio metrics from CSV data."""

    currency: str
    total_bought: Decimal = Decimal("0")
    total_sold: Decimal = Decimal("0")
    total_deposited: Decimal = Decimal("0")
    total_withdrawn: Decimal = Decimal("0")
    buy_count: int = 0
    sell_count: int = 0
    current_balance: Decimal = Decimal("0")
    avg_buy_price_twd: Decimal = Decimal("0")
    total_buy_cost_twd: Decimal = Decimal("0")
    total_sell_revenue_twd: Decimal = Decimal("0")
    realized_pnl_twd: Decimal = Decimal("0")
    first_trade_ts: int = 0
    last_trade_ts: int = 0


class CSVProcessor:
    """Processes MaiCoin/MAX trading history CSV files.

    Provides:
    - Record-level validation and parsing
    - Portfolio-level aggregation
    - Time-range filtering
    - Currency-specific analysis
    - Chunked text generation for RAG embedding
    """

    def __init__(self, csv_path: str | Path):
        self.csv_path = Path(csv_path)
        self._records: list[TradeRecord] = []
        self._loaded = False

    def load(self) -> "CSVProcessor":
        """Load and validate all records from CSV.

        Returns:
            self for method chaining
        """
        if not self.csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {self.csv_path}")

        records = []
        with open(self.csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                try:
                    record = TradeRecord(
                        timestamp=int(row["timestamp"]),
                        currency=row["currency"],
                        price=Decimal(row["price"]),
                        action=row["action"],
                        change=Decimal(row["change"]),
                        balance=Decimal(row["balance"]),
                    )
                    records.append(record)
                except (ValueError, InvalidOperation, KeyError) as e:
                    # Skip malformed rows, log for debugging
                    print(f"[CSVProcessor] Skipping row {i+1}: {e}")

        self._records = sorted(records, key=lambda r: r.timestamp)
        self._loaded = True
        return self

    @property
    def records(self) -> list[TradeRecord]:
        """All validated records, sorted by timestamp."""
        if not self._loaded:
            self.load()
        return self._records

    @property
    def currencies(self) -> list[str]:
        """Unique currencies in the dataset."""
        return sorted(set(r.currency for r in self.records))

    @property
    def date_range(self) -> tuple[datetime, datetime]:
        """Start and end dates of the dataset."""
        if not self.records:
            return (datetime.min, datetime.min)
        return (self.records[0].datetime_utc, self.records[-1].datetime_utc)

    def filter_by_currency(self, currency: str) -> list[TradeRecord]:
        """Get all records for a specific currency."""
        currency = currency.strip().lower()
        return [r for r in self.records if r.currency == currency]

    def filter_by_action(self, action: str) -> list[TradeRecord]:
        """Get all records for a specific action type."""
        action = action.strip().lower()
        return [r for r in self.records if r.action == action]

    def filter_by_time_range(
        self, start_ts: int | None = None, end_ts: int | None = None
    ) -> list[TradeRecord]:
        """Filter records by timestamp range (milliseconds)."""
        result = self.records
        if start_ts is not None:
            result = [r for r in result if r.timestamp >= start_ts]
        if end_ts is not None:
            result = [r for r in result if r.timestamp <= end_ts]
        return result

    def compute_portfolio(self) -> dict[str, PortfolioSnapshot]:
        """Compute portfolio metrics for each currency.

        Returns:
            Dict mapping currency symbol to its PortfolioSnapshot.
        """
        snapshots: dict[str, PortfolioSnapshot] = {}

        for record in self.records:
            cur = record.currency
            if cur not in snapshots:
                snapshots[cur] = PortfolioSnapshot(
                    currency=cur, first_trade_ts=record.timestamp
                )

            snap = snapshots[cur]
            snap.last_trade_ts = record.timestamp
            snap.current_balance = record.balance

            if record.action == "buy":
                snap.total_bought += abs(record.change)
                snap.buy_count += 1
                snap.total_buy_cost_twd += abs(record.change) * record.price

            elif record.action == "sell":
                snap.total_sold += abs(record.change)
                snap.sell_count += 1
                snap.total_sell_revenue_twd += abs(record.change) * record.price

            elif record.action == "deposit":
                snap.total_deposited += abs(record.change)

            elif record.action == "withdrawal":
                snap.total_withdrawn += abs(record.change)

        # Calculate derived metrics
        for snap in snapshots.values():
            if snap.total_bought > 0:
                snap.avg_buy_price_twd = snap.total_buy_cost_twd / snap.total_bought
            snap.realized_pnl_twd = snap.total_sell_revenue_twd - (
                snap.total_buy_cost_twd
                * (snap.total_sold / snap.total_bought)
                if snap.total_bought > 0
                else Decimal("0")
            )

        return snapshots

    def generate_rag_chunks(self, chunk_size: int = 5) -> Generator[str, None, None]:
        """Generate text chunks suitable for RAG embedding.

        Groups records into chunks and produces natural language summaries
        that can be embedded into a vector store.

        Args:
            chunk_size: Number of records per chunk.

        Yields:
            Natural language text chunks describing trading activity.
        """
        for i in range(0, len(self.records), chunk_size):
            chunk = self.records[i : i + chunk_size]
            text_parts = []

            start_dt = chunk[0].datetime_utc.strftime("%Y-%m-%d %H:%M")
            end_dt = chunk[-1].datetime_utc.strftime("%Y-%m-%d %H:%M")
            text_parts.append(f"交易紀錄期間：{start_dt} 至 {end_dt}")

            for record in chunk:
                dt = record.datetime_utc.strftime("%m/%d %H:%M")
                action_map = {
                    "buy": "買入",
                    "sell": "賣出",
                    "deposit": "入金",
                    "withdrawal": "出金",
                }
                action_zh = action_map.get(record.action, record.action)
                text_parts.append(
                    f"- {dt} {action_zh} {abs(record.change)} {record.currency.upper()}"
                    f"，單價 {record.price} TWD"
                    f"，餘額 {record.balance} {record.currency.upper()}"
                )

            yield "\n".join(text_parts)

    def summary_text(self) -> str:
        """Generate a comprehensive portfolio summary as text.

        Useful for direct LLM context injection.
        """
        portfolio = self.compute_portfolio()
        start, end = self.date_range

        lines = [
            f"=== 投資組合摘要 ===",
            f"數據期間：{start.strftime('%Y-%m-%d')} 至 {end.strftime('%Y-%m-%d')}",
            f"總交易筆數：{sum(s.buy_count + s.sell_count for s in portfolio.values())}",
            f"涵蓋幣種：{', '.join(self.currencies)}",
            "",
        ]

        for cur, snap in sorted(portfolio.items()):
            if cur == "twd":
                lines.append(f"[TWD] 最終餘額: {snap.current_balance}")
                lines.append(
                    f"  入金總計: {snap.total_deposited} / 出金總計: {snap.total_withdrawn}"
                )
            else:
                lines.append(f"[{cur.upper()}]")
                lines.append(f"  持倉: {snap.current_balance}")
                lines.append(f"  均買價: {snap.avg_buy_price_twd:.2f} TWD")
                lines.append(f"  買入: {snap.buy_count} 次, 賣出: {snap.sell_count} 次")
                lines.append(
                    f"  買入總量: {snap.total_bought}, 賣出總量: {snap.total_sold}"
                )
                lines.append(f"  已實現損益: {snap.realized_pnl_twd:.2f} TWD")
            lines.append("")

        return "\n".join(lines)
